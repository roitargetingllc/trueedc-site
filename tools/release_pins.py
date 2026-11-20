"""Daily pin release, run by .github/workflows/release-pins.yml (no image work, no fonts needed).

Reads the items already in docs/feed.xml, adds every scheduled pin from data/pins_scheduled.json
whose release date (Israel time) has come, and rewrites docs/feed.xml and data/feed_dates.json.
Pinterest then makes Pins from the new items on its next read of the feed.

  python3 tools/release_pins.py            # release what is due today
  python3 tools/release_pins.py --check    # print what would be released, change nothing
"""
import json, sys, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import feed

MEDIA = "{http://search.yahoo.com/mrss/}content"

def main():
    site = json.loads((ROOT / "site.json").read_text())
    path = ROOT / "docs" / "feed.xml"
    items = []
    for it in ET.parse(path).getroot().iter("item"):
        items.append({"id": it.findtext("guid"), "title": it.findtext("title"), "desc": it.findtext("description"),
                      "link": it.findtext("link"), "image": it.find(MEDIA).get("url")})
    have = {i["id"] for i in items}
    new = [i for i in feed.due(site) if i["id"] not in have]
    print(f"{feed.today_israel()}: {len(items)} items in feed, {len(new)} due to release")
    for i in new: print("  +", i["id"], i["title"])
    if "--check" in sys.argv or not new: return
    path.write_text(feed.rss(site, items + new))

if __name__ == "__main__":
    main()
