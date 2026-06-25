# config.py
"""
Central configuration for the job digest bot.
Edit this file to change search targets, scoring weights, or filters.
"""

# Job search keywords
SEARCH_TERMS = [
    "Senior Cloud Security Engineer",
    "DevSecOps Engineer",
    "Kubernetes Security",
]

# Target countries & cities
# Each entry: (country_code_for_jobspy, display_name, city_list)
SEARCH_LOCATIONS = [
    ("germany",        "Germany",        ["Germany", "Berlin", "Munich", "Frankfurt", "Hamburg"]),
    ("netherlands",    "Netherlands",    ["Netherlands", "Amsterdam", "Rotterdam", "The Hague"]),
    ("czech republic", "Czech Republic", ["Czech Republic", "Prague"]),
    ("hungary",        "Hungary",        ["Hungary", "Budapest"]),
    ("austria",        "Austria",        ["Austria", "Vienna"]),
    ("ireland",        "Ireland",        ["Ireland", "Dublin"]),
]

# Jobs scoring below this (0-100) are excluded from the digest entirely
MIN_SCORE_TO_INCLUDE = 70

# If ANY of these appear in the job description, the job is flagged as relocation-friendly
RELOCATION_KEYWORDS = [
    "relocation", "relocation assistance", "relocation support", "relocation package",
    "visa sponsorship", "visa support", "work permit", "work visa",
    "we sponsor", "sponsorship provided", "sponsorship available",
    "help with relocation", "moving allowance", "moving expenses", "expat",
    "international candidates", "open to candidates from abroad",
    "candidates outside", "non-EU candidates", "non-eu",
    "umzugshilfe", "umzugskosten", "relokace", "relokácia",
    "willing to relocate", "open to relocation", "support relocation",
]

# Your CV profile — used for AI matching prompt
CV_PROFILE = """
Mohamed ElBeltagy - Senior Cloud Security Engineer
6+ years experience: AWS, Azure, GCP
Core strengths:
- Kubernetes security (EKS, AKS, Talos Linux, RKE2, Cilium/eBPF, Falco, OPA/Gatekeeper)
- DevSecOps & GitOps (ArgoCD, GitLab CI/CD, GitHub Actions, Terraform, Pulumi)
- Cloud security posture (Wiz CNAPP, SPIFFE/SPIRE, Vault, Zero Trust, mTLS)
- Compliance & policy (GDPR, NIS2, ISO 27001, CIS Benchmarks, Trivy, Checkov)
- Cloud platforms (AWS EKS/EC2/S3/Lambda/IAM, Azure AKS/Private Link/NSG/APIM)
- Programming (Python, Go, Bash, PowerShell, Java)
- Security tooling (Falco, Trivy, Checkov, Sentinel, RBAC, Pod Security Standards)
Seeking: Senior Cloud Security / DevSecOps / Platform Security roles
Location: Relocating from Cairo to EU (Germany, Netherlands, Czech, Hungary, Austria, Ireland)
Languages: Arabic (native), English (fluent), German B1
"""

# Jobs seen within this many days are never re-shown in the digest
DEDUP_DAYS = 30
