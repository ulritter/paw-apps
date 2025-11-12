from fastapi import FastAPI, File, UploadFile, HTTPException, Cookie, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import anthropic
import base64
import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from jose import JWTError, jwt
import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PDF Converter API",
    version="2.0.0",
    description="AI-powered PDF to Excel converter"
)

# Configuration
PORT = int(os.getenv("PORT", "8001"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
DATABASE_URL = os.getenv("DATABASE_URL")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    max_age=86400
)


# --- Authentication ---
async def verify_auth_token(auth_token: str | None = Cookie(None)):
    """Dependency to verify authentication token"""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(auth_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")


# --- Utilities: NUMBER NORMALIZATION FOR DATEV-LIKE DOCUMENTS ---
MONEY_HEADER_HINTS = [
    'brutto', 'netto', 'betrag', 'summe', 'gesamt', 'lohn', 'gehalt', 
    'steuer', 'kirchen', 'solidar', 'versicherung',
    'gross', 'net', 'amount', 'total', 'sum', 'pay', 'salary', 
    'tax', 'health', 'pension', 'unemployment'
]


def is_money_header(header: str = '') -> bool:
    """Check if a header name suggests monetary values."""
    h = str(header).lower()
    return any(k in h for k in MONEY_HEADER_HINTS)


def is_digits(value: Any) -> bool:
    """Check if value contains only digits (possibly with minus sign)."""
    return bool(re.match(r'^-?\d+$', str(value).strip()))


def is_likely_cents(value: Any) -> bool:
    """Check if value looks like a cents column (0, 00, or 2-digit numbers)."""
    v = str(value).strip()
    return bool(re.match(r'^-?\d{1,2}$', v))


def normalize_money_value(value: Any) -> str:
    """
    Normalize monetary values to German format (comma decimal separator).
    
    Examples:
        "123.45" -> "123,45"
        "12345" -> "123,45" (interprets last 2 digits as cents)
        "123,45" -> "123,45" (already correct)
    """
    raw = str(value or '').strip()
    if not raw:
        return raw
    
    # Already has decimal separator
    if re.match(r'^-?\d+[\.,]\d{1,2}$', raw):
        parts = raw.replace(',', '.').split('.')
        int_part = parts[0]
        dec_part = (parts[1] if len(parts) > 1 else '').ljust(2, '0')[:2]
        return f"{int(int_part):,}".replace(',', '') + f",{dec_part}"
    
    # Pure digits: interpret last two as cents if 3+ digits
    if re.match(r'^-?\d{3,}$', raw):
        neg = raw.startswith('-')
        digits = raw[1:] if neg else raw
        euros = digits[:-2]
        cents = digits[-2:]
        out = f"{int(euros)},{cents}"
        return '-' + out if neg else out
    
    # Leave as-is (could be non-monetary or already formatted)
    return raw


def merge_euro_cent_columns(table: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge split Euro/cent columns into single monetary values.
    
    DATEV documents often split amounts into separate Euro and cent columns.
    This function detects and merges them.
    """
    if not table or not isinstance(table.get('headers'), list) or not isinstance(table.get('rows'), list):
        return table
    
    headers = table['headers'].copy()
    rows = [row.copy() for row in table['rows']]
    
    # Heuristic: if a column looks like integer euros and the next column is mostly 1-2 digit cents, merge them
    col = 0
    while col < len(headers) - 1:
        h0 = headers[col] or ''
        h1 = headers[col + 1] or ''
        
        # Count how many rows look like euros and cents
        cents_like_count = 0
        euros_like_count = 0
        sample_count = max(1, len(rows))
        
        for row in rows:
            if col < len(row) and col + 1 < len(row):
                v0 = row[col]
                v1 = row[col + 1]
                if is_digits(v0):
                    euros_like_count += 1
                if is_likely_cents(v1):
                    cents_like_count += 1
        
        cents_ratio = cents_like_count / sample_count
        euros_ratio = euros_like_count / sample_count
        
        # Merge if patterns match
        if (is_money_header(h0) or euros_ratio > 0.6) and cents_ratio > 0.6:
            # Merge columns col and col+1 into col with comma decimal
            for i, row in enumerate(rows):
                if col < len(row) and col + 1 < len(row):
                    left = str(row[col] or '').strip()
                    right = str(row[col + 1] or '').strip().zfill(2)[-2:]
                    
                    if not left and not right:
                        continue
                    
                    if re.match(r'^-?\d+$', left):
                        neg = left.startswith('-')
                        l = left[1:] if neg else left
                        merged = f"{int(l)},{right}"
                        if neg:
                            merged = '-' + merged
                    elif re.match(r'^-?\d+[\.,]\d+$', left):
                        # Already has decimals; keep left but ensure two digits
                        parts = left.replace(',', '.').split('.')
                        i_part = parts[0]
                        d_part = (parts[1] if len(parts) > 1 else '').ljust(2, '0')[:2]
                        merged = f"{int(i_part)},{d_part}"
                    else:
                        # Fallback: just concatenate with comma
                        merged = f"{left},{right}"
                    
                    rows[i][col] = merged
            
            # Remove the cents column
            headers.pop(col + 1)
            for i in range(len(rows)):
                if col + 1 < len(rows[i]):
                    rows[i].pop(col + 1)
            
            # Move back one column to re-evaluate after structural change
            col = max(0, col - 1)
        else:
            col += 1
    
    # Normalize monetary-looking columns' values formatting
    for c in range(len(headers)):
        if is_money_header(headers[c]):
            for r in range(len(rows)):
                if c < len(rows[r]):
                    rows[r][c] = normalize_money_value(rows[r][c])
    
    return {**table, 'headers': headers, 'rows': rows}


def normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize all tables in the extraction result."""
    if not result or not isinstance(result.get('tables'), list):
        return result
    
    tables = [merge_euro_cent_columns(t) for t in result['tables']]
    return {**result, 'tables': tables}


# --- API Endpoints ---

@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "api_key_configured": bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your-api-key-here')
    }


@app.post("/api/convert")
async def convert_ai(
    pdf: UploadFile = File(...),
    email: str = Depends(verify_auth_token)
):
    """
    AI-powered extraction via Anthropic Claude.
    
    Uses Claude Sonnet 4 to intelligently extract structured data from PDFs.
    Requires authentication.
    """
    try:
        # Validate API key
        if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == 'your-api-key-here':
            logger.error('ANTHROPIC_API_KEY not configured')
            raise HTTPException(status_code=500, detail="API key not configured")
        
        # Validate file
        if not pdf.filename or not pdf.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read file content
        content = await pdf.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB."
            )
        
        logger.info(f"Processing PDF: {pdf.filename}, Size: {len(content)} bytes")
        
        # Encode to base64
        base64_data = base64.b64encode(content).decode('utf-8')
        
        # Initialize Anthropic client
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Create the prompt
        prompt_text = """You are a precise data extraction specialist for German DATEV payroll documents (Lohnjournale).

⚠️ CRITICAL: VERTICAL LINES ARE COLUMN SEPARATORS, NOT DATA!

DATEV documents use THIN VERTICAL LINES to separate Euro and Cent columns:
- Example in PDF: "867 | 00" (vertical line between)
- You might see: "867|00" or "867 00" with a line
- CORRECT extraction: "867,00" (ONE merged value)
- WRONG: "86700" or "867 00" or keeping them separate

STEP-BY-STEP PROCESS:

1. **Identify Column Structure FIRST**:
   - Look for thin vertical lines in the table
   - These lines separate Euro (left) from Cents (right)
   - Example: If you see "867" then a line then "00", merge to "867,00"
   - If you see "1.858" then a line then "71", merge to "1858,71"

2. **Recognize Monetary Columns**:
   - Headers like: "Brutto", "Netto", "LSt", "KiSt", "SolZ", "Steuer"
   - ANY column with Euro amounts will have cents in the next narrow column
   - The cents column is usually 2 digits wide

3. **Extract Each Row Carefully**:
   - Read left-to-right across the row
   - When you hit a Euro amount, check the NEXT column for cents
   - Merge them with comma: "euros,cents"
   - Continue to next data column (skip the cents column)

4. **Number Formatting Rules**:
   - Use comma (,) as decimal separator: "867,00" NOT "867.00"
   - NO thousands separators: "1234,00" NOT "1.234,00"
   - Always include 2 decimal places for monetary amounts
   - If cents column shows "0" or blank, use "00": "867,00"

5. **Column Headers**:
   - Identify German DATEV column names accurately
   - Common headers: "Mitarbeiter-Nr", "Name", "Brutto", "Netto", "LSt", "KiSt", "SolZ"
   - Use the EXACT header text from the document
   - Do NOT create headers for the cents columns (they get merged)

6. **Table Structure**:
   - Main employee table: One row per employee with ALL their data
   - Summary tables: Separate tables for totals
   - Tax tables: Separate tables for tax breakdowns
   - Each row must have the SAME number of columns as headers

7. **Quality Checks**:
   - Count rows: If document shows 10 employees, extract 10 rows
   - Verify numbers: Cross-check totals match individual entries
   - Check alignment: Each value must be in the correct column
   - NO concatenated values like "86700" or "1.85871"

OUTPUT FORMAT (JSON only, no markdown):

{
  "documentType": "DATEV Lohnjournal",
  "tables": [
    {
      "title": "Mitarbeiter Lohnabrechnung",
      "headers": ["Mitarbeiter-Nr", "Faktor", "Name", "Brutto", "Netto", "LSt", "KiSt", "SolZ"],
      "rows": [
        ["00030", "1,0", "Ritter, Uwe", "867,00", "650,00", "180,00", "15,00", "10,00"],
        ["00031", "1,0", "Schmelzer, Marcus", "843,00", "625,00", "170,00", "14,00", "9,00"]
      ]
    }
  ],
  "metadata": {
    "date": "Januar 2025",
    "reference": "document reference if found",
    "notes": "any important context"
  }
}

EXTRACT ALL DATA WITH MAXIMUM PRECISION. Every number, every row, every column must be accurate."""
        
        # Call Anthropic API
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",  # Latest Sonnet 4.5 - best for complex agents and coding
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": base64_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt_text
                        }
                    ]
                }
            ]
        )
        
        # Extract text content from response
        text_content = ""
        for block in message.content:
            if block.type == "text":
                text_content += block.text
        
        # Clean up JSON (remove markdown code blocks if present)
        json_text = text_content.strip()
        json_text = re.sub(r'```json\n?', '', json_text)
        json_text = re.sub(r'```\n?', '', json_text)
        
        # Parse JSON
        try:
            import json
            result = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse AI response: {str(e)}"
            )
        
        # Normalize the result (merge euro/cent columns, etc.)
        normalized = normalize_result(result)
        
        logger.info(f"Successfully processed PDF: {len(normalized.get('tables', []))} tables extracted")
        
        return JSONResponse(content=normalized)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(e)}"
        )


# Error handler for file size errors
@app.exception_handler(413)
async def request_entity_too_large_handler(request, exc):
    return JSONResponse(
        status_code=413,
        content={"error": f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024:.0f}MB."}
    )


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting PDF Converter API on port {PORT}")
    logger.info(f"Environment: {os.getenv('ENV', 'development')}")
    logger.info(f"API Key configured: {'Yes' if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your-api-key-here' else 'No'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
