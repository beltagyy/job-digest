#!/usr/bin/env python3
"""Called by CI to check detect-secrets output. Exits 1 if secrets found."""
import json
import sys

with open("/tmp/secrets.json") as f:
    data = json.load(f)

results = data.get("results", {})
total = sum(len(v) for v in results.values())
print(f"Potential secrets found: {total}")

if total > 0:
    for path, findings in results.items():
        for finding in findings:
            print(f"  {path}: {finding.get('type')} at line {finding.get('line_number')}")
    sys.exit(1)

print("No secrets detected.")
