#!/bin/bash
set -e

echo "Installing Python dependencies."
pip install -r requirements.txt

echo "Installing frontend dependencies."
cd frontend
npm install

echo "Setup complete."
