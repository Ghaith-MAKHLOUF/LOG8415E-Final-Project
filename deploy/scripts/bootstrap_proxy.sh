#!/bin/bash

# Setup
## Setup environment
sudo apt update
sudo apt install -y python3-venv python3-pip
python3 -m venv .venv
source ~/.venv/bin/activate
pip install fastapi uvicorn boto3 requests pymysql pydantic

# Launch Proxy
sudo .venv/bin/uvicorn main:app --host 0.0.0.0 --port 80