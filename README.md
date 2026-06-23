# Job Digest Bot

Scrapes LinkedIn, Indeed, Glassdoor, and Xing every 2 days for Cloud Security / DevSecOps roles
in Germany, Netherlands, Czech Republic, Hungary, Austria, and Ireland.
Uses Claude Haiku to score each job against your CV. Sends a rich HTML digest email.

## Stack
- **Scraping:** JobSpy (LinkedIn/Indeed/Glassdoor) + Playwright (Xing)
- **AI Matching:** Claude Haiku (`claude-haiku-4-5-20251001`)
- **Dedup:** SQLite
- **Email:** Resend.com free tier
- **Infra:** Hetzner CX11 VPS, EUR 3.79/month

## Setup

### Local dev
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env && nano .env   # add your API keys
```

### Run locally
```bash
python run.py --dry-run --no-xing   # quick test, no email sent
python run.py --dry-run             # full test with Xing, no email sent
python run.py                       # real run - sends email
```

### VPS (Hetzner)
See the full implementation plan for complete VPS setup instructions.

Cron job (runs at 08:00 AM every 2 days):
```
0 8 */2 * * /opt/job-digest/run_digest.sh
```

## Configuration
Edit `config.py` to change:
- `SEARCH_TERMS` - job title keywords
- `SEARCH_LOCATIONS` - target countries
- `MIN_SCORE_TO_INCLUDE` - AI match threshold (0-100)
- `CV_PROFILE` - your CV summary used for AI matching

## Tests
```bash
python -m pytest tests/ -v
```

## Cost estimate
- Hetzner CX11: ~EUR 3.79/month
- Claude Haiku: ~$0.0008/job scored, ~$0.02-0.05 per run
- Resend: free tier (3,000 emails/month)
- **Total: ~EUR 4-5/month**
