import os
import json
import asyncio
import random
from datetime import datetime
from telegram import Bot
import redis.asyncio as redis

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")


async def get_redis_client():
    """Get Redis client"""
    return redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def get_from_redis(key):
    """Get value from Redis"""
    client = None
    try:
        client = await get_redis_client()
        value = await client.get(key)
        return value
    except Exception as e:
        print(f"Error getting {key}: {e}")
        return None
    finally:
        if client:
            await client.close()


async def get_keys(pattern):
    """Get keys matching pattern from Redis"""
    client = None
    try:
        client = await get_redis_client()
        keys = await client.keys(pattern)
        return keys
    except Exception as e:
        print(f"Error getting keys: {e}")
        return []
    finally:
        if client:
            await client.close()


async def get_needy_plants():
    """Get plants that need watering"""
    needy = []

    # Get all plant keys
    keys = await get_keys("plant_bot:user:*")

    for key in keys:
        plant_json = await get_from_redis(key)
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
    reminders_enabled = await get_from_redis("plant_bot:reminders_enabled")
    if reminders_enabled == "false":
        print("ℹ️ Reminders are disabled")
        return

    # Get plants needing water
    needy_plants = await get_needy_plants()

    if not needy_plants:
        print("✅ No plants need watering")
        return

    # Build reminder message with random greeting
    reminders = [
        "💧 Time to water your plants!",
        "🌱 Your plants are thirsty!",
        "🚿 Watering time!",
        "🌿 Don't forget your plants!",
        "💦 Plant care reminder!",
        "🪴 Your green friends need you!",
        "🌺 Plant watering alert!",
        "🍃 Time for some plant TLC!",
    ]

    # Try to read from file, fallback to default reminders
    try:
        if os.path.exists("plant_reminders.txt"):
            with open("plant_reminders.txt", "r") as file:
                lines = [line.strip() for line in file.readlines() if line.strip()]
                if lines:
                    reminders = lines
    except Exception as e:
        print(f"⚠️ Could not read plant_reminders.txt: {e}")

    message = f"{random.choice(reminders)}\n\n"
    message += "\n".join(needy_plants)
    message += "\n\nUse /watered when you've watered your plant! 🌿"

    # Get all registered chat IDs
    chat_ids_json = await get_from_redis("plant_bot:chat_ids")
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
