#!/bin/bash

PYTHON=python3.11

if [ ! -d "./.venv" ]; then
    echo "No virtual environment found. Creating virtual environment..."
    $PYTHON -m venv .venv
    source .venv/bin/activate
    $PYTHON -m pip install --upgrade pip
else
    source .venv/bin/activate
fi

if [ ! -d "./.venv/lib/python3.11/site-packages/discord" ]; then
    echo "Installing requirements..."
    $PYTHON -m pip install -r requirements.txt
fi

$PYTHON -m src -O
