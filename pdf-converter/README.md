# AI-Powered PDF to Excel Converter

## Architecture

**Simple AI-Powered Stack:**
- **Backend API**: FastAPI (Python 3.11) + Anthropic Claude Sonnet 4
- **Frontend**: React 18

## Quick Start

1. Get your Anthropic API key from https://console.anthropic.com/
2. Edit `.env` and add your API key:
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```
3. Run: `./deploy.sh`

## Access

- Frontend: http://localhost:3000
- Backend API: http://localhost:3001
- Health Check: http://localhost:3001/health

## Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f

# View backend logs
docker compose logs -f backend

# Stop services
docker compose down

# Rebuild after code changes
docker compose up -d --build
```

## API Endpoints

### Backend API (Port 3001)
- `POST /api/convert` - AI-powered extraction using Claude Sonnet 4
- `GET /health` - Health check

## Features

✅ **AI-Powered Extraction**
- Uses Claude Sonnet 4 for intelligent document understanding
- Automatically detects tables, lists, and structured data
- Handles complex layouts including DATEV payroll documents
- Merges split Euro/cent columns automatically
- Understands semantic structure

✅ **DATEV Support**
- Optimized for German DATEV Lohnjournal documents
- Automatic number normalization (German format)
- Handles merged cells and complex headers

✅ **Export Options**
- CSV export with German formatting (semicolon-separated)
- Copy to clipboard
- Preview in browser

## Cost Estimate

**Using Claude Sonnet 4.5** (best accuracy):
- Per PDF: ~$0.08-0.15
- 100 PDFs/month: ~$8-15
- 1000 PDFs/month: ~$80-150

*Note: Sonnet 4.5 is slightly more expensive than Sonnet 4, but provides significantly better accuracy for complex documents.*

## Support

**Check logs:**
```bash
docker compose logs backend
```

**Verify API key:**
Check `.env` file has valid `ANTHROPIC_API_KEY`

**Common issues:**
- "API key not configured" → Check `.env` file
- "Failed to process PDF" → Check PDF is not encrypted/corrupted
- Empty extraction → PDF might be image-based (needs OCR first)

## Development

### Backend (Python)
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend (React)
```bash
cd frontend
npm install
npm start
```

## Technology Stack

- **Backend**: FastAPI, Anthropic SDK, Python 3.11
- **Frontend**: React 18, Lucide Icons, TailwindCSS
- **AI**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929) - Latest model
- **Deployment**: Docker, Docker Compose
