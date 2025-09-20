#!/usr/bin/env python3
"""Test script to verify signal-cli path detection."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import Config, find_signal_cli_path

print("Testing signal-cli path detection...")
print("=" * 50)

# Test the find function directly
detected_path = find_signal_cli_path()
print(f"Detected signal-cli path: {detected_path}")

# Test through Config
config = Config()
print(f"Config SIGNAL_CLI_PATH: {config.SIGNAL_CLI_PATH}")

# Test if it actually works
import subprocess
try:
    result = subprocess.run([config.SIGNAL_CLI_PATH, "--version"],
                          capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print(f"✓ signal-cli is working!")
        print(f"  Version: {result.stdout.strip()}")
    else:
        print(f"✗ signal-cli not working at {config.SIGNAL_CLI_PATH}")
        print(f"  Error: {result.stderr}")
except FileNotFoundError:
    print(f"✗ signal-cli not found at {config.SIGNAL_CLI_PATH}")
except Exception as e:
    print(f"✗ Error testing signal-cli: {e}")

print("=" * 50)
print("Test complete.")