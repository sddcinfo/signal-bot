#!/usr/bin/env python3
"""
Test different JSON-RPC formats for sending reactions
"""
import json
import socket
import time

def test_reaction_formats():
    """Try different parameter formats for sendReaction."""

    socket_path = "/tmp/signal-cli.socket"

    # Connect to daemon
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(socket_path)
    sock.settimeout(5.0)
    print(f"Connected to daemon at {socket_path}")

    # Test data - use the latest message
    # Try with the account's own number instead of group
    bot_phone = "+19095292723"
    group_id = "jEVHwxmxcRjFt0PfCgiP7T7+jIJwL6W/b9oayx6BLqU="
    author_uuid = "e225c213-f176-4d26-a28b-666b4d9a72ca"
    timestamp = 1758275609218
    emoji = "👍"

    formats_to_test = [
        # Format 1: recipient as list with group ID
        {
            "name": "recipient as list",
            "params": {
                "recipient": [group_id],
                "targetAuthor": author_uuid,
                "targetSentTimestamp": timestamp,
                "emoji": emoji
            }
        },
        # Format 2: recipient as string
        {
            "name": "recipient as string",
            "params": {
                "recipient": group_id,
                "targetAuthor": author_uuid,
                "targetSentTimestamp": timestamp,
                "emoji": emoji
            }
        },
        # Format 3: groupId parameter
        {
            "name": "groupId parameter",
            "params": {
                "groupId": group_id,
                "targetAuthor": author_uuid,
                "targetSentTimestamp": timestamp,
                "emoji": emoji
            }
        },
        # Format 4: group parameter (no Id suffix)
        {
            "name": "group parameter",
            "params": {
                "group": group_id,
                "targetAuthor": author_uuid,
                "targetSentTimestamp": timestamp,
                "emoji": emoji
            }
        },
        # Format 5: try with account parameter
        {
            "name": "with account parameter",
            "params": {
                "account": bot_phone,
                "recipient": [group_id],
                "targetAuthor": author_uuid,
                "targetSentTimestamp": timestamp,
                "emoji": emoji
            }
        },
        # Format 6: try quoting flag
        {
            "name": "with quoting flag",
            "params": {
                "recipient": [group_id],
                "targetAuthor": author_uuid,
                "targetSentTimestamp": timestamp,
                "emoji": emoji,
                "quoting": False
            }
        }
    ]

    for test_format in formats_to_test:
        print(f"\n{'='*60}")
        print(f"Testing: {test_format['name']}")
        print(f"{'='*60}")

        request = {
            "jsonrpc": "2.0",
            "method": "sendReaction",
            "params": test_format['params'],
            "id": str(int(time.time() * 1000))
        }

        print(f"Request: {json.dumps(request, indent=2)}")

        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            sock.send(request_str.encode('utf-8'))

            # Wait for response
            response_data = b""
            start_time = time.time()
            while time.time() - start_time < 3:
                try:
                    chunk = sock.recv(4096)
                    if chunk:
                        response_data += chunk
                        if b"\n" in response_data:
                            break
                except socket.timeout:
                    continue

            if response_data:
                response = json.loads(response_data.decode('utf-8').strip())
                print(f"Response: {json.dumps(response, indent=2)}")

                if "error" not in response:
                    print(f"✅ SUCCESS with format: {test_format['name']}")
                    return True
                else:
                    print(f"❌ Error: {response['error']['message']}")
            else:
                print("❌ No response received")

        except Exception as e:
            print(f"❌ Exception: {e}")

    sock.close()
    return False

if __name__ == "__main__":
    success = test_reaction_formats()
    if not success:
        print("\n❌ All formats failed")
    else:
        print("\n✅ Found working format!")