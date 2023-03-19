#!/bin/bash

if [ ! -x "$0" ]; then
  echo "Error: Script does not have execution permission. Please run 'chmod +x $0' to grant execution permission."
  exit 1
fi

if [ ! -d "./.venv" ]; then
  echo "Error: Virtual environment not found. Please create a virtual environment in the .venv directory."
  exit 1
fi

source ./.venv/bin/activate

if [ ! -d "./.venv/lib/python3.11/site-packages/discord" ]; then
  pip install -r requirements.txt
fi

python src -O