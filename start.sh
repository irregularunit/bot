#!/bin/bash

if [ ! -d "./.venv" ]; then
  echo "Error: Virtual environment not found. Please create a virtual environment."
  exit 1
fi

source ./.venv/bin/activate

if [ ! -d "./.venv/lib/python3.11/site-packages/discord" ]; then
  pip install -r requirements.txt
fi

python src -O
