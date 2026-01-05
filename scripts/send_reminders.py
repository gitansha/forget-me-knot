import os
import json
import asyncio
import random
from datetime import datetime
from telegram import Bot
import redis.asyncio as redis
import ssl

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")

print("🚀 Starting reminder script...")
print(f"📝 BOT_TOKEN exists: {bool(BOT_TOKEN)}")
print(f"📝 REDIS_URL exists: {bool(REDIS_URL)}")


async def get_redis_client():
    """Get Redis client with SSL support"""
    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    # Use SSL if URL starts with rediss://
    if REDIS_URL and REDIS_URL.startswith("rediss://"):
        print("🔒 Using SSL connection")
        return redis.from_url(
            REDIS_URL, encoding="utf-8", decode_responses=True, ssl=ssl_context
        )
    else:
        print("🔓 Using non-SSL connection")
        return redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def get_from_redis(key):
    """Get value from Redis"""
    client = None
    try:
        client = await get_redis_client()
        value = await client.get(key)
        return value
    except Exception as e:
        print(f"❌ Error getting {key}: {e}")
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
        print(f"❌ Error getting keys: {e}")
        return []
    finally:
        if client:
            await client.close()


async def get_needy_plants():
    """Get plants that need watering"""
    needy = []

    print("🔍 Searching for plants that need watering...")

    # Get all plant keys
    keys = await get_keys("plant_bot:user:*")
    print(f"📊 Found {len(keys)} total plants")

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
                print(f"  ⚠️ {name} - Never watered")
            else:
                last_watered = datetime.fromisoformat(plant["last_watered"])
                days_since = (datetime.now() - last_watered).days

                if days_since >= 3:
                    days_overdue = days_since - 3
                    if days_overdue == 0:
                        needy.append(f"🌱 {name} ({username}) - Due today!")
                        print(f"  ⚠️ {name} - Due today")
                    else:
                        needy.append(
                            f"🌱 {name} ({username}) - {days_overdue} days overdue!"
                        )
                        print(f"  ⚠️ {name} - {days_overdue} days overdue")
                else:
                    print(f"  ✅ {name} - Good for {3 - days_since} more days")

        except Exception as e:
            print(f"❌ Error processing plant {key}: {e}")

    return needy


async def send_reminders():
    """Send reminder notifications to all registered chats"""
    print("=" * 60)
    print("🚀 Starting reminder check...")
    print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Check if reminders are enabled
    reminders_enabled = await get_from_redis("plant_bot:reminders_enabled")
    print(f"🔔 Reminders enabled: {reminders_enabled}")

    if reminders_enabled == "false":
        print("ℹ️ Reminders are disabled - exiting")
        return

    # Get plants needing water
    needy_plants = await get_needy_plants()

    if not needy_plants:
        print("✅ No plants need watering - no reminders sent")
        return

    print(f"\n⚠️ Found {len(needy_plants)} plants needing water")

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
        "🌵 Even cacti need water sometimes!",
        "🌻 Keep your plants happy!",
        "💚 Show your plants some love!",
        "🌴 Your botanical buddies are calling!",
    ]

    # Try to read custom reminders from file
    try:
        if os.path.exists("plant_reminders.txt"):
            with open("plant_reminders.txt", "r") as file:
                lines = [line.strip() for line in file.readlines() if line.strip()]
                if lines:
                    reminders = lines
                    print(f"📝 Loaded {len(reminders)} custom reminder messages")
    except Exception as e:
        print(f"⚠️ Could not read plant_reminders.txt: {e}")

    message = f"{random.choice(reminders)}\n\n"
    message += "\n".join(needy_plants)
    message += "\n\nUse /watered when you've watered your plant! 🌿"

    print(f"\n📝 Reminder message:\n{message}\n")

    # Get all registered chat IDs
    chat_ids_json = await get_from_redis("plant_bot:chat_ids")
    if not chat_ids_json:
        print("❌ No chat IDs registered - no one to send to!")
        return

    chat_ids = json.loads(chat_ids_json)
    print(f"📤 Sending reminders to {len(chat_ids)} chats: {chat_ids}")

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

    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"  ✅ Sent: {sent}")
    print(f"  ❌ Failed: {failed}")
    print(f"  🌱 Plants needing water: {len(needy_plants)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    try:
        asyncio.run(send_reminders())
        print("\n✅ Script completed successfully")
    except Exception as e:
        print(f"\n❌ Script failed with error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
