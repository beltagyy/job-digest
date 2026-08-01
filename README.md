# 🔍 Job Digest Bot

> A personal AI-powered job search assistant that scrapes LinkedIn and Indeed every 2 days across 10 EU countries, scores each listing against your CV using an LLM, and emails you a curated digest with tailored cover letters — so you only see roles worth your time. Runs in **~5 minutes** end-to-end using fully parallel scraping and scoring.

[![CI](https://github.com/beltagyy/job-digest/actions/workflows/ci.yml/badge.svg)](https://github.com/beltagyy/job-digest/actions/workflows/ci.yml)

---

## What It Does

1. **Scrapes** LinkedIn + Indeed across multiple countries and cities
2. **Scores** every job against your CV profile using an LLM (0–100% match)
3. **Filters** out anything below your threshold (default: 70%)
4. **Detects** relocation/visa sponsorship mentions automatically
5. **Writes** a tailored 2-paragraph cover letter for each passing job
6. **Emails** a rich HTML digest grouped by country, sorted by match %

### Sample Email Output

```
🇩🇪 Germany — 4 matches

[85%] Senior Cloud Security Engineer @ N26 · Berlin · ✅ Relocation
  ✓ Why it matches: AWS + K8s security, Wiz CNAPP, GDPR compliance
  ✍ Cover Letter:
    "At N26, where cloud-native security at scale is a core engineering..."

[78%] DevSecOps Engineer @ Siemens · Munich · linkedin
  ...
```

---

## Performance

| Stage | Time |
|-------|------|
| Scraping (10 countries, parallel) | ~2 min |
| Scoring (parallel subprocess batches) | ~3 min |
| **Total end-to-end** | **~5 min** |

Previous sequential approach took ~75 min. Parallel architecture = **14x speedup**.

## Tech Stack

| Layer | Tool | Cost |
|-------|------|------|
| Scraping | [JobSpy](https://github.com/Bunsly/JobSpy) (LinkedIn + Indeed) | Free |
| Parallel scraping | `ThreadPoolExecutor` (6 workers) | Free |
| AI Scoring & Cover Letters | Any OpenAI-compatible LLM (DeepSeek-V3.2 default) | Pay-per-use |
| Scoring | Parallel subprocess batches of 40 (avoids 128k token limit) | - |
| Pre-filter | Title keyword filter (removes junk before AI) | Free |
| Deduplication | SQLite (stdlib) | Free |
| Email | [Resend.com](https://resend.com) | Free (3k/month) |
| Template | Jinja2 HTML | Free |
| Infrastructure | Any Linux VPS or cloud VM | ~$5–10/month |
| Scheduler | Linux cron | Free |

---

## Quick Start

### Prerequisites

- Python 3.11 or 3.12
- A Linux server (VPS, cloud VM, or local machine)
- An OpenAI-compatible API key (Azure AI Foundry, OpenAI, etc.)
- A [Resend.com](https://resend.com) account (free)

---

## Step-by-Step Setup

### Step 1 — Clone the Repository

```bash
git clone https://gitlab.com/mohamed_elbeltagy/job-digest.git
cd job-digest
```

### Step 2 — Create a Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# On Windows: .venv\Scripts\activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** If `jobspy` installs as the wrong package, run:
> ```bash
> pip uninstall jobspy -y && pip install python-jobspy
> ```

### Step 4 — Install Playwright (for Xing scraping)

```bash
playwright install chromium
playwright install-deps chromium   # Linux only — installs OS-level deps
```

> On Ubuntu 24.04, if you get a `libasound2` error:
> ```bash
> sudo apt install -y libasound2t64
> PLAYWRIGHT_BROWSERS_PATH=/opt/job-digest/.playwright playwright install chromium
> ```
> Then add `PLAYWRIGHT_BROWSERS_PATH=/opt/job-digest/.playwright` to your `.env`

### Step 5 — Configure Your Environment

Copy the example file and fill in your values:

```bash
cp .env.example .env
nano .env
```

Your `.env` should look like this:

```env
# LLM API (Azure AI Foundry, OpenAI, or any compatible endpoint)
AZURE_AI_ENDPOINT=https://YOUR-RESOURCE.services.ai.azure.com/
AZURE_AI_API_KEY=your_api_key_here
AZURE_AI_MODEL=DeepSeek-V3.2          # or gpt-4o-mini, gpt-4o, etc.

# Email delivery (https://resend.com — free tier)
RESEND_API_KEY=re_your_key_here
DIGEST_TO_EMAIL=your@email.com
DIGEST_FROM_EMAIL=digest@yourdomain.com   # or onboarding@resend.dev for testing

# Optional tuning
MAX_JOBS_PER_SOURCE=25                # jobs per search query (lower = faster)
PLAYWRIGHT_BROWSERS_PATH=/opt/job-digest/.playwright   # only needed if Playwright install path differs
```

### Step 6 — Customize for Your Profile

Open `config.py` and update these sections:

```python
# 1. Your job search terms
SEARCH_TERMS = [
    "Senior Cloud Security Engineer",
    "DevSecOps Engineer",
    "Kubernetes Security",
]

# 2. Target countries and cities
SEARCH_LOCATIONS = [
    ("germany",     "Germany",     ["Germany", "Berlin", "Munich"]),
    ("netherlands", "Netherlands", ["Netherlands", "Amsterdam"]),
    ...
]

# 3. Minimum match score to appear in digest (0-100)
MIN_SCORE_TO_INCLUDE = 70

# 4. YOUR CV profile — this drives AI matching and cover letter generation
CV_PROFILE = """
Your Name — Your Title
X years experience in ...
Core strengths:
- Skill 1
- Skill 2
...
Seeking: [role type]
Location: Relocating from [city] to [target region]
Languages: ...
"""
```

> **Tip:** The more specific and accurate your `CV_PROFILE`, the better the match scores and cover letters will be. Include technologies, frameworks, certifications, and seniority level.

### Step 7 — Test Run (No Email Sent)

```bash
# Quick test — skip Xing, save HTML preview instead of emailing
python run.py --dry-run --no-xing

# Full test including Xing scraping
python run.py --dry-run
```

Open `digest_preview_YYYY-MM-DD.html` in your browser to see what the email looks like.

### Step 8 — Real Run (Sends Email)

```bash
python run.py --no-xing   # LinkedIn + Indeed only (faster)
python run.py              # Full run including Xing
```

Check your inbox — the digest should arrive within 60 seconds.

### Step 9 — Set Up Automatic Scheduling (Every 2 Days)

#### On Linux (cron)

```bash
# Create the run script
cat > /opt/job-digest/run_digest.sh << 'EOF'
#!/bin/bash
cd /opt/job-digest
source .venv/bin/activate
python run.py >> /var/log/job-digest.log 2>&1
EOF

chmod +x /opt/job-digest/run_digest.sh

# Create log file
sudo touch /var/log/job-digest.log
sudo chmod 666 /var/log/job-digest.log

# Add to cron — runs at 8am every 2 days
crontab -e
# Add this line:
0 8 */2 * * /opt/job-digest/run_digest.sh
```

Monitor logs:
```bash
tail -f /var/log/job-digest.log
```

#### On Windows (Task Scheduler)

1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily, repeat every 2 days
3. Action: Start a program
   - Program: `C:\path\to\job-digest\.venv\Scripts\python.exe`
   - Arguments: `run.py`
   - Start in: `C:\path\to\job-digest`

---

## Updating the Code

When you push changes to the repo, deploy to your VPS with:

```bash
ssh user@YOUR_VPS_IP
cd /opt/job-digest
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt   # only if requirements.txt changed
```

---

## Customizing for a Different Person

Everything you need to change is in **two files only**:

### `config.py` — Search & Matching

| Setting | What to change |
|---------|----------------|
| `SEARCH_TERMS` | Job titles you're targeting |
| `SEARCH_LOCATIONS` | Countries and cities to search |
| `MIN_SCORE_TO_INCLUDE` | Strictness (60 = more jobs, 80 = fewer, higher quality) |
| `RELOCATION_KEYWORDS` | Add keywords in local languages if needed |
| `CV_PROFILE` | **Your most important change** — paste your own background here |
| `DEDUP_DAYS` | How long before a seen job can reappear (default: 30 days) |

### `.env` — Infrastructure

| Variable | What to change |
|----------|---------------|
| `AZURE_AI_MODEL` | Switch to `gpt-4o-mini`, `gpt-4o`, `DeepSeek-V3`, Mistral, etc. |
| `DIGEST_TO_EMAIL` | Your email address |
| `MAX_JOBS_PER_SOURCE` | Lower (10) for faster runs, higher (50) for broader coverage |

### Changing the AI Provider

The scorer uses any OpenAI-compatible API. To switch:

**OpenAI:**
```env
AZURE_AI_ENDPOINT=https://api.openai.com/
AZURE_AI_API_KEY=sk-...
AZURE_AI_MODEL=gpt-4o-mini
```

**Azure AI Foundry (DeepSeek, Mistral, Llama, etc.):**
```env
AZURE_AI_ENDPOINT=https://YOUR-RESOURCE.services.ai.azure.com/
AZURE_AI_API_KEY=...
AZURE_AI_MODEL=DeepSeek-V3.2    # or Mistral-large, Llama-3.3-70B-Instruct, etc.
```

**Local Ollama:**
```env
AZURE_AI_ENDPOINT=http://localhost:11434/
AZURE_AI_API_KEY=ollama
AZURE_AI_MODEL=llama3.1
```

---

## Project Structure

```
job-digest/
├── run.py                              # Entry point — orchestrates the pipeline
├── config.py                           # ⚙️  All tunables: CV profile, countries, threshold
├── requirements.txt
├── .env.example                        # Template for secrets
├── .gitlab-ci.yml                      # CI pipeline: lint + tests + SAST security checks
├── scripts/
│   └── check_secrets.py                # Called by CI detect-secrets job
│
├── scrapers/
│   └── jobspy_scraper.py               # Parallel scraping via ThreadPoolExecutor (6 workers)
│
├── matching/
│   └── scorer.py                       # Parallel subprocess batch scoring (40 jobs/batch)
│                                       # Each subprocess = fresh API session (no 128k limit)
│
├── storage/
│   └── db.py                           # SQLite deduplication (30-day window)
│
├── email_digest/
│   ├── renderer.py                     # Jinja2 HTML rendering
│   ├── sender.py                       # Resend.com delivery
│   └── templates/
│       └── digest.html.j2              # Email HTML template
│
└── tests/
    ├── test_db.py
    ├── test_scorer.py                  # Tests pre-filter, relocation detection, enrich_jobs
    ├── test_renderer.py
    └── fixtures/sample_jobs.json
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests use mocked API calls — no real LLM calls or emails are made.

---

## Cost Estimate

| Component | Usage | Cost |
|-----------|-------|------|
| VPS (Azure B2s, Sweden Central) | Always on | ~$30/month (or free with startup credits) |
| LLM scoring (DeepSeek-V3.2 via Azure AI Foundry) | ~630 jobs × 2 runs/week, parallel batches | ~$0.20–0.50/month |
| Resend email | 2 emails/week | Free (3,000/month limit) |
| **Total** | | **~$0.50–1/month** (after credits) |

> Using **Azure for Startups** ($1,000 credit): **$0/month** for 12+ months.

## Scoring Logic

The AI model scores each job 0–100 with these rules:
- **Base score**: technical skill overlap with job requirements
- **+10 bonus**: relocation support / visa sponsorship mentioned
- **+5 bonus**: startup or scale-up company
- **+5 bonus**: fewer than 25 applicants or posted <24h ago
- **-15 penalty**: purely consulting/advisory, no hands-on engineering
- **-10 penalty**: requires EU/local citizenship only
- **Hard cap 50**: zero cloud/security/devops overlap

Default threshold: **75%** — only genuinely strong matches reach your inbox.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'jobspy'`
```bash
pip uninstall jobspy -y
pip install python-jobspy
```

### `DeploymentNotFound` from Azure AI
- Check your deployment name in Azure AI Foundry → Deployments
- Update `AZURE_AI_MODEL` in `.env` to match exactly

### Playwright / Chromium install fails on Ubuntu 24.04
```bash
sudo apt install -y libasound2t64
PLAYWRIGHT_BROWSERS_PATH=~/.playwright playwright install chromium
echo "PLAYWRIGHT_BROWSERS_PATH=$HOME/.playwright" >> .env
```

### Glassdoor 403 errors
Glassdoor actively blocks scraping. This is expected — the bot uses LinkedIn and Indeed only by default. Glassdoor is excluded from `site_name` in the scraper.

### 0 jobs scraped
LinkedIn sometimes rate-limits by IP. If running locally, try from a VPS with a European IP address. EU IPs (Germany, Netherlands) get much better results for EU job searches.

---

## CI/CD Pipeline & Security Checks

The project includes a GitLab CI pipeline (`.gitlab-ci.yml`) with the following free stages:

### Pipeline Stages

```
lint → test → security → build
```

### Create `.gitlab-ci.yml`

Add this file to the root of the repo:

```yaml
stages:
  - lint
  - test
  - security

default:
  image: python:3.12-slim   # explicit Python image — avoids ruby/default runner issues

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - .venv/

before_script:
  - python3 -m venv .venv
  - source .venv/bin/activate
  - pip install -r requirements.txt

# ── Lint ─────────────────────────────────────────────────────────────────────

flake8:
  stage: lint
  script:
    - pip install flake8
    - flake8 . --max-line-length=120 --exclude=.venv,__pycache__
  allow_failure: false

black:
  stage: lint
  script:
    - pip install black
    - black --check --line-length 120 .
  allow_failure: true   # warn but don't block — formatting is advisory

# ── Tests ─────────────────────────────────────────────────────────────────────

pytest:
  stage: test
  script:
    - pip install pytest pytest-mock pytest-cov
    - pytest tests/ -v --cov=. --cov-report=term-missing --cov-fail-under=60
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

# ── Security ──────────────────────────────────────────────────────────────────

semgrep:
  stage: security
  image: semgrep/semgrep
  script:
    - semgrep scan --config=auto --error .
  allow_failure: true

bandit:
  stage: security
  script:
    - pip install bandit
    - bandit -r . -x .venv,tests -ll   # only medium+ severity
  allow_failure: true

pip-audit:
  stage: security
  script:
    - pip install pip-audit
    - pip-audit --require-hashes -r requirements.txt
  allow_failure: true

secret-detection:
  stage: security
  script:
    - pip install detect-secrets
    - detect-secrets scan --baseline .secrets.baseline
  allow_failure: true

safety:
  stage: security
  script:
    - pip install safety
    - safety check --full-report
  allow_failure: true
```

### What Each Check Does

| Tool | What it catches | Free? |
|------|----------------|-------|
| **flake8** | PEP8 style violations, undefined variables, unused imports | ✅ |
| **black** | Code formatting consistency | ✅ |
| **pytest + coverage** | Unit tests + enforces ≥60% coverage gate | ✅ |
| **Semgrep** | SAST — insecure patterns, injection risks, hardcoded secrets | ✅ (free tier) |
| **Bandit** | Python-specific security issues (subprocess injection, weak crypto, etc.) | ✅ |
| **pip-audit** | Dependency CVE scanning (like Snyk but free) | ✅ |
| **detect-secrets** | Prevents API keys/passwords from being committed | ✅ |
| **Safety** | Known vulnerabilities in installed packages | ✅ |

> **Semgrep** is the closest free equivalent to Checkmarx for Python. Run `semgrep scan --config=p/python --config=p/secrets .` locally for a deeper scan. Checkmarx and Veracode offer free community editions but require account registration.

### Running Security Checks Locally

```bash
# Install all security tools
pip install bandit semgrep pip-audit detect-secrets safety flake8 black

# Run all checks in one go
flake8 . --max-line-length=120 --exclude=.venv
bandit -r . -x .venv,tests -ll
pip-audit -r requirements.txt
safety check
semgrep scan --config=auto .

# Scan for accidentally committed secrets
detect-secrets scan > .secrets.baseline
```

---

## 🗺️ Roadmap

Features planned in order of priority:

### ✅ Done
- LinkedIn + Indeed scraping across 6 EU countries
- LLM-powered CV matching (0–100% score)
- Tailored 2-paragraph cover letter per job
- Relocation/visa sponsorship detection
- SQLite deduplication (30-day window)
- HTML email digest via Resend
- Cron scheduling on VPS

---

### 🔜 Planned Features

#### 1. 🌐 Demo Website
A static showcase page deployed on GitHub Pages or Vercel showing:
- A live sample digest with real anonymized job data
- "How it works" visual explainer (scrape → score → cover letter → email)
- Customization guide
- Link to repo + setup instructions

No backend, no auth, zero cost. Goal: let anyone understand the project in 60 seconds without reading code.

#### 2. ⚙️ Web Config Generator
A simple web form where you fill in your CV summary, pick target countries and job titles, set your match threshold, and download a ready-to-use `config.py`. No setup knowledge required — makes the project accessible to non-developers who just want to run the bot for themselves.

#### 3. 📱 Telegram / WhatsApp Notifications
Send the digest as a Telegram message (via Bot API) in addition to or instead of email. Each job becomes a formatted message with inline "Apply" button. Useful for mobile-first users who live in their phone notifications. WhatsApp via Twilio sandbox is a stretch goal.

#### 4. 🎯 Application Tracker
Mark jobs as "Applied", "Interview", "Rejected", or "Ignored" directly from the email (via one-click links). Builds a local SQLite log of your application history. Never see a job you already applied to again. Generates a weekly stats summary: X applied, Y responses, Z% response rate.

#### 5. 👥 Multi-User SaaS Mode
Each user registers with email + CV profile. The bot runs on a shared schedule and delivers personalized digests to each user. Requires: FastAPI backend, PostgreSQL (replacing SQLite), per-user job queues, Stripe for billing (~€5/month per user). Only built if demand is proven by demo + config generator phases.

#### 6. ⚡ Parallel Scraping & Performance Optimization
Current scraping is fully sequential (~30s per query × 130 queries = 30-40 min runtime). Planned improvements:
- **Country-level parallelism** — scrape Tier 2/3 countries concurrently (they're lower traffic, less likely to be rate-limited)
- **Indeed-only fallback** — Indeed is 3-5x faster than LinkedIn per query; run Indeed in parallel while LinkedIn runs sequentially
- **Smart caching** — skip queries where no new jobs appeared in last 3 runs (stale country/term combos)
- **Incremental `hours_old`** — first run uses 72h, subsequent runs use `(hours since last run + 6h)` to avoid refetching
- **Target runtime: under 10 minutes** end-to-end

#### 7. 🤖 Easy Apply Bot (Optional / Opt-in)
For jobs marked "Easy Apply" on LinkedIn, an optional mode that auto-fills and submits the application using the generated cover letter. Strictly opt-in, rate-limited (max 5/day), runs with human-like delays. Carries ToS risk — users acknowledge this explicitly before enabling.

---

## 🤝 How to Contribute

Contributions are welcome — whether it's a bug fix, a new job board scraper, a better prompt, or a new feature from the roadmap.

### Getting Started

1. **Fork the repo** on GitLab
2. **Clone your fork**
   ```bash
   git clone https://gitlab.com/YOUR_USERNAME/job-digest.git
   cd job-digest
   ```
3. **Create a feature branch**
   ```bash
   git checkout -b feat/your-feature-name
   ```
4. **Set up your dev environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install flake8 black bandit pytest pytest-mock
   ```
5. **Make your changes**

6. **Run tests and checks before pushing**
   ```bash
   python -m pytest tests/ -v
   flake8 . --max-line-length=120 --exclude=.venv
   bandit -r . -x .venv,tests -ll
   ```

7. **Commit with a clear message**
   ```bash
   git commit -m "feat: add Indeed salary filter support"
   # Use: feat / fix / docs / refactor / test / chore
   ```

8. **Open a Merge Request** against `main`

### Contribution Guidelines

- **One feature per MR** — keep changes focused and reviewable
- **Tests required** — add or update tests for any new logic in `scrapers/`, `matching/`, `storage/`, or `email_digest/`
- **No secrets in code** — all credentials go in `.env`, never hardcoded
- **Match existing style** — the codebase uses type hints, docstrings on public functions, and f-strings
- **Update `config.py` comments** if you add a new tunable

### Good First Issues

| Area | Task |
|------|------|
| Scrapers | Add a new job board (StepStone, EuroEngineerJobs, Relocate.me) |
| Matching | Improve the scoring prompt — test with diverse job types |
| Email | Add a plain-text fallback version of the digest |
| Config | Add salary range filter support |
| Docs | Translate setup guide to German, Dutch, or Arabic |
| Tests | Increase test coverage above 80% |
| CI | Add GitHub Actions equivalent of the GitLab CI pipeline |

### Reporting Issues

Open a GitLab issue with:
- Python version (`python3 --version`)
- OS and VPS/cloud provider
- The exact error message and full stack trace
- What you were running (`python run.py --dry-run`, etc.)

---

## License

MIT — use it, fork it, make it your own.

---

*Built with Python, JobSpy, DeepSeek, Resend, and a lot of job searching frustration.*
