#!/bin/bash

# Script to set up local virtual environment and host locally for testing
# Run this script from the root folder: bash local_startup.sh

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
