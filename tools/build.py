#!/usr/bin/env python3
"""Build the True EDC static site into docs/ (served by GitHub Pages).

Inputs:  site.json, data/products.json, data/guides.json
Outputs: docs/ (HTML pages, feed.xml for Pinterest auto-publish, sitemap, pins/*.png)

Run:  python3 tools/build.py
Rules baked in:
  - No exact Amazon prices on the page (Amazon only allows prices from its API, refreshed daily).
    Prices in products.json are only used to place items in budget tiers.
  - Every page carries the FTC disclosure and Amazon's required statement.
  - No product photos (no Amazon images without their tools); pins are text graphics.
"""
import json, html, datetime, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"

site = json.loads((ROOT / "site.json").read_text())
products = {p["id"]: p for p in json.loads((ROOT / "data/products.json").read_text())}
guides = json.loads((ROOT / "data/guides.json").read_text())

AMAZON_LINE = "As an Amazon Associate, True EDC earns from qualifying purchases."
FTC_LINE = ("Some links on this page are affiliate links. If you buy through them, True EDC may earn a commission "
            "at no extra cost to you. It never changes what we pick.")

def esc(s): return html.escape(str(s), quote=True)

def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return d.strftime("%b %-d, %Y")

def amazon_url(asin):
    url = f"https://www.amazon.com/dp/{asin}"
    if site.get("amazon_tag"):
        url += f"?tag={site['amazon_tag']}"
    return url

def tier(price):
    if price <= 25: return "Under $25"
    if price <= 50: return "Under $50"
    return "Splurge"

CSS = """
:root{--bg:#f6f4ef;--ink:#1d1d1b;--muted:#5e5b55;--line:#dedad1;--card:#fff;--accent:#c2410c;--accent-ink:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--ink:#f1efe9;--muted:#a9a59c;--line:#2e2d2a;--card:#1d1c1a;--accent:#f97316;--accent-ink:#141413}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif}
a{color:var(--accent)}
.wrap{max-width:760px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--line)}
header.top .wrap{display:flex;align-items:center;justify-content:space-between;height:60px}
.logo{font-weight:800;letter-spacing:.04em;text-decoration:none;color:var(--ink);font-size:18px}
.logo span{color:var(--accent)}
nav a{color:var(--muted);text-decoration:none;margin-left:16px;font-size:15px}
h1{font-size:clamp(28px,6vw,40px);line-height:1.15;margin:32px 0 12px}
h2{font-size:24px;margin:40px 0 12px;padding-top:8px;border-top:2px solid var(--ink)}
h3{font-size:20px;margin:0 0 4px}
.dek{color:var(--muted);font-size:18px}
.disclosure{font-size:14px;color:var(--muted);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}
.meta{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:6px}
.card ul{margin:10px 0;padding-left:20px;color:var(--muted);font-size:15px}
.btn{display:inline-block;background:var(--accent);color:var(--accent-ink);text-decoration:none;font-weight:700;padding:10px 16px;border-radius:8px;margin-top:6px}
.guides a.g{display:block;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:12px 0;text-decoration:none;color:var(--ink)}
.guides a.g strong{display:block;font-size:19px}.guides a.g span{color:var(--muted);font-size:15px}
.signup{background:var(--ink);color:var(--bg);border-radius:12px;padding:22px;margin:32px 0}
.signup a{background:var(--accent);color:var(--accent-ink)}
footer{border-top:1px solid var(--line);margin-top:48px;padding:24px 0 40px;color:var(--muted);font-size:14px}
footer a{color:var(--muted)}
.total{font-weight:700}
"""

def page(title, description, body, path, extra_head=""):
    canonical = site["base_url"].rstrip("/") + path
    nav = '<a href="/">Guides</a><a href="/about/">About</a>'
    signup = ""
    if site.get("newsletter_url"):
        signup = (f'<div class="signup"><strong>{esc(site["newsletter_name"])}</strong><br>'
                  f'Three useful picks and one real deal, once a week. Free.<br>'
                  f'<a class="btn" href="{esc(site["newsletter_url"])}">Get the Drop</a></div>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}"><meta property="og:type" content="article">
<link rel="alternate" type="application/rss+xml" title="True EDC" href="/feed.xml">
<style>{CSS}</style>{extra_head}
</head><body>
<header class="top"><div class="wrap"><a class="logo" href="/">TRUE<span>EDC</span></a><nav>{nav}</nav></div></header>
<main class="wrap">
{body}
{signup}
</main>
<footer><div class="wrap">
<p>{esc(AMAZON_LINE)} <a href="/disclosure/">Affiliate disclosure</a> · <a href="/privacy/">Privacy</a></p>
<p>© {site['year']} True EDC</p>
</div></footer>
</body></html>"""

def product_card(p, show_tier=True):
    facts = "".join(f"<li>{esc(f)}</li>" for f in p["facts"])
    meta = p["category"] + (f" · {tier(p['price'])}" if show_tier else "")
    return f"""<div class="card" id="{esc(p['id'])}">
<div class="meta">{esc(meta)}</div>
<h3>{esc(p['name'])}</h3>
<p>{esc(p['pitch'])}</p>
<ul>{facts}</ul>
<a class="btn" href="{esc(amazon_url(p['asin']))}" rel="sponsored nofollow noopener" target="_blank">Check today's price on Amazon</a>
</div>"""

def latest_checked(ids):
    return max(products[i]["checked"] for i in ids)

def build_guide(g):
    ids = [i for i in g["products"] if i in products]
    missing = [i for i in g["products"] if i not in products]
    if missing: print(f"WARN {g['slug']}: unknown products {missing}", file=sys.stderr)
    checked = nice_date(latest_checked(ids))
    intro = "".join(f"<p>{esc(t.replace('{checked}', checked))}</p>" for t in g["intro"])
    parts = [f"<h1>{esc(g['title'])}</h1>", f"<p class='dek'>{esc(g['description'].replace('{checked}', checked))}</p>",
             f"<div class='disclosure'>{esc(FTC_LINE)}</div>", intro]
    warnings = []
    if g["mode"] == "tiers":
        for t in ["Under $25", "Under $50", "Splurge"]:
            items = [products[i] for i in ids if tier(products[i]["price"]) == t]
            if not items: continue
            parts.append(f"<h2>{esc(t)}</h2>")
            parts += [product_card(p, show_tier=False) for p in items]
    elif g["mode"] == "under":
        items = [products[i] for i in ids]
        over = [p["name"] for p in items if p["price"] > g["max_price"]]
        if over: warnings.append(f"{g['slug']}: over ${g['max_price']}: {over}")
        parts += [product_card(products[i]) for i in ids if products[i]["price"] <= g["max_price"]]
    elif g["mode"] == "kit":
        items = [products[i] for i in ids]
        total = sum(p["price"] for p in items)
        if total > g["budget"]: warnings.append(f"{g['slug']}: kit total ${total:.2f} is over ${g['budget']}")
        parts += [product_card(p) for p in items]
        parts.append(f"<p class='total'>All five came to under ${g['budget']} together when we priced them on {checked}. "
                     f"Prices move, so check each one on Amazon.</p>")
    parts.append(f"<p>{esc(g['outro'])}</p>")
    parts.append(f"<p class='dek'>Prices checked {checked}. Prices and availability change, so the button always shows today's price.</p>")
    for w in warnings: print("WARN", w, file=sys.stderr)
    path = f"/{g['slug']}/"
    return path, page(f"{g['title']} | True EDC", g["description"].replace("{checked}", checked), "\n".join(parts), path), warnings

def static_pages():
    about = """<h1>About True EDC</h1>
<p>True EDC picks everyday-carry gear by budget: small tools, lights, pens, wallets and the rest of what people actually keep on them.</p>
<p>Every pick is a real product with a real listing, and prices are re-checked regularly. We do not use AI pictures of products, and we do not list anything we could not verify.</p>
<p>True EDC is supported by affiliate links. See the <a href="/disclosure/">affiliate disclosure</a>.</p>"""
    disclosure = f"""<h1>Affiliate disclosure</h1>
<p>{esc(FTC_LINE)}</p>
<p>{esc(AMAZON_LINE)}</p>
<p>We may also earn commissions from other retailers and brand programs. Links that can earn a commission are marked as sponsored, and posts with affiliate links on social media are labeled #ad.</p>"""
    privacy = """<h1>Privacy</h1>
<p>This site has no accounts and sets no cookies of its own. Retailers you click through to, such as Amazon, may set their own cookies to track a referral; their privacy policies apply on their sites.</p>
<p>If you sign up for our email, your address is stored by our newsletter provider only to send that email, and every email has an unsubscribe link.</p>"""
    return {"/about/": ("About | True EDC", "What True EDC is and how picks are made.", about),
            "/disclosure/": ("Affiliate disclosure | True EDC", "How True EDC earns money.", disclosure),
            "/privacy/": ("Privacy | True EDC", "True EDC privacy policy.", privacy)}

def write(path, content, binary=False):
    f = OUT / path.lstrip("/")
    if path.endswith("/"): f = f / "index.html"
    f.parent.mkdir(parents=True, exist_ok=True)
    (f.write_bytes if binary else f.write_text)(content)

def main():
    if OUT.exists():
        keep = OUT / "pins"
        for c in OUT.iterdir():
            if c != keep: shutil.rmtree(c) if c.is_dir() else c.unlink()
    OUT.mkdir(exist_ok=True)
    urls, all_warn = ["/"], []
    for g in guides:
        path, htmltext, w = build_guide(g)
        write(path, htmltext); urls.append(path); all_warn += w
    links = "".join(f'<a class="g" href="/{esc(g["slug"])}/"><strong>{esc(g["title"])}</strong><span>{esc(g["description"].replace("{checked}", nice_date(latest_checked(g["products"]))))}</span></a>' for g in guides)
    home = (f"<h1>Everyday carry, picked by budget.</h1><p class='dek'>{esc(site['tagline'])}</p>"
            f"<div class='guides'>{links}</div>")
    write("/", page("True EDC | Everyday carry gear and gift guides", site["tagline"], home, "/"))
    for path, (t, d, b) in static_pages().items():
        write(path, page(t, d, b, path)); urls.append(path)
    base = site["base_url"].rstrip("/")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{base}{u}</loc></url>" for u in urls) + "</urlset>\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    write("/CNAME", "trueedc.com\n")
    write("/.nojekyll", "")
    # Pins + RSS feed for Pinterest auto-publish
    sys.path.insert(0, str(ROOT / "tools"))
    import pins, feed
    pin_items = pins.make_all(site, products, guides, OUT / "pins")
    write("/feed.xml", feed.rss(site, pin_items))
    print(f"Built {len(urls)} pages and {len(pin_items)} pins into {OUT}")
    if all_warn:
        print("CHECK THESE:", *all_warn, sep="\n  ")
        sys.exit(2)

if __name__ == "__main__":
    main()
