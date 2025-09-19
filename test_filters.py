#!/usr/bin/env python3
"""
Test all filter permutations to ensure consistency across tabs.
"""

import sys
import json
from typing import Dict, Any
from urllib.parse import urlencode

sys.path.insert(0, '/home/sysadmin/claude/signal-bot')

from web.shared.filters import GlobalFilterSystem

def test_filter_combinations():
    """Test all combinations of filters."""

    test_cases = [
        # Test 1: Default state
        {
            'name': 'Default (All Dates, All Time)',
            'params': {},
            'expected': {
                'date_mode': 'all',
                'hours': 24,
                'attachments_only': False
            }
        },

        # Test 2: Today with hours filter
        {
            'name': 'Today + Last 3 hours',
            'params': {
                'date_mode': ['today'],
                'hours': ['3']
            },
            'expected': {
                'date_mode': 'today',
                'hours': 3,
                'date': 'auto_today'  # Should be today's date
            }
        },

        # Test 3: Specific date with attachments
        {
            'name': 'Specific Date + Attachments Only',
            'params': {
                'date_mode': ['specific'],
                'date': ['2025-09-19'],
                'attachments_only': ['true']
            },
            'expected': {
                'date_mode': 'specific',
                'date': '2025-09-19',
                'attachments_only': True
            }
        },

        # Test 4: Group filter with sender
        {
            'name': 'Group + Sender + Hours',
            'params': {
                'group_id': ['test-group-id'],
                'sender_id': ['test-sender-uuid'],
                'hours': ['48']
            },
            'expected': {
                'group_id': 'test-group-id',
                'sender_id': 'test-sender-uuid',
                'hours': 48
            }
        },

        # Test 5: All filters combined
        {
            'name': 'All Filters Combined',
            'params': {
                'group_id': ['group123'],
                'sender_id': ['sender456'],
                'date_mode': ['specific'],
                'date': ['2025-09-15'],
                'hours': ['24'],
                'attachments_only': ['true']
            },
            'expected': {
                'group_id': 'group123',
                'sender_id': 'sender456',
                'date_mode': 'specific',
                'date': '2025-09-15',
                'hours': 24,
                'attachments_only': True
            }
        }
    ]

    print("Testing Filter Combinations")
    print("=" * 60)

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print("-" * 40)

        # Parse the filters
        parsed = GlobalFilterSystem.parse_query_filters(test['params'])

        # Check expected values
        passed = True
        for key, expected_value in test['expected'].items():
            actual_value = parsed.get(key)

            # Special handling for today's date
            if expected_value == 'auto_today':
                from datetime import date
                expected_value = date.today().isoformat()

            if actual_value != expected_value:
                print(f"  ❌ {key}: expected {expected_value}, got {actual_value}")
                passed = False
            else:
                print(f"  ✓ {key}: {actual_value}")

        if passed:
            print("  ✅ Test PASSED")
        else:
            print("  ❌ Test FAILED")

    print("\n" + "=" * 60)
    print("Testing URL Parameter Generation")
    print("=" * 60)

    # Test that filters generate correct URLs
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        query_string = urlencode(test['params'], doseq=True)
        print(f"  URL params: ?{query_string}")

        # Simulate what would be in the browser
        parsed = GlobalFilterSystem.parse_query_filters(test['params'])

        # Check if we can reconstruct the URL params
        reconstructed = {}
        if parsed.get('group_id'):
            reconstructed['group_id'] = parsed['group_id']
        if parsed.get('sender_id'):
            reconstructed['sender_id'] = parsed['sender_id']
        if parsed.get('date_mode'):
            reconstructed['date_mode'] = parsed['date_mode']
        if parsed.get('date'):
            reconstructed['date'] = parsed['date']
        if parsed.get('hours'):
            reconstructed['hours'] = parsed['hours']
        if parsed.get('attachments_only'):
            reconstructed['attachments_only'] = 'true'

        print(f"  Reconstructed: {reconstructed}")

if __name__ == "__main__":
    test_filter_combinations()