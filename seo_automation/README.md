# SEO/AEO Content Automation System

An automated pipeline that discovers trending keywords, generates SEO/AEO-optimised articles, and publishes them to WordPress. Built for Oliveboard-style exam preparation platforms.

## Architecture

```
TREND FETCHER (Google Trends, Autocomplete, PAA, Reddit)
    │
    ▼
RELEVANCE FILTER (OpenAI — filters by Oliveboard domains)
    │
    ▼
KEYWORD EXPANSION (OpenAI — long-tail query generation)
    │
    ▼
KEYWORD CLUSTERING (OpenAI — topical grouping)
    │
    ▼
BLUEPRINT GENERATOR (OpenAI — article outlines, FAQs, snippets)
    │
    ▼
ARTICLE GENERATOR (OpenAI — 1500–2000 word Markdown articles)
    │
    ▼
SEO/AEO OPTIMIZER (Markdown→HTML, JSON-LD schemas, keyword checks)
    │
    ▼
INTERNAL LINKER (auto-links to 3 related + 1 pillar article)
    │
    ▼
CMS PUBLISHER (WordPress REST API)
```

## Quick Start

### 1. Install dependencies

```bash
cd seo_automation
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run a dry-run test

```bash
python -m seo_automation.main --dry-run
```

### 4. Run the full pipeline

```bash
python -m seo_automation.main
```

## CLI Options

| Flag | Description |
|---|---|
| `--dry-run` | Validate pipeline without external API calls |
| `--step <name>` | Run only a specific step: `trend_fetch`, `expand`, `cluster`, `blueprint`, `generate`, `optimize`, `link`, `publish` |
| `--limit <N>` | Limit number of articles to generate |
| `--skip-publish` | Run everything except publishing |
| `--skip-scraping` | Skip Playwright-based scraping |

## Project Structure

```
seo_automation/
├── main.py                  # Pipeline orchestrator (CLI entry point)
├── config.py                # Configuration from .env
├── database.py              # SQLite database layer
├── trend_fetcher.py         # Broad trend discovery + relevance filtering
├── keyword_expander.py      # Long-tail keyword expansion (OpenAI)
├── keyword_cluster.py       # Topical keyword clustering (OpenAI)
├── blueprint_generator.py   # Article blueprint generation (OpenAI)
├── article_generator.py     # Full article generation (OpenAI)
├── seo_optimizer.py         # SEO/AEO post-processing + schema markup
├── internal_linker.py       # Automatic internal linking engine
├── publisher.py             # WordPress REST API publisher
├── utils/
│   ├── openai_client.py     # OpenAI API wrapper with retry logic
│   ├── schema_generator.py  # JSON-LD structured data generators
│   └── deduplicator.py      # Fuzzy keyword/title deduplication
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## AEO Optimisation

Every article is structured for AI answer engine extraction:

- **Direct answer summary** (40–60 words) at the top
- **Question-based headings** (What is…? How to…?)
- **Definition boxes** (`> **Definition:**`)
- **Step-by-step sections** with numbered lists
- **Tables** for comparisons and structured data
- **FAQ section** with concise, self-contained answers
- **JSON-LD schemas**: Article, FAQPage, HowTo

## Schema Markup

The system automatically generates and injects:

- `Article` schema
- `FAQPage` schema (extracted from FAQ sections)
- `HowTo` schema (when step-by-step content is detected)

## Relevant Domains

The trend fetcher discovers **any** trending keyword and filters by relevance to:

- Competitive exams
- Government job preparation
- Study techniques
- Career guidance
- Learning productivity
- Exam notifications
- Current affairs
- Interview preparation
- Mock tests
- Skill building
- Student productivity

## Scaling

The system is designed to generate **10–50 articles/day**:

- Configurable via `ARTICLES_PER_DAY` in `.env`
- Use `--limit` flag for manual control
- All data persisted in SQLite for restartability
- Deduplication prevents repeated content

## Daily Automation

Use cron or similar to run the pipeline daily:

```bash
# Run daily at 6 AM IST
0 6 * * * cd /path/to/project && python -m seo_automation.main >> pipeline.log 2>&1
```
