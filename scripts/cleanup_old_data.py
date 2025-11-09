import os
import json
import asyncio
from datetime import datetime, timedelta
import httpx

KV_REST_API_URL = os.getenv("KV_REST_API_URL")
KV_REST_API_TOKEN = os.getenv("KV_REST_API_TOKEN")


async def kv_get(key):
    """Get value from Vercel KV"""
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


async def kv_delete(key):
    """Delete key from Vercel KV"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{KV_REST_API_URL}/del/{key}",
                headers={"Authorization": f"Bearer {KV_REST_API_TOKEN}"},
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Error deleting {key}: {e}")
        return False


async def kv_keys(pattern):
    """Get keys matching pattern"""
    try:
        async with httpx.AsyncClient() as client:
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


async def cleanup_old_data():
    """Remove plant data older than 7 days"""
    print("🧹 Starting cleanup of old data...")

    cutoff_date = datetime.now() - timedelta(days=7)
    print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M')}")

    # Get all plant keys
    keys = await kv_keys("plant_bot:user:*")
    print(f"🔍 Found {len(keys)} plant records")

    deleted = 0
    kept = 0

    for key in keys:
        plant_json = await kv_get(key)
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

                if await kv_delete(key):
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
