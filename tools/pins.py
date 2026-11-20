"""Text-only Pinterest pins (1000x1500 PNG). No product photos, so no image-rights issues.

One pin per guide, plus one per product pointing at that product on its best guide.
Returns a list of dicts used by feed.py (newest first is fine; Pinterest reads every new item).
"""
import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 1500
BG, INK, ACCENT, MUTED = (20, 20, 19), (241, 239, 233), (249, 115, 22), (169, 165, 156)
FONT_DIR = "/usr/share/fonts/opentype/inter/"

def font(weight, size):
    for name in (f"Inter-{weight}.otf", "Inter-Bold.otf"):
        try: return ImageFont.truetype(FONT_DIR + name, size)
        except OSError: pass
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)

def wrap(draw, text, f, width):
    words, lines, line = text.split(), [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textlength(test, font=f) <= width: line = test
        else: lines.append(line); line = w
    if line: lines.append(line)
    return lines

def fit(draw, text, weight, max_size, width, max_lines):
    size = max_size
    while size > 40:
        f = font(weight, size)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines: return f, lines, size
        size -= 6
    f = font(weight, 40); return f, wrap(draw, text, f, width), 40

def make_pin(path, kicker, headline, sub, cta="trueedc.com"):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    m = 80
    d.rectangle([0, 0, W, 18], fill=ACCENT)
    d.text((m, 110), "TRUE", font=font("Black", 56), fill=INK)
    d.text((m + d.textlength("TRUE", font=font("Black", 56)), 110), "EDC", font=font("Black", 56), fill=ACCENT)
    y = 330
    kf = font("Bold", 38)
    for line in wrap(d, kicker.upper(), kf, W - 2 * m):
        d.text((m, y), line, font=kf, fill=ACCENT); y += 50
    y += 30
    hf, hlines, hs = fit(d, headline, "Black", 120, W - 2 * m, 6)
    for line in hlines:
        d.text((m, y), line, font=hf, fill=INK); y += int(hs * 1.12)
    y += 40
    sf = font("Medium", 44)
    room = (H - 270 - y) // 60  # lines that fit above the button
    slines = wrap(d, sub, sf, W - 2 * m)
    if room < len(slines):
        slines = slines[:max(room, 0)]
        if slines:
            last = slines[-1]
            while last and d.textlength(last + "...", font=sf) > W - 2 * m:
                last = last.rsplit(" ", 1)[0] if " " in last else last[:-1]
            slines[-1] = last.rstrip(",.;:") + "..."
    for line in slines:
        d.text((m, y), line, font=sf, fill=MUTED); y += 60
    d.rounded_rectangle([m, H - 240, W - m, H - 130], radius=20, fill=ACCENT)
    cf = font("Bold", 46)
    tw = d.textlength(cta, font=cf)
    d.text(((W - tw) / 2, H - 213), cta, font=cf, fill=BG)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)

def make_all(site, products, guides, out_dir, posts=()):
    base = site["base_url"].rstrip("/")
    items, seen = [], set()
    for g in guides:
        fn = f"guide-{g['slug']}.png"
        checked = max(products[i]["checked"] for i in g["products"] if i in products)
        checked = datetime.date.fromisoformat(checked).strftime("%b %-d, %Y")
        desc = g["description"].replace("{checked}", checked)
        kicker = {"holiday": "Holiday gift guide", "evergreen": "EDC buying guide"}.get(g.get("season"), "EDC guide")
        make_pin(out_dir / fn, kicker, g["title"], desc, "See the picks at trueedc.com")
        items.append({"id": fn, "title": g["title"], "desc": desc + " Links may earn us a commission. #ad",
                      "link": f"{base}/{g['slug']}/", "image": f"{base}/pins/{fn}"})
    for g in guides:
        for pid in g["products"]:
            if pid in seen or pid not in products: continue
            seen.add(pid)
            p = products[pid]
            fn = f"pick-{pid}.png"
            kicker = "Under $25 EDC pick" if p["price"] <= 25 else ("Under $50 EDC pick" if p["price"] <= 50 else "Worth the splurge")
            make_pin(out_dir / fn, kicker, p["name"], p["pitch"], "Why we picked it: trueedc.com")
            items.append({"id": fn, "title": f"{p['name']}: {kicker}", "desc": p["pitch"] + " Links may earn us a commission. #ad",
                          "link": f"{base}/{g['slug']}/#{pid}", "image": f"{base}/pins/{fn}"})
    for po in posts:
        fn = f"post-{po['slug']}.png"
        make_pin(out_dir / fn, f"EDC {po['tag'].lower()} guide" if po["tag"] != "Gifts" else "EDC gift guide",
                 po["title"], po["description"], "Read it at trueedc.com")
        items.append({"id": fn, "title": po["title"], "desc": po["description"] + " Links may earn us a commission. #ad",
                      "link": f"{base}/blog/{po['slug']}/", "image": f"{base}/pins/{fn}"})
        for sec in po["sections"]:
            for pid in sec.get("products", []):
                if pid in seen or pid not in products: continue
                seen.add(pid)
                pr = products[pid]
                fn = f"pick-{pid}.png"
                kicker = "Under $25 EDC pick" if pr["price"] <= 25 else ("Under $50 EDC pick" if pr["price"] <= 50 else "Worth the splurge")
                make_pin(out_dir / fn, kicker, pr["name"], pr["pitch"], "Why we picked it: trueedc.com")
                items.append({"id": fn, "title": f"{pr['name']}: {kicker}", "desc": pr["pitch"] + " Links may earn us a commission. #ad",
                              "link": f"{base}/blog/{po['slug']}/#{pid}", "image": f"{base}/pins/{fn}"})
    return items

# Second pin set (Nov 20 2026, Day 1 growth plan): light design, one per item in data/pins_extra.json.
LBG, LINK = (241, 239, 233), (20, 20, 19)

def make_pin_light(path, kicker, headline, sub, cta, photo=None):
    img = Image.new("RGB", (W, H), LBG)
    d = ImageDraw.Draw(img)
    m = 80
    d.rectangle([0, H - 18, W, H], fill=ACCENT)
    d.text((m, 90), "TRUE", font=font("Black", 52), fill=LINK)
    d.text((m + d.textlength("TRUE", font=font("Black", 52)), 90), "EDC", font=font("Black", 52), fill=ACCENT)
    y = 200
    if photo:
        ph = Image.open(photo).convert("RGB")
        box_w, box_h = W - 2 * m, 560
        ph.thumbnail((box_w, box_h))
        bg = Image.new("RGB", (box_w, box_h), (255, 255, 255))
        bg.paste(ph, ((box_w - ph.width) // 2, (box_h - ph.height) // 2))
        img.paste(bg, (m, y)); y += box_h + 50
    else:
        y = 330
    kf = font("Bold", 38)
    for line in wrap(d, kicker.upper(), kf, W - 2 * m):
        d.text((m, y), line, font=kf, fill=ACCENT); y += 50
    y += 20
    hf, hlines, hs = fit(d, headline, "Black", 104 if photo else 120, W - 2 * m, 4 if photo else 6)
    for line in hlines:
        d.text((m, y), line, font=hf, fill=LINK); y += int(hs * 1.12)
    y += 30
    sf = font("Medium", 44)
    room = (H - 270 - y) // 60
    for line in wrap(d, sub, sf, W - 2 * m)[:max(room, 0)]:
        d.text((m, y), line, font=sf, fill=(90, 87, 80)); y += 60
    d.rounded_rectangle([m, H - 240, W - m, H - 130], radius=20, fill=LINK)
    cf = font("Bold", 46)
    tw = d.textlength(cta, font=cf)
    d.text(((W - tw) / 2, H - 213), cta, font=cf, fill=LBG)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)

def make_extra(site, root, out_dir):
    import json
    base = site["base_url"].rstrip("/")
    f = root / "data" / "pins_extra.json"
    if not f.exists(): return []
    items = []
    for it in json.loads(f.read_text()):
        fn = f"pin2-{it['n']:02d}.png"
        photo = root / it["photo"] if it.get("photo") else None
        make_pin_light(out_dir / fn, it["kicker"], it["title"], it["desc"], "See it at trueedc.com", photo)
        desc = it["desc"] + (" " + it["credit"] if it.get("credit") else "") + " Links may earn us a commission. #ad"
        items.append({"id": fn, "title": it["title"], "desc": desc, "link": base + it["path"], "image": f"{base}/pins/{fn}"})
    return items
