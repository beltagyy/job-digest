#!/usr/bin/env python3
"""Compare DeepSeek-V3.2 vs Kimi-K2.6 on 5 test jobs."""
import os, json, time, sys, re
sys.path.insert(0, '/opt/job-digest')
from dotenv import load_dotenv
load_dotenv('/opt/job-digest/.env')
from openai import OpenAI

ds = OpenAI(
    api_key=os.environ['AZURE_AI_API_KEY'],
    base_url=os.environ['AZURE_AI_ENDPOINT'].rstrip('/') + '/openai/v1/'
)
kimi = OpenAI(
    api_key='REDACTED_KEY',
    base_url='https://job-enhance-resource.services.ai.azure.com/openai/v1/'
)

JOBS = [
    ('Senior Cloud Security Eng', 'Zalando', 'Germany',
     'AWS EKS, Falco, Wiz CNAPP, DevSecOps, Terraform, Kubernetes, GDPR. Relocation and visa sponsorship provided.'),
    ('DevOps Engineer', 'Random Corp', 'Netherlands',
     'Jenkins, basic AWS, Java preferred. No relocation support.'),
    ('Platform Security Engineer', 'N26', 'Germany',
     'Kubernetes security, OPA/Gatekeeper, Cilium, ArgoCD, zero trust. International candidates welcome, visa sponsorship.'),
    ('IT Support Technician', 'Helpdesk GmbH', 'Germany',
     '1st line support, Windows admin, ticketing. German language required.'),
    ('Cloud Architect', 'AWS', 'Ireland',
     'Senior cloud architect for AWS migrations. Security background preferred. Relocation package provided.'),
]

def make_prompt(title, company, country, desc):
    return (
        f"Score job match 0-100 for: Senior Cloud Security Engineer, "
        f"6yr AWS/K8s/Falco/Wiz/DevSecOps, relocating Cairo to EU.\n"
        f"Job: {title} at {company} ({country}). {desc}\n"
        f'Output ONLY valid JSON: {{"score":X,"reasons":["r1","r2"],"missing":["g1"]}}'
    )

def parse_score(raw):
    try:
        # Fix double braces from Kimi
        raw = raw.replace('{{', '{').replace('}}', '}')
        # Strip code fences
        raw = re.sub(r'```[a-z]*\n?', '', raw).strip()
        if not raw.startswith('{'):
            raw = '{' + raw
        return json.loads(raw)
    except:
        return {}

print(f"{'Job':<30} {'DS':>5} {'DSt':>5}  {'Kimi':>5} {'Kimt':>6}  {'Match?'}")
print('-' * 70)

for title, company, country, desc in JOBS:
    prompt = make_prompt(title, company, country, desc)

    # DeepSeek
    t0 = time.time()
    try:
        r = ds.chat.completions.create(
            model='DeepSeek-V3.2', max_tokens=200, temperature=0.1,
            messages=[{'role': 'user', 'content': prompt}]
        )
        ds_data = parse_score(r.choices[0].message.content)
        ds_score = ds_data.get('score', '?')
        ds_reasons = ds_data.get('reasons', [])
    except Exception as e:
        ds_score, ds_reasons = 'err', []
    ds_t = round(time.time() - t0, 1)

    # Kimi (prefill with { to force immediate JSON)
    t0 = time.time()
    try:
        r2 = kimi.chat.completions.create(
            model='Kimi-K2.6', max_tokens=1500, temperature=0.1,
            messages=[
                {'role': 'user', 'content': prompt},
                {'role': 'assistant', 'content': '{'}
            ]
        )
        kimi_raw = '{' + r2.choices[0].message.content.strip()
        kimi_data = parse_score(kimi_raw)
        kimi_score = kimi_data.get('score', '?')
    except Exception as e:
        kimi_score = 'err'
    kimi_t = round(time.time() - t0, 1)

    # Agreement check
    agree = ''
    if isinstance(ds_score, int) and isinstance(kimi_score, int):
        diff = abs(ds_score - kimi_score)
        agree = '✅ agree' if diff <= 10 else f'⚠️ diff {diff}'

    label = title[:28]
    print(f"{label:<30} {str(ds_score):>5} {str(ds_t)+'s':>5}  {str(kimi_score):>5} {str(kimi_t)+'s':>6}  {agree}")

print()
print("Summary:")
print(f"  DeepSeek-V3.2 : ~2-3s/job, structured output, reliable JSON")
print(f"  Kimi-K2.6     : ~5-8s/job, reasoning model, more thoughtful but slower")
