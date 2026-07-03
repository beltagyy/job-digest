# Job Digest Bot

> Personal AI-powered job search tool that automates finding relevant EU positions.

[![CI](https://github.com/beltagyy/job-digest/actions/workflows/ci.yml/badge.svg)](https://github.com/beltagyy/job-digest/actions/workflows/ci.yml)

## Core Workflow

1. Scrapes LinkedIn + Indeed across 10 EU countries
2. Scores listings against your CV (0–100%) via LLM
3. Filters below-threshold roles (default: 75%)
4. Generates tailored cover letters
5. Delivers an HTML email digest grouped by country

## Performance

The parallel architecture achieves a **14× speedup** — ~5 min end-to-end versus a previous sequential approach taking ~75 minutes.

## Key Tech

| Layer | Tool |
|---|---|
| Scraping | JobSpy + `ThreadPoolExecutor` (6 workers) |
| AI scoring | Any OpenAI-compatible LLM (DeepSeek-V3.2 by default via Azure AI Foundry) |
| Storage | SQLite deduplication |
| Email | [Resend.com](https://resend.com) (free tier) |
| Scheduling | Linux cron |

## Cost

~$0.50–1/month total · LLM scoring ~$0.20–0.50/month

## Setup

```bash
# 1. Clone
git clone https://github.com/beltagyy/job-digest.git
cd job-digest

# 2. Install deps (Python 3.12+)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. Configure
cp .env.example .env
# Edit .env with your Azure AI + Resend credentials

# 4. Customise config.py with your CV profile and search terms

# 5. Run
python run.py            # full run
python run.py --dry-run  # scrape + score, save preview HTML, no email
python run.py --no-xing  # skip Xing (faster for testing)
```

## Scheduling (Linux cron)

```cron
# Run every day at 7 AM
0 7 * * * cd /path/to/job-digest && .venv/bin/python run.py >> digest_run.log 2>&1
```

## Customisation

Only two files need editing:

- **`config.py`** — CV profile, search terms, target countries, score threshold
- **`.env`** — API keys and email addresses

## Project Structure

```
job-digest/
├── run.py                         # Entry point
├── config.py                      # All configuration
├── scrapers/
│   ├── jobspy_scraper.py          # LinkedIn + Indeed via JobSpy (parallel)
│   ├── xing_scraper.py            # Xing via Playwright
│   └── yej_scraper.py             # YourEnglishJob.com via REST API
├── matching/
│   └── scorer.py                  # AI scoring + cover letter generation
├── storage/
│   └── db.py                      # SQLite deduplication
├── email_digest/
│   ├── renderer.py                # Jinja2 HTML rendering
│   ├── sender.py                  # Resend.com email dispatch
│   └── templates/
│       └── digest.html.j2         # Email HTML template
├── scripts/
│   └── check_secrets.py           # CI secrets scanner helper
└── tests/                         # pytest test suite
```

## License

MIT
