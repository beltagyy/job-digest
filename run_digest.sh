#!/bin/bash
cd /opt/job-digest
source .venv/bin/activate
python run.py >> /var/log/job-digest.log 2>&1
