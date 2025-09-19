#!/usr/bin/env python3
"""
Systematically test different parameter formats for sendReaction
"""
import json
import socket
import time

def send_request(sock, request):
    """Send a request and get response."""
    request_str = json.dumps(request) + "\n"
    sock.send(request_str.encode('utf-8'))

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
        try:
            return json.loads(response_data.decode('utf-8').strip())
        except:
            return {"error": {"message": "Invalid JSON response"}}
    return {"error": {"message": "No response"}}

def test_reaction_formats():
    """Try every conceivable format."""
    socket_path = "/tmp/signal-cli.socket"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(socket_path)
    sock.settimeout(0.5)
    print(f"Connected to daemon\n")

    group_id = "jEVHwxmxcRjFt0PfCgiP7T7+jIJwL6W/b9oayx6BLqU="
    author_uuid = "e225c213-f176-4d26-a28b-666b4d9a72ca"
    author_phone = "+61407568949"  # If we have it
    timestamp = 1758275609218
    emoji = "👍"

    # Different author formats
    author_formats = [
        ("UUID only", author_uuid),
        ("UUID without dashes", author_uuid.replace("-", "")),
        ("Phone number", author_phone),
        ("Phone without +", author_phone[1:]),
        ("recipientAddress object", {
            "uuid": author_uuid,
            "number": author_phone
        }),
        ("UUID in dict", {"uuid": author_uuid}),
    ]

    # Different timestamp formats
    timestamp_formats = [
        ("int", timestamp),
        ("string", str(timestamp)),
        ("float", float(timestamp)),
        ("milliseconds/1000", timestamp // 1000),
    ]

    # Different parameter names
    param_variations = [
        # Standard attempt
        {
            "name": "Standard (groupId + targetAuthor + targetSentTimestamp)",
            "params": lambda a, t: {
                "groupId": group_id,
                "targetAuthor": a,
                "targetSentTimestamp": t,
                "emoji": emoji
            }
        },
        # Try targetTimestamp instead
        {
            "name": "targetTimestamp instead of targetSentTimestamp",
            "params": lambda a, t: {
                "groupId": group_id,
                "targetAuthor": a,
                "targetTimestamp": t,
                "emoji": emoji
            }
        },
        # Try with reaction instead of emoji
        {
            "name": "reaction instead of emoji",
            "params": lambda a, t: {
                "groupId": group_id,
                "targetAuthor": a,
                "targetSentTimestamp": t,
                "reaction": emoji
            }
        },
        # Try with recipient array format
        {
            "name": "recipient array format",
            "params": lambda a, t: {
                "recipient": [group_id],
                "targetAuthor": a,
                "targetSentTimestamp": t,
                "emoji": emoji
            }
        },
        # Try with account parameter
        {
            "name": "with account parameter",
            "params": lambda a, t: {
                "account": "+19095292723",
                "groupId": group_id,
                "targetAuthor": a,
                "targetSentTimestamp": t,
                "emoji": emoji
            }
        },
        # Try with remove=false
        {
            "name": "with remove=false",
            "params": lambda a, t: {
                "groupId": group_id,
                "targetAuthor": a,
                "targetSentTimestamp": t,
                "emoji": emoji,
                "remove": False
            }
        },
        # Try author as targetAuthorUuid
        {
            "name": "targetAuthorUuid instead of targetAuthor",
            "params": lambda a, t: {
                "groupId": group_id,
                "targetAuthorUuid": a,
                "targetSentTimestamp": t,
                "emoji": emoji
            }
        },
        # Try timestamp as just timestamp
        {
            "name": "timestamp instead of targetSentTimestamp",
            "params": lambda a, t: {
                "groupId": group_id,
                "targetAuthor": a,
                "timestamp": t,
                "emoji": emoji
            }
        },
    ]

    success_count = 0
    test_count = 0

    for param_var in param_variations:
        print(f"\n{'='*60}")
        print(f"Testing: {param_var['name']}")
        print(f"{'='*60}")

        # Test with first author and timestamp format
        author_name, author_val = author_formats[0]
        ts_name, ts_val = timestamp_formats[0]

        test_count += 1
        request = {
            "jsonrpc": "2.0",
            "method": "sendReaction",
            "params": param_var["params"](author_val, ts_val),
            "id": str(test_count)
        }

        print(f"Params: {json.dumps(request['params'], indent=2)}")
        response = send_request(sock, request)

        if "error" in response:
            error_msg = response["error"].get("message", "Unknown error")
            print(f"❌ {error_msg}")

            # If it's not "No recipients given", try different author formats
            if "No recipients" not in error_msg and "null" not in error_msg.lower():
                print("\nTrying different author formats...")
                for author_name, author_val in author_formats[1:]:
                    test_count += 1
                    request["params"] = param_var["params"](author_val, ts_val)
                    request["id"] = str(test_count)
                    print(f"  - {author_name}: ", end="")
                    response = send_request(sock, request)
                    if "error" not in response:
                        print(f"✅ SUCCESS!")
                        success_count += 1
                        return True
                    else:
                        print(response["error"].get("message", "Failed"))
        else:
            print(f"✅ SUCCESS! Response: {json.dumps(response, indent=2)}")
            success_count += 1
            return True

    sock.close()
    print(f"\n{'='*60}")
    print(f"Tested {test_count} combinations: {success_count} successful")
    return success_count > 0

if __name__ == "__main__":
    if test_reaction_formats():
        print("\n🎉 Found working format for reactions!")
    else:
        print("\n😞 No working format found - might be a signal-cli bug")