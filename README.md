# examtopics-scraper

Resilient scraper for [Exam Topics](https://www.examtopics.com) certification exams. Focused on Google Cloud certifications with anti-detection measures, caching, and multiple export formats.

## Features

- **Resilient Scraping**: Automatic retries, exponential backoff, stealth mode
- **Anti-Detection**: User agent rotation, browser fingerprint randomization
- **Caching**: Disk cache to avoid re-scraping
- **Proxy Support**: HTTP/HTTPS proxy configuration
- **Multiple Formats**: JSON, CSV, Anki flashcards
- **Rate Limiting**: Configurable delays between requests

## Installation

```bash
pip install examtopics-scraper
playwright install chromium
```

## Available Exams

### Google Cloud (GCP)

| Code | Exam Name |
|------|-----------|
| `gcp-pca` | Professional Cloud Architect |
| `gcp-pcd` | Professional Cloud Developer |
| `gcp-ace` | Associate Cloud Engineer |
| `gcp-pds` | Professional Data Engineer |
| `gcp-pse` | Professional Security Engineer |
| `gcp-pne` | Professional Network Engineer |

## Usage

### List Available Exams

```bash
examtopics list-exams
```

### Scrape an Exam

```bash
# Basic scrape (saves to output/exam.json)
examtopics scrape gcp-pca

# Scrape with page limit
examtopics scrape gcp-pca --max-pages 10

# Export to CSV
examtopics scrape gcp-pca --format csv --output gcp-pca.csv

# Export to Anki
examtopics scrape gcp-pca --format anki --output gcp-pca.apkg

# Show browser (non-headless)
examtopics scrape gcp-pca --no-headless
```

### Scrape Single Page

```bash
examtopics scrape-page gcp-pca 1
```

### Configuration

```bash
examtopics config
```

### Clear Cache

```bash
examtopics clear-cache
```

## Configuration (.env)

```bash
EXAMTOPICS_HEADLESS=true
EXAMTOPICS_BASE_URL=https://www.examtopics.com
EXAMTOPICS_OUTPUT_DIR=./output
EXAMTOPICS_CACHE_DIR=./.cache
EXAMTOPICS_REQUEST_DELAY_MIN=2.0
EXAMTOPICS_REQUEST_DELAY_MAX=5.0
EXAMTOPICS_MAX_RETRIES=3
EXAMTOPICS_USE_STEALTH=true
EXAMTOPICS_USE_PROXY=false
EXAMTOPICS_PROXY_URL=http://user:pass@host:port
```

## Programmatic Usage

```python
import asyncio
from examtopics_scraper import ExamTopicsScraper, ExamTopicsSettings

async def main():
    settings = ExamTopicsSettings(
        headless=True,
        max_pages=5,
        request_delay_min=3.0,
    )
    
    scraper = ExamTopicsScraper(settings)
    
    # Scrape entire exam
    exam = await scraper.scrape_exam("gcp-pca")
    
    print(f"Scraped {len(exam.questions)} questions")
    print(f"With answers: {exam.correct_answer_count}")
    
    # Access questions
    for q in exam.questions[:3]:
        print(f"\nQ{q.number}: {q.text[:80]}...")
        for ans in q.answers:
            mark = "✓" if ans.is_correct else " "
            print(f"  [{mark}] {ans.letter}. {ans.text[:50]}...")

asyncio.run(main())
```

## Resilience Features

1. **Exponential Backoff**: Retries with increasing delays (5s → 10s → 20s)
2. **Random Delays**: 2-5 second random delays between requests
3. **User Agent Rotation**: Rotates browser fingerprints
4. **Stealth Mode**: Hides automation indicators
5. **Disk Caching**: Avoids re-scraping already-fetched pages
6. **Scroll Simulation**: Scrolls page to load lazy content

## License

MIT
