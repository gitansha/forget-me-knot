import os
from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Check environment variables"""

        BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        REDIS_URL = os.getenv("REDIS_URL")

        # Mask sensitive data
        bot_token_masked = (
            f"{BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}" if BOT_TOKEN else None
        )

        redis_masked = None
        if REDIS_URL:
            # Mask password
            if "@" in REDIS_URL:
                parts = REDIS_URL.split("@")
                if ":" in parts[0]:
                    password = parts[0].split(":")[-1]
                    redis_masked = REDIS_URL.replace(password, "****")
            else:
                redis_masked = REDIS_URL

        result = {
            "bot_token_exists": bool(BOT_TOKEN),
            "bot_token_preview": bot_token_masked,
            "redis_url_exists": bool(REDIS_URL),
            "redis_url_preview": redis_masked,
            "all_env_keys": list(os.environ.keys()),
        }

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode("utf-8"))
