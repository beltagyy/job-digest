# config.py
"""
Central configuration for the job digest bot.
Edit this file to change search targets, scoring weights, or filters.
"""

# Job search keywords
SEARCH_TERMS = [
    "Cloud Security Engineer",    # core — catches senior/lead/junior variants
    "DevSecOps Engineer",         # devsecops + platform security overlap
    "Cloud Engineer",             # broad — infra/automation/systems all show up
    "DevOps Engineer",            # wide net, AI filters out weak matches
    "Platform Engineer",          # SRE/infra/k8s overlap
    "Cloud Architect",            # solution architect + cloud lead roles
    "Kubernetes Engineer",        # container/k8s specific
    "Site Reliability Engineer",  # SRE with cloud/security angle
]

# Companies known to actively sponsor visas and support relocation to EU.
# Used ONLY to add a "⭐ Known Relocator" badge in the email digest —
# NOT used to filter out other companies. Any company can still appear
# and get a high score if it matches your CV well.
KNOWN_RELOCATORS = {
    # Big Tech
    "amazon", "aws", "google", "microsoft", "meta", "apple",
    "salesforce", "oracle", "ibm", "sap",
    # Fintech scale-ups
    "adyen", "bolt", "wise", "revolut", "n26", "monzo",
    "stripe", "klarna", "sumup", "mollie", "checkout.com",
    "bunq", "paysafe", "mambu", "solaris",
    # Marketplaces / Consumer
    "ebay", "zalando", "booking.com", "booking", "delivery hero",
    "trivago", "hellofresh", "aboutyou", "windtre",
    # Cloud / Infra / Security
    "cloudflare", "hashicorp", "datadog", "dynatrace",
    "crowdstrike", "palo alto", "wiz", "snyk", "elastic",
    "grafana", "gitlab", "github", "atlassian",
    # EU Big Tech
    "siemens", "bosch", "deutsche telekom", "telefonica",
    "criteo", "ovhcloud", "teamviewer", "personio", "celonis",
    "bmw", "volkswagen", "continental", "mercedes",
    # Unicorns / well-funded startups known for relocation
    "spotify", "skyscanner", "wise", "messagebird",
    "contentful", "signavio", "sennder", "gorillas", "flink",
    "taxfix", "trade republic", "auto1", "homeday", "clark",
    "sumup", "moss", "billie", "solarisbank", "penta",
    # Consulting / Enterprise known for visa sponsorship
    "deloitte", "accenture", "thoughtworks", "capgemini",
    "pwc", "kpmg", "infosys", "wipro", "tata",
}

# Target countries & cities
# Each entry: (country_code_for_jobspy, display_name, city_list)
SEARCH_LOCATIONS = [
    # Tier 1 — primary targets (highest job density, strong relocation culture)
    ("germany",        "Germany",        ["Berlin", "Munich", "Frankfurt", "Hamburg", "Dusseldorf"]),
    ("netherlands",    "Netherlands",    ["Amsterdam", "Rotterdam", "The Hague", "Eindhoven"]),
    ("ireland",        "Ireland",        ["Dublin", "Cork"]),
    # Tier 2 — growing tech hubs, lower cost, active relocation support
    ("czech republic", "Czech Republic", ["Prague", "Brno"]),
    ("poland",         "Poland",         ["Warsaw", "Krakow"]),
    ("austria",        "Austria",        ["Vienna", "Graz"]),
    ("spain",          "Spain",          ["Barcelona", "Madrid"]),
    ("estonia",        "Estonia",        ["Tallinn"]),
    # Tier 3 — emerging, worth monitoring
    ("hungary",        "Hungary",        ["Budapest"]),
    ("croatia",        "Croatia",        ["Zagreb"]),
    ("bulgaria",       "Bulgaria",       ["Sofia"]),
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
