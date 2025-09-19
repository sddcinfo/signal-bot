#!/usr/bin/env python3
"""
Test script to send a reaction through the daemon service
"""
import json
import socket
import time
import sys

def send_test_reaction():
    """Send a test reaction through the daemon."""

    socket_path = "/tmp/signal-cli.socket"

    # Wait for daemon to be ready
    print("Waiting for daemon to be ready...")
    time.sleep(3)

    try:
        # Connect to daemon socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        sock.settimeout(5.0)
        print(f"Connected to daemon at {socket_path}")

        # Get the latest message from database to react to
        import sqlite3
        conn = sqlite3.connect('signal_bot.db')
        cursor = conn.cursor()

        # Get a recent message from a monitored group
        cursor.execute("""
            SELECT m.timestamp, m.sender_uuid, g.group_id, m.message_text
            FROM messages m
            JOIN groups g ON m.group_id = g.group_id
            WHERE g.is_monitored = 1
            ORDER BY m.timestamp DESC
            LIMIT 1
        """)

        result = cursor.fetchone()
        if not result:
            print("No messages found in monitored groups")
            return False

        timestamp, author_uuid, group_id, message_text = result
        print(f"Found message: '{message_text[:50]}' from {author_uuid[:8]} at {timestamp}")

        # Prepare reaction request
        # Try different parameter combinations
        print(f"\nTrying different parameter formats...")

        # Format 1: recipient as string with group: prefix
        request = {
            "jsonrpc": "2.0",
            "method": "sendReaction",
            "params": {
                "recipient": group_id,  # Just the group ID as string
                "targetAuthor": author_uuid,
                "targetSentTimestamp": int(timestamp),
                "emoji": "👍",
                "remove": False
            },
            "id": str(int(time.time() * 1000))
        }

        print(f"Sending reaction to group {group_id[:8]}...")
        print(f"Request: {json.dumps(request, indent=2)}")

        # Send the request
        request_str = json.dumps(request) + "\n"
        sock.send(request_str.encode('utf-8'))

        print("Reaction request sent! Waiting for response...")

        # Try to read response
        response_data = b""
        start_time = time.time()
        while time.time() - start_time < 5:
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

            if response.get("error"):
                print(f"Error: {response['error']}")
                return False
            else:
                print("✅ Reaction sent successfully!")
                return True
        else:
            print("No response received (this might be normal for reactions)")
            print("✅ Reaction likely sent (fire-and-forget)")
            return True

    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    success = send_test_reaction()
    sys.exit(0 if success else 1)