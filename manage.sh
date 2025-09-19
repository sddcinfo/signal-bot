#!/bin/bash
# Wrapper script for manage.py
# Provides backward compatibility for shell-based usage

# Use virtual environment python if it exists
if [ -f "venv/bin/python" ]; then
    exec venv/bin/python manage.py "$@"
else
    exec python3 manage.py "$@"
fi