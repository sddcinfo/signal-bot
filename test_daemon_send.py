#!/usr/bin/env python3
"""
Test daemon bidirectionality - can it send messages?
"""
import json
import socket
import time

def test_send_message():
    """Test if daemon can send a regular message."""
    socket_path = "/tmp/signal-cli.socket"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(socket_path)
    sock.settimeout(5.0)
    print(f"Connected to daemon at {socket_path}")

    # Test sending a regular message to prove daemon works
    group_id = "jEVHwxmxcRjFt0PfCgiP7T7+jIJwL6W/b9oayx6BLqU="

    request = {
        "jsonrpc": "2.0",
        "method": "send",
        "params": {
            "groupId": group_id,
            "message": "Test from daemon - proving bidirectionality works!"
        },
        "id": str(int(time.time() * 1000))
    }

    print(f"Sending message via daemon...")
    print(f"Request: {json.dumps(request, indent=2)}")

    request_str = json.dumps(request) + "\n"
    sock.send(request_str.encode('utf-8'))

    # Wait for response
    response_data = b""
    start_time = time.time()
    while time.time() - start_time < 10:
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

        if "error" in response:
            print(f"❌ Error: {response['error']}")
        else:
            print("✅ Message sent successfully!")
            return True
    else:
        print("❌ No response received")

    sock.close()
    return False

if __name__ == "__main__":
    success = test_send_message()
    if success:
        print("\n✅ Daemon IS bidirectional - it can send messages!")
        print("The issue is specifically with sendReaction parameters/format")
    else:
        print("\n❌ Daemon failed to send message")