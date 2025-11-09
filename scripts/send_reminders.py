import os
import json
import asyncio
import random
from datetime import datetime
from telegram import Bot
import httpx

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
KV_REST_API_URL = os.getenv("KV_REST_API_URL")
KV_REST_API_TOKEN = os.getenv("KV_REST_API_TOKEN")


async def kv_get(key):
    """Get value from Vercel KV using REST API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{KV_REST_API_URL}/get/{key}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"},
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("result")
            return None
    except Exception as e:
        print(f"Error getting {key}: {e}")
        return None


async def kv_keys(pattern):
    """Get keys matching pattern from Vercel KV"""
    try:
        async with httpx.AsyncClient() as client:
            # Use SCAN command for pattern matching
            response = await client.get(
                f"{KV_REST_API_URL}/keys/{pattern}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"},
            )
            if response.status_code == 200:
                result = response.json()
                return result.get("result", [])
            return []
    except Exception as e:
        print(f"Error getting keys: {e}")
        return []


async def get_needy_plants():
    """Get plants that need watering"""
    needy = []

    # Get all plant keys
    keys = await kv_keys("plant_bot:user:*")

    for key in keys:
        plant_json = await kv_get(key)
        if not plant_json:
            continue

        try:
            plant = json.loads(plant_json)
            name = plant["plant_name"]
            username = plant["username"]

            if not plant["last_watered"]:
                needy.append(f"🌱 {name} ({username}) - Never watered!")
            else:
                last_watered = datetime.fromisoformat(plant["last_watered"])
                days_since = (datetime.now() - last_watered).days

                if days_since >= 3:
                    days_overdue = days_since - 3
                    if days_overdue == 0:
                        needy.append(f"🌱 {name} ({username}) - Due today!")
                    else:
                        needy.append(
                            f"🌱 {name} ({username}) - {days_overdue} days overdue!"
                        )
        except Exception as e:
            print(f"Error processing plant {key}: {e}")

    return needy


async def send_reminders():
    """Send reminder notifications to all registered chats"""
    print("🚀 Starting reminder check...")

    # Check if reminders are enabled
    reminders_enabled = await kv_get("plant_bot:reminders_enabled")
    if reminders_enabled == "false":
        print("ℹ️ Reminders are disabled")
        return

    # Get plants needing water
    needy_plants = await get_needy_plants()

    if not needy_plants:
        print("✅ No plants need watering")
        return

    # Build reminder message
    messages = [
        "💧 Time to water your plants!",
        "🌱 Your plants are thirsty!",
        "🚿 Watering reminder!",
        "🌿 Don't forget your green friends!",
        "💦 Plants need love!",
        "🪴 Watering time!",
    ]

    message = f"{random.choice(messages)}\n\n"
    message += "\n".join(needy_plants)
    message += "\n\nUse /watered when you've watered your plant! 🌿"

    # Get all registered chat IDs
    chat_ids_json = await kv_get("plant_bot:chat_ids")
    if not chat_ids_json:
        print("ℹ️ No chat IDs registered")
        return

    chat_ids = json.loads(chat_ids_json)
    print(f"📤 Sending reminders to {len(chat_ids)} chats")

    # Send to all chats
    bot = Bot(token=BOT_TOKEN)
    sent = 0
    failed = 0

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message)
            sent += 1
            print(f"✅ Sent to chat {chat_id}")
        except Exception as e:
            failed += 1
            print(f"❌ Failed to send to chat {chat_id}: {e}")

    print(f"\n📊 Summary:")
    print(f"  Sent: {sent}")
    print(f"  Failed: {failed}")
    print(f"  Plants needing water: {len(needy_plants)}")


if __name__ == "__main__":
    asyncio.run(send_reminders())
