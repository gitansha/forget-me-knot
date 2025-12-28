import os
import json
import asyncio
import redis.asyncio as redis
from http.server import BaseHTTPRequestHandler

REDIS_URL = os.getenv("REDIS_URL")


async def test_redis_connection():
    """Test Redis connection and return results"""

    results = {
        "redis_url_exists": bool(REDIS_URL),
        "redis_url_preview": None,
        "connection_test": "not_tested",
        "ping_test": "not_tested",
        "write_test": "not_tested",
        "read_test": "not_tested",
        "error": None,
    }

    if not REDIS_URL:
        results["error"] = "REDIS_URL environment variable is not set"
        return results

    # Mask password for security
    if "@" in REDIS_URL:
        parts = REDIS_URL.split("@")
        if ":" in parts[0]:
            password = parts[0].split(":")[-1]
            results["redis_url_preview"] = REDIS_URL.replace(password, "****")
    else:
        results["redis_url_preview"] = REDIS_URL

    client = None

    try:
        # Test 1: Create connection
        results["connection_test"] = "attempting"
        client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        results["connection_test"] = "success"

        # Test 2: Ping
        results["ping_test"] = "attempting"
        ping_response = await client.ping()
        results["ping_test"] = f"success (response: {ping_response})"

        # Test 3: Write
        results["write_test"] = "attempting"
        await client.set("test:vercel:connection", "working")
        results["write_test"] = "success"

        # Test 4: Read
        results["read_test"] = "attempting"
        value = await client.get("test:vercel:connection")
        results["read_test"] = f"success (value: {value})"

        # Cleanup
        await client.delete("test:vercel:connection")

        results["overall_status"] = "✅ ALL TESTS PASSED - Redis is working!"

    except redis.ConnectionError as e:
        results["connection_test"] = "failed"
        results["error"] = f"Connection Error: {str(e)}"
        results["overall_status"] = "❌ CONNECTION FAILED"

    except redis.AuthenticationError as e:
        results["error"] = f"Authentication Error: {str(e)}"
        results["overall_status"] = (
            "❌ AUTHENTICATION FAILED - Check password in REDIS_URL"
        )

    except redis.TimeoutError as e:
        results["error"] = f"Timeout Error: {str(e)}"
        results["overall_status"] = "❌ TIMEOUT - Redis server not responding"

    except Exception as e:
        results["error"] = f"Unexpected Error: {str(e)}"
        results["overall_status"] = "❌ ERROR"

    finally:
        if client:
            try:
                await client.close()
            except:
                pass

    return results


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Test Redis connection"""

        try:
            # Run async test
            results = asyncio.run(test_redis_connection())

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()

            response = json.dumps(results, indent=2, ensure_ascii=False)
            self.wfile.write(response.encode("utf-8"))

        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            error_response = {"error": str(e), "overall_status": "❌ ENDPOINT ERROR"}
            self.wfile.write(json.dumps(error_response, indent=2).encode("utf-8"))
