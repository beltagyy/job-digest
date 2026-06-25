# 🔍 Job Digest Bot

> A personal AI-powered job search assistant that scrapes LinkedIn and Indeed every 2 days, scores each listing against your CV using an LLM, and emails you a curated digest with tailored cover letters — so you only see roles worth your time.

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

## Tech Stack

| Layer | Tool | Cost |
|-------|------|------|
| Scraping | [JobSpy](https://github.com/Bunsly/JobSpy) (LinkedIn + Indeed) | Free |
| AI Scoring & Cover Letters | Any OpenAI-compatible LLM | Pay-per-use |
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
├── config.py                           # ⚙️  All tunables: CV profile, search targets, thresholds
├── requirements.txt
├── .env.example                        # Template for secrets
│
├── scrapers/
│   ├── jobspy_scraper.py               # LinkedIn + Indeed via JobSpy
│   └── xing_scraper.py                 # Xing via Playwright (DE/AT/CZ/HU)
│
├── matching/
│   └── scorer.py                       # LLM scoring + cover letter generation
│
├── storage/
│   └── db.py                           # SQLite deduplication
│
├── email_digest/
│   ├── renderer.py                     # Jinja2 HTML rendering
│   ├── sender.py                       # Resend.com delivery
│   └── templates/
│       └── digest.html.j2              # Email HTML template
│
└── tests/
    ├── test_db.py
    ├── test_scorer.py
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
| LLM scoring (DeepSeek-V3.2 via Azure) | ~300 jobs × 2 runs/week | ~$0.10–0.50/month |
| Resend email | 2 emails/week | Free (3,000/month limit) |
| **Total** | | **~$0.50–1/month** (after credits) |

> Using **Azure for Startups** ($1,000 credit) or **Oracle Cloud Always Free** (Frankfurt VM): **$0/month** for 12+ months.

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

## License

MIT — use it, fork it, make it your own.

---

*Built with Python, JobSpy, DeepSeek, Resend, and a lot of job searching frustration.*
