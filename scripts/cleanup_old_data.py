import os
import json
import asyncio
from datetime import datetime, timedelta
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL")


async def get_redis_client():
    """Get Redis client"""
    return redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


async def delete_key(key):
    """Delete key from Redis"""
    client = None
    try:
        client = await get_redis_client()
        result = await client.delete(key)
        return result > 0
    except Exception as e:
        print(f"Error deleting {key}: {e}")
        return False
    finally:
        if client:
            await client.close()


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


async def cleanup_old_data():
    """Remove plant data older than 7 days"""
    print("🧹 Starting cleanup of old data...")

    cutoff_date = datetime.now() - timedelta(days=7)
    print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M')}")

    # Get all plant keys
    keys = await get_keys("plant_bot:user:*")
    print(f"🔍 Found {len(keys)} plant records")

    deleted = 0
    kept = 0

    for key in keys:
        plant_json = await get_from_redis(key)
        if not plant_json:
            continue

        try:
            plant = json.loads(plant_json)
            last_watered_str = plant.get("last_watered")

            # Decide whether to delete
            should_delete = False
            reason = ""

            if not last_watered_str:
                # Never watered - check creation date
                created_at_str = plant.get("created_at")
                if created_at_str:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at < cutoff_date:
                        should_delete = True
                        reason = f"created {(datetime.now() - created_at).days} days ago, never watered"
            else:
                # Has watering data - check last watered date
                try:
                    last_watered = datetime.fromisoformat(last_watered_str)
                    if last_watered < cutoff_date:
                        should_delete = True
                        days_old = (datetime.now() - last_watered).days
                        reason = f"last watered {days_old} days ago"
                except ValueError:
                    print(f"⚠️ Invalid date format in {key}: {last_watered_str}")

            if should_delete:
                username = plant.get("username", "Unknown")
                plant_name = plant.get("plant_name", "Unknown")

                if await delete_key(key):
                    deleted += 1
                    print(f"🗑️ Deleted: {plant_name} ({username}) - {reason}")
                else:
                    print(f"❌ Failed to delete: {key}")
            else:
                kept += 1

        except Exception as e:
            print(f"⚠️ Error processing {key}: {e}")

    print(f"\n📊 Cleanup Summary:")
    print(f"  Deleted: {deleted}")
    print(f"  Kept: {kept}")
    print(f"  Total processed: {len(keys)}")


if __name__ == "__main__":
    asyncio.run(cleanup_old_data())
