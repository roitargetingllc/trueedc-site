"""RSS 2.0 feed for Pinterest auto-publish (Pinterest reads <title>, <description>, <link>, <media:content>).

Item pubDates are stored in data/feed_dates.json so an item keeps its first-seen date and new
items show up as new. Pinterest only creates Pins for items it hasn't seen.
"""
import json, datetime, html
from email.utils import format_datetime
from pathlib import Path

DATES = Path(__file__).resolve().parent.parent / "data" / "feed_dates.json"
SCHEDULED = Path(__file__).resolve().parent.parent / "data" / "pins_scheduled.json"

def mime(url):
    return "image/jpeg" if url.lower().endswith((".jpg", ".jpeg")) else "image/png"

def today_israel():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Asia/Jerusalem")).date()
    except Exception:
        return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)).date()

def due(site, today=None):
    """Scheduled pins (data/pins_scheduled.json) whose release date (Israel time) has come.
    Items not yet due stay out of the feed, so Pinterest only sees them on their day."""
    if not SCHEDULED.exists(): return []
    today = today or today_israel()
    base = site["base_url"].rstrip("/")
    return [{"id": it["id"], "title": it["title"], "desc": it["desc"], "link": it["link"], "image": base + it["image"]}
            for it in json.loads(SCHEDULED.read_text()) if datetime.date.fromisoformat(it["release"]) <= today]

def rss(site, items):
    dates = json.loads(DATES.read_text()) if DATES.exists() else {}
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    for it in items:
        dates.setdefault(it["id"], now.isoformat())
    DATES.write_text(json.dumps(dates, indent=1, sort_keys=True) + "\n")
    items = sorted(items, key=lambda i: dates[i["id"]], reverse=True)
    e = lambda s: html.escape(str(s), quote=True)
    base = site["base_url"].rstrip("/")
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:atom="http://www.w3.org/2005/Atom">',
           "<channel>", f"<title>{e(site['name'])}</title>", f"<link>{base}/</link>",
           f"<description>{e(site['tagline'])}</description>", "<language>en-us</language>",
           f'<atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>']
    for it in items:
        pub = format_datetime(datetime.datetime.fromisoformat(dates[it["id"]]))
        out += ["<item>", f"<title>{e(it['title'])}</title>", f"<link>{e(it['link'])}</link>",
                f"<description>{e(it['desc'])}</description>", f'<guid isPermaLink="false">{e(it["id"])}</guid>',
                f"<pubDate>{pub}</pubDate>",
                f'<media:content url="{e(it["image"])}" medium="image" type="{mime(it["image"])}" width="1000" height="1500"/>',
                f'<enclosure url="{e(it["image"])}" type="{mime(it["image"])}" length="0"/>', "</item>"]
    out += ["</channel>", "</rss>", ""]
    return "\n".join(out)
