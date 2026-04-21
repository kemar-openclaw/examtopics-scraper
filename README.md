# examtopics-scraper

Resilient scraper for [Exam Topics](https://www.examtopics.com) certification exams. Scrapes questions from ALL vendors (Google, Amazon, Microsoft, CompTIA, Cisco, and more).

## Features

- **All Vendors**: Not just Google Cloud — works with Amazon (AWS), Microsoft (Azure), CompTIA, Cisco, and any vendor on Exam Topics
- **Dynamic Discovery**: Automatically discovers vendors and exams from the website
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

## Quick Start

### Discover All Vendors

```bash
examtopics list-vendors
```

### Discover All Exams

```bash
# All exams from all vendors
examtopics list-exams

# Exams from specific vendor
examtopics list-exams --vendor amazon
examtopics list-exams --vendor google
examtopics list-exams --vendor microsoft
```

### Scrape a Single Exam

```bash
# Scrape Google Cloud PCA
examtopics scrape gcp-pca

# Scrape AWS Solutions Architect
examtopics scrape aws-saa-c03

# Export to CSV
examtopics scrape aws-saa-c03 --format csv --output aws-exam.csv

# Export to Anki
examtopics scrape gcp-pca --format anki --output gcp-pca.apkg

# Show browser (non-headless)
examtopics scrape gcp-pca --no-headless
```

### Scrape ALL Exams

```bash
# Scrape all available exams (limited to 10 pages each by default)
examtopics scrape-all

# Scrape all Google exams
examtopics scrape-all --vendor google

# Scrape all AWS exams
examtopics scrape-all --vendor amazon

# Custom output directory
examtopics scrape-all --output-dir ./all-exams --format json
```

## Available Exams (Built-in)

### Google Cloud (GCP)

| Slug | Code | Exam Name |
|------|------|-----------|
| `gcp-pca` | GCP-PCA | Professional Cloud Architect |
| `gcp-pcd` | GCP-PCD | Professional Cloud Developer |
| `gcp-ace` | GCP-ACE | Associate Cloud Engineer |
| `gcp-pde` | GCP-PDE | Professional Data Engineer |
| `gcp-pse` | GCP-PSE | Professional Security Engineer |
| `gcp-pne` | GCP-PNE | Professional Network Engineer |

### Amazon Web Services (AWS)

| Slug | Code | Exam Name |
|------|------|-----------|
| `aws-saa-c03` | AWS-SAA-C03 | Solutions Architect - Associate |
| `aws-sap-c02` | AWS-SAP-C02 | Solutions Architect - Professional |
| `aws-dva-c02` | AWS-DVA-C02 | Developer - Associate |
| `aws-soa-c02` | AWS-SOA-C02 | SysOps Administrator - Associate |
| `aws-cli` | AWS-CLI | Cloud Practitioner |

### Microsoft Azure

| Slug | Code | Exam Name |
|------|------|-----------|
| `azure-az-900` | AZ-900 | Azure Fundamentals |
| `azure-az-104` | AZ-104 | Azure Administrator |
| `azure-az-305` | AZ-305 | Azure Solutions Architect |
| `azure-az-204` | AZ-204 | Azure Developer |

> **Note**: You can discover more exams dynamically using `examtopics list-exams --discover`

## CLI Commands

| Command | Description |
|---------|-------------|
| `list-vendors` | List all certification vendors |
| `list-exams` | List all available exams |
| `scrape` | Scrape a single exam |
| `scrape-all` | Scrape ALL exams |
| `scrape-page` | Scrape a single page |
| `config` | Show configuration |
| `clear-cache` | Clear the cache |

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
    
    # Discover all vendors
    vendors = await scraper.discover_vendors()
    print(f"Found {len(vendors)} vendors")
    
    # Discover exams from a vendor
    exams = await scraper.discover_exams("amazon")
    print(f"Found {len(exams)} AWS exams")
    
    # Scrape a single exam
    exam = await scraper.scrape_exam("gcp-pca")
    print(f"Scraped {len(exam.questions)} questions")
    
    # Scrape ALL exams from a vendor
    all_exams = await scraper.scrape_all_exams("google", max_pages_per_exam=5)
    print(f"Scraped {len(all_exams)} Google exams")

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
