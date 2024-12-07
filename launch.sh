#!/bin/bash


## Activate Enviornment and make sure the dependencies are updated
echo "Creating python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing python required packages..."
pip install -r requirements.txt

## Launch instances and make sure the apps are working 
echo "Deploying applications and bootstrapping..."
python deploy/main.py

## Benchmark
echo "Benchmarking the applications..."
python benchmark/main.py

## Uncomment when finishing the script
echo "Cleaning up the infrastructure..."
python deploy/main.py cleanup