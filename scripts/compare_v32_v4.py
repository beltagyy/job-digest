#!/usr/bin/env python3
# Model comparison script — run manually to benchmark scoring models
# Usage: python3 scripts/compare_v32_v4.py
import os, json, time, re, sys
sys.path.insert(0, '/opt/job-digest')
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

print('Run: python3 scripts/compare_v32_v4.py')
print('Set COMPARE_KEY env var for the second model endpoint')
