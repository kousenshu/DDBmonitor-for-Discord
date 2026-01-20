import json
import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import certifi
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

STATUS_URL = "https://status.dndbeyond.com/config.json"
STATE_FILE = "timeline_state.json"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


def load_seen_timeline_ids():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_timeline_ids(timeline_ids):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(timeline_ids), f, indent=2)


def fetch_status():
    response = requests.get(
        STATUS_URL,
        timeout=10,
        verify=False
    )
    response.raise_for_status()
    return response.json()


def send_to_discord(message):
    if not WEBHOOK_URL:
        return

    payload = {"content": message[:1900]}

    requests.post(
        WEBHOOK_URL,
        json=payload,
        timeout=10,
        verify=False
    )



def format_components(components):
    return "\n".join(
        f"- {c.get('name')} ➡ {c.get('status')}"
        for c in components
    )

def format_timestamp(ts):
    if not ts:
        return "Unknown time"

    utc_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    finland_dt = utc_dt.astimezone(ZoneInfo("Europe/Helsinki"))

    return finland_dt.strftime("%H:%M:%S %d.%m.%Y %Z")

def discord_relative_time(ts):
    """
    Returns a Discord relative timestamp: <t:unix:R>
    """
    if not ts:
        return "Unknown time"

    utc_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    unix_ts = int(utc_dt.timestamp())

    return f"<t:{unix_ts}:R>"

def discord_relative_time2(ts):
    """
    Returns a Discord relative timestamp: <t:unix:F>
    """
    if not ts:
        return "Unknown time"

    utc_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    unix_ts = int(utc_dt.timestamp())

    return f"<t:{unix_ts}:F>"



def main():
    data = fetch_status()
    seen_timeline_ids = load_seen_timeline_ids()

    for incident in data.get("incidents", []):
        title = incident.get("title", "Untitled Incident")
        incident_status = incident.get("currentStatus", "unknown")
        incident_id = incident.get("id", "unknown")

        for entry in incident.get("timeline", []):
            entry_id = entry.get("id")
            if not entry_id or entry_id in seen_timeline_ids:
                continue

            created_at = format_timestamp(entry.get("createdAt"))
            relative = discord_relative_time(entry.get("createdAt"))
            discordLocalized = discord_relative_time(entry.get("createdAt"))
            components = format_components(entry.get("componentsAffected", []))
            description = entry.get("description", "No description provided.")

            # Console output
            print("\n🚨 TIMELINE UPDATE DETECTED")
            print(title)
            print(incident_id)
            print(incident_status)
            print(created_at)
            print(components)
            print(description)
            print("-" * 50)

            # Discord message (mirrors console output)
            discord_message = (
    f"## 🚨 {title} 🚨\n"
    f"At {created_at} - {relative}\n"
    f"At {discord_localized} - {relative}\n"
    f"**Status:** *{incident_status}*\n\n"
    f"### Components:\n"
    f"{components}\n\n"
    f"### Details:\n"
    f"*{description}*\n\n"
    f"[Go to incident page](https://status.dndbeyond.com/{incident_id})\n"
    f"[Go to status page](https://status.dndbeyond.com)\n"
    f"===End==="
            )

            send_to_discord(discord_message)

            seen_timeline_ids.add(entry_id)

    save_seen_timeline_ids(seen_timeline_ids)


if __name__ == "__main__":
    main()
