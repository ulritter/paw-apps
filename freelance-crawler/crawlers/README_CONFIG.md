# Search Configuration Quick Reference

## File Location
`/crawlers/search_config.json`

## JSON Structure
```json
{
  "crawler_name": {
    "base_url": "https://example.com",
    "search_path": "/search",
    "search_patterns": [
      {
        "query": "search_term",
        "filter_keywords": ["keyword1", "keyword2"]
      }
    ]
  }
}
```

## How It Works

1. **URL Construction**: Uses `base_url` + `search_path` + `?query=...`
2. **Search**: Crawler searches for `query` on the website
3. **Filter**: Only saves jobs that contain at least one `filter_keyword`
4. **Isolation**: Each search pattern has its own filter keywords

## Quick Examples

### Add New Search Pattern
```json
{
  "query": "react",
  "filter_keywords": ["react", "javascript", "typescript", "frontend"]
}
```

### No Filtering (Save All Results)
```json
{
  "query": "freelance",
  "filter_keywords": []
}
```

### Technology-Specific
```json
{
  "query": "cloud",
  "filter_keywords": ["aws", "azure", "gcp", "kubernetes", "docker"]
}
```

## Current Configuration

### FreelancerMap
- **Base URL**: `https://www.freelancermap.de`
- **Search Path**: `/projektboerse.html`
- **Patterns**:
  - ✅ salesforce (10 filter keywords)
  - ✅ data science (16 filter keywords)


### Solcom
- **Base URL**: `https://www.solcom.de`
- **Search Path**: `/de/projektportal`
- **Patterns**:
  - ✅ salesforce (10 filter keywords)
  - ✅ data science (16 filter keywords)


### Hays
- **Base URL**: `https://www.hays.de`
- **Search Path**: `/jobsuche/stellenangebote-jobs`
- **Patterns**:
  - ✅ salesforce (10 filter keywords)
  - ✅ data science (16 filter keywords)


## Testing

```bash
# Validate JSON
cat crawlers/search_config.json | jq .

# Run crawler
docker compose up --build

# Check results
docker compose logs crawler | grep "Total jobs"
```

## Filter Matching

Searches these fields (case-insensitive):
- ✅ Job title
- ✅ Company name
- ✅ Location

Example:
```
Job: "Senior Salesforce Developer"
Filter: ["salesforce", "apex"]
Result: ✅ MATCH (contains "salesforce")
```

## Tips

1. **Use lowercase** for consistency
2. **Include variations**: "ml" and "machine learning"
3. **Start broad**, refine based on results
4. **Test incrementally** after changes

## See Full Documentation
`SEARCH_CONFIG_GUIDE.md` - Complete guide with examples and best practices
