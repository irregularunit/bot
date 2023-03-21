#!/bin/bash
# * Bot for Discord
# * Copyright (C) 2023 Irregular Unit
# * This software is licensed under Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
# * For more information, see README.md and LICENSE

if [ ! -d "./.venv" ]; then
  echo "Error: Virtual environment not found. Please create a virtual environment."
  exit 1
fi

source ./.venv/bin/activate

if [ ! -d "./.venv/lib/python3.11/site-packages/discord" ]; then
  pip install -r requirements.txt
fi

python src -O
