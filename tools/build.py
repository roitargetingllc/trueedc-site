#!/usr/bin/env python3
"""Build the True EDC static site into docs/ (served by GitHub Pages).

Inputs:  site.json, data/products.json, data/guides.json
Outputs: docs/ (HTML pages, feed.xml for Pinterest auto-publish, sitemap, pins/*.png)

Run:  python3 tools/build.py
Rules baked in:
  - No exact Amazon prices on the page (Amazon only allows prices from its API, refreshed daily).
    Prices in products.json only place items in budget tiers.
  - Every page carries the FTC disclosure and Amazon's required statement; every Amazon button
    is labeled as a paid link and carries rel="sponsored nofollow noopener".
  - No product photos until they can come through Amazon's API or a brand's written permission.
    Product cards use drawn category icons, which are clearly icons, never stand-ins for photos.
  - Internal links are relative, so the same build works on trueedc.com and in a preview.
"""
import json, html, datetime, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
PREVIEW = "--preview" in sys.argv  # python3 tools/build.py --preview DIR : links end in index.html, no pins/feed
if PREVIEW:
    OUT = Path(sys.argv[sys.argv.index("--preview") + 1]).resolve()

site = json.loads((ROOT / "site.json").read_text())
products = {p["id"]: p for p in json.loads((ROOT / "data/products.json").read_text())}
guides = json.loads((ROOT / "data/guides.json").read_text())

AMAZON_LINE = "As an Amazon Associate, True EDC earns from qualifying purchases."
FTC_LINE = ("Some links on this page are affiliate links. If you buy through them, True EDC may earn a commission "
            "at no extra cost to you. It never changes what we pick.")

TIERS = [("under-25", "Under $25", "Stocking stuffers and keychain upgrades."),
         ("under-50", "Under $50", "The sweet spot: real tools, real brands."),
         ("splurge", "Worth the splurge", "Buy once, carry for a decade.")]

CATS = [  # slug, label, product categories, blurb
    ("knives", "Knives", ["Knife"], "Folders that open clean and carry light."),
    ("flashlights", "Flashlights", ["Flashlight"], "Keychain lights that beat a phone torch."),
    ("multitools", "Multitools", ["Multitool"], "Pliers, drivers and blades in one."),
    ("pens-notebooks", "Pens & notebooks", ["Pen", "Notebook"], "Write it down. Anywhere, any weather."),
    ("watches", "Watches", ["Watch"], "Tough, simple, always on the wrist."),
    ("keychain", "Keychain gear", ["Keychain"], "Clips and carabiners that sort your keys."),
]
CAT_ICON = {"Knife": "knife", "Flashlight": "light", "Multitool": "tool", "Pen": "pen", "Notebook": "notebook",
            "Watch": "watch", "Keychain": "clip"}

def esc(s): return html.escape(str(s), quote=True)

def nice_date(iso):
    return datetime.date.fromisoformat(iso).strftime("%b %-d, %Y")

def amazon_url(asin):
    url = f"https://www.amazon.com/dp/{asin}"
    if site.get("amazon_tag"):
        url += f"?tag={site['amazon_tag']}"
    return url

def tier_slug(price):
    if price <= 25: return "under-25"
    if price <= 50: return "under-50"
    return "splurge"

def tier_label(price):
    return {s: l for s, l, _ in TIERS}[tier_slug(price)]

# ---------- icons (drawn line art, 48x48) ----------
ICONS = {
 "knife": '<path d="M6 30 L30 10 C34 7 39 8 41 11 L20 32 Z"/><path d="M20 32 L28 40 C29 41 31 41 32 40 L35 37 C36 36 36 34 35 33 L27 25"/><circle cx="31" cy="36" r="1.4"/>',
 "light": '<rect x="8" y="19" width="22" height="10" rx="3"/><path d="M30 17 L38 14 L38 34 L30 31 Z"/><path d="M8 24 H4"/><path d="M42 18 L46 16 M42 24 H47 M42 30 L46 32"/>',
 "tool": '<path d="M10 38 L22 26"/><path d="M14 42 L26 30"/><path d="M22 26 L26 30 L34 22 C38 23 42 20 42 15 L37 18 L33 15 L35 10 C30 10 26 14 27 18 Z"/>',
 "pen": '<path d="M12 36 L34 14 L38 18 L16 40 L10 42 Z"/><path d="M30 18 L34 22"/><path d="M34 14 L37 11 C38 10 40 10 41 11 C42 12 42 14 41 15 L38 18"/>',
 "notebook": '<rect x="11" y="7" width="26" height="34" rx="2"/><path d="M17 7 V41"/><path d="M22 16 H32 M22 22 H32 M22 28 H29"/>',
 "watch": '<circle cx="24" cy="24" r="11"/><path d="M18 14 L19 5 H29 L30 14 M18 34 L19 43 H29 L30 34"/><path d="M24 18 V24 L28 27"/>',
 "clip": '<path d="M18 8 C10 8 10 20 18 20 H30 C38 20 38 32 30 32 H18 C10 32 10 44 18 44"/><path d="M30 8 H22 M26 44 H34"/>',
 "spark": '<path d="M24 6 L27 21 L42 24 L27 27 L24 42 L21 27 L6 24 L21 21 Z"/>',
}
def icon(name, cls="ico"):
    return (f'<svg class="{cls}" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')

LOGO = ('<svg class="mark" viewBox="0 0 32 32" aria-hidden="true"><path d="M16 2 L29 9 V23 L16 30 L3 23 V9 Z" '
        'fill="none" stroke="currentColor" stroke-width="2.4"/><path d="M10 12 H22 M16 12 V23" stroke="#ff6b1a" '
        'stroke-width="3" stroke-linecap="square"/></svg>')

TOPO = ('<svg class="topo" viewBox="0 0 800 500" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
        + "".join(f'<path d="M-50 {60+i*38} C 150 {20+i*38}, 250 {120+i*38}, 420 {70+i*38} S 700 {10+i*38}, 860 {80+i*38}"/>'
                  for i in range(12)) + "</svg>")

CSS = """
:root{--bg:#0e0e0d;--panel:#171715;--panel2:#1f1e1b;--line:#2c2b27;--ink:#efe9dc;--muted:#a49f93;--blaze:#ff6b1a;--blaze2:#ff8a47;--olive:#8b9160;--r:14px;color-scheme:dark}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
a{color:var(--blaze)}img,svg{display:block}
.wrap{max-width:1120px;margin:0 auto;padding:0 16px}
h1,h2,h3{font-family:Archivo,Inter,sans-serif;font-stretch:78%;letter-spacing:-.01em;line-height:1.02;margin:0}
h1{font-weight:900;text-transform:uppercase;font-size:clamp(44px,9vw,92px)}
h2{font-weight:850;text-transform:uppercase;font-size:clamp(30px,5vw,46px)}
h3{font-weight:800;font-size:22px;font-stretch:85%}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font:700 12px/1 Inter,sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--blaze)}
.eyebrow:before{content:"";width:22px;height:2px;background:var(--blaze)}
.muted{color:var(--muted)}
.top{position:sticky;top:0;z-index:20;background:rgba(14,14,13,.86);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:20px;height:64px}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);font:900 20px/1 Archivo,Inter,sans-serif;font-stretch:80%;letter-spacing:.06em}
.brand .mark{width:28px;height:28px;color:var(--ink)}.brand b{color:var(--blaze)}
.top nav{margin-left:auto;display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
.top nav a{color:var(--muted);text-decoration:none;font-weight:600;font-size:14px;padding:8px 10px;border-radius:8px;white-space:nowrap}
.top nav a:hover{color:var(--ink);background:var(--panel)}
.btn{display:inline-flex;align-items:center;gap:8px;background:var(--blaze);color:#140a03;text-decoration:none;font-weight:800;padding:13px 20px;border-radius:10px;border:0;transition:transform .15s,background .15s}
.btn:hover{background:var(--blaze2);transform:translateY(-1px)}
.btn.ghost{background:transparent;color:var(--ink);box-shadow:inset 0 0 0 1.5px var(--line)}
.btn.ghost:hover{box-shadow:inset 0 0 0 1.5px var(--muted);background:transparent}
.hero{position:relative;overflow:hidden;border-bottom:1px solid var(--line);background:radial-gradient(1200px 500px at 85% 10%,rgba(255,107,26,.16),transparent 60%),var(--bg)}
.topo{position:absolute;inset:0;width:100%;height:100%;stroke:#ffffff;stroke-opacity:.045;fill:none;stroke-width:1.2}
.hero .wrap{position:relative;display:grid;grid-template-columns:1.15fr .85fr;gap:40px;align-items:center;padding-top:72px;padding-bottom:72px}
.hero p.lead{font-size:clamp(17px,2.2vw,20px);color:var(--muted);max-width:520px;margin:20px 0 28px}
.hero .ctas{display:flex;flex-wrap:wrap;gap:12px}
.hero h1 em{font-style:normal;color:var(--blaze)}
.trust{display:flex;flex-wrap:wrap;gap:8px 22px;margin-top:30px;font-size:13px;color:var(--muted);font-weight:600}
.trust span{display:flex;align-items:center;gap:7px}.trust span:before{content:"";width:6px;height:6px;border-radius:2px;background:var(--olive)}
.layout{display:grid;grid-template-columns:1fr 1fr;gap:12px;transform:rotate(-3deg)}
.layout .slot{aspect-ratio:1;border-radius:var(--r);background:linear-gradient(145deg,var(--panel2),var(--panel));border:1px solid var(--line);display:flex;flex-direction:column;justify-content:space-between;padding:16px;color:var(--blaze);box-shadow:0 20px 40px rgba(0,0,0,.35)}
.layout .slot:nth-child(2),.layout .slot:nth-child(4){transform:translateY(22px)}
.layout .slot .ico{width:58%;height:auto;margin:auto}
.layout .slot small{color:var(--muted);font-weight:700;font-size:11px;letter-spacing:.14em;text-transform:uppercase}
section.band{padding:72px 0;border-bottom:1px solid var(--line)}
.sec-head{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:28px;flex-wrap:wrap}
.sec-head p{margin:10px 0 0;color:var(--muted);max-width:520px}
.sec-head a{font-weight:700;text-decoration:none;white-space:nowrap}
.tiers{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.tier{position:relative;display:block;text-decoration:none;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:26px 22px 22px;overflow:hidden;transition:border-color .15s,transform .15s}
.tier:hover{border-color:var(--blaze);transform:translateY(-2px)}
.tier .amt{font:900 clamp(44px,6vw,64px)/1 Archivo,sans-serif;font-stretch:75%;color:var(--blaze);letter-spacing:-.02em;text-transform:uppercase}
.tier .lbl{font-weight:800;text-transform:uppercase;letter-spacing:.12em;font-size:12px;color:var(--muted);margin-bottom:10px}
.tier p{margin:12px 0 0;color:var(--muted)}.tier .n{position:absolute;top:18px;right:18px;font-size:12px;font-weight:700;color:var(--muted)}
.cats{display:grid;grid-template-columns:repeat(6,1fr);gap:12px}
.cat{display:flex;flex-direction:column;gap:12px;text-decoration:none;color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:18px 16px;transition:border-color .15s,background .15s}
.cat:hover{border-color:var(--olive);background:var(--panel2)}
.cat .ico{width:40px;height:40px;color:var(--blaze)}
.cat strong{font:800 18px/1.1 Archivo,sans-serif;font-stretch:85%}.cat span{font-size:12px;color:var(--muted);font-weight:600}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.card{display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:var(--r);overflow:hidden;scroll-margin-top:84px}
.plate{position:relative;aspect-ratio:16/10;background:radial-gradient(circle at 50% 60%,rgba(255,107,26,.14),transparent 62%),linear-gradient(160deg,var(--panel2),#121210);display:flex;align-items:center;justify-content:center;color:var(--blaze);border-bottom:1px solid var(--line)}
.plate .ico{width:34%;height:auto}
.chip{position:absolute;top:12px;font:800 11px/1 Inter,sans-serif;letter-spacing:.12em;text-transform:uppercase;padding:7px 9px;border-radius:7px}
.chip.c{left:12px;background:rgba(14,14,13,.7);color:var(--ink);border:1px solid var(--line)}
.chip.t{right:12px;background:var(--blaze);color:#140a03}
.chip.top{left:12px;top:auto;bottom:12px;background:var(--olive);color:#0e0e0d}
.card .body{display:flex;flex-direction:column;gap:10px;padding:18px 18px 20px;flex:1}
.card .brand-line{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.card p{margin:0;color:#d4cec1}
.card ul{margin:2px 0 0;padding:0;list-style:none;display:grid;gap:6px;font-size:14px;color:var(--muted)}
.card li{display:flex;gap:8px}.card li:before{content:"";flex:none;width:6px;height:6px;margin-top:9px;border-radius:2px;background:var(--olive)}
.buy{margin-top:auto;padding-top:8px;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.paid{font-size:11px;color:var(--muted);font-weight:600;letter-spacing:.04em}
.guides{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.guide{position:relative;display:flex;flex-direction:column;justify-content:space-between;min-height:250px;text-decoration:none;color:var(--ink);border-radius:var(--r);padding:24px;border:1px solid var(--line);background:linear-gradient(180deg,rgba(255,107,26,.08),transparent 55%),var(--panel);overflow:hidden;transition:border-color .15s,transform .15s}
.guide:hover{border-color:var(--blaze);transform:translateY(-2px)}
.guide .num{font:900 72px/1 Archivo,sans-serif;font-stretch:70%;color:transparent;-webkit-text-stroke:1.5px #4a4740}
.guide h3{font-size:26px;margin:14px 0 8px}.guide p{margin:0;color:var(--muted);font-size:15px}
.guide .go{margin-top:18px;font-weight:800;color:var(--blaze)}
.how{display:grid;grid-template-columns:repeat(3,1fr);gap:28px}
.how div{border-top:2px solid var(--blaze);padding-top:16px}.how h3{font-size:20px;margin-bottom:6px}.how p{margin:0;color:var(--muted)}
.drop{display:grid;grid-template-columns:1.1fr .9fr;gap:28px;align-items:center;background:linear-gradient(120deg,#1c1206,#171715 60%);border:1px solid #3a2a1c;border-radius:20px;padding:36px}
.drop p{color:var(--muted);margin:12px 0 0}
.drop .soon{display:flex;flex-wrap:wrap;gap:10px}
.ghero{position:relative;overflow:hidden;border-bottom:1px solid var(--line);background:radial-gradient(900px 400px at 90% 0%,rgba(255,107,26,.14),transparent 60%),var(--bg)}
.ghero .wrap{position:relative;padding-top:56px;padding-bottom:48px}
.ghero h1{font-size:clamp(40px,7vw,76px);margin-top:14px;max-width:900px}
.ghero .dek{font-size:clamp(17px,2.2vw,20px);color:var(--muted);margin:18px 0 0;max-width:680px}
.meta-row{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
.pill{font-size:13px;font-weight:700;padding:7px 12px;border-radius:999px;background:var(--panel);border:1px solid var(--line);color:var(--muted)}
.jump{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.jump a{font-weight:700;font-size:14px;text-decoration:none;color:var(--ink);padding:9px 14px;border-radius:9px;background:var(--panel2);border:1px solid var(--line)}
.jump a:hover{border-color:var(--blaze)}
.disclosure{font-size:13px;color:var(--muted);border-left:3px solid var(--olive);padding:4px 0 4px 14px;margin:0}
.prose{max-width:720px;font-size:17px;color:#d4cec1}.prose p{margin:0 0 16px}
.tier-head{display:flex;align-items:baseline;gap:14px;margin:56px 0 20px;scroll-margin-top:84px}
.tier-head h2{font-size:clamp(28px,4.5vw,40px)}.tier-head span{color:var(--muted);font-weight:600}
.kitbar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:20px 22px;margin:28px 0}
.kitbar strong{font:900 30px/1 Archivo,sans-serif;font-stretch:78%;text-transform:uppercase}.kitbar strong em{font-style:normal;color:var(--blaze)}
.outro{margin:48px 0 0;padding:22px;border-radius:var(--r);background:var(--panel);border:1px solid var(--line);color:#d4cec1}
.page{padding:56px 0 24px;max-width:760px}.page h1{font-size:clamp(40px,7vw,64px);margin-bottom:22px}.page p{color:#d4cec1;font-size:17px}
footer{padding:48px 0 56px;color:var(--muted);font-size:14px;border-top:1px solid var(--line)}
footer .cols{display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap}
footer a{color:var(--muted);text-decoration:none}footer a:hover{color:var(--ink)}
footer .links{display:flex;gap:18px;flex-wrap:wrap}
footer .fine{margin-top:24px;padding-top:20px;border-top:1px solid var(--line);font-size:13px}
@media (max-width:960px){.cats{grid-template-columns:repeat(3,1fr)}.grid,.guides{grid-template-columns:repeat(2,1fr)}}
@media (max-width:760px){.hero .wrap{grid-template-columns:1fr;padding-top:44px;padding-bottom:56px}.layout{max-width:340px;margin:8px auto 0}
 .tiers,.how,.drop{grid-template-columns:1fr}.grid,.guides{grid-template-columns:1fr}.cats{grid-template-columns:repeat(2,1fr)}
 section.band{padding:52px 0}.drop{padding:24px}.top .wrap{gap:10px}.top nav a{padding:8px 6px;font-size:13px}}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,700..900&family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">')

def rel(cur, target):
    """Relative link from page path `cur` (like /a/b/) to site path `target` (like /x/ or /#id)."""
    depth = len([p for p in cur.strip("/").split("/") if p])
    prefix = "../" * depth or "./"
    t = target.lstrip("/")
    if PREVIEW:
        base, _, frag = t.partition("#")
        if base == "" or base.endswith("/"): base += "index.html"
        t = base + ("#" + frag if frag else "")
    return prefix + t

def page(title, description, body, path):
    canonical = site["base_url"].rstrip("/") + path
    L = lambda t: esc(rel(path, t))
    nav = (f'<a href="{L("/best-edc-gifts-2026/")}">Gift guide</a><a href="{L("/#budget")}">Budget</a>'
           f'<a href="{L("/#gear")}">Gear</a><a href="{L("/about/")}">About</a>')
    brand = f'<a class="brand" href="{L("/")}">{LOGO}<span>TRUE<b>EDC</b></span></a>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<meta name="theme-color" content="#0e0e0d">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}"><meta property="og:type" content="website"><meta property="og:site_name" content="True EDC">
<link rel="alternate" type="application/rss+xml" title="True EDC" href="{L('/feed.xml')}">
{FONTS}
<style>{CSS}</style>
</head><body>
<header class="top"><div class="wrap">{brand}<nav>{nav}</nav></div></header>
<main>
{body}
</main>
<footer><div class="wrap">
<div class="cols">{brand}
<div class="links"><a href="{L('/best-edc-gifts-2026/')}">Gift guide</a><a href="{L('/about/')}">About</a><a href="{L('/disclosure/')}">Affiliate disclosure</a><a href="{L('/privacy/')}">Privacy</a><a href="{esc(site['pinterest'])}" rel="noopener">Pinterest</a><a href="{esc(site['instagram'])}" rel="noopener">Instagram</a></div>
</div>
<p class="fine">{esc(AMAZON_LINE)} Links marked "paid link" may earn us a commission. © {site['year']} True EDC</p>
</div></footer>
</body></html>"""

def product_card(p, top=False, show_tier=True):
    facts = "".join(f"<li>{esc(f)}</li>" for f in p["facts"])
    chips = f'<span class="chip c">{esc(p["category"])}</span>'
    if show_tier: chips += f'<span class="chip t">{esc(tier_label(p["price"]))}</span>'
    if top: chips += '<span class="chip top">Top pick</span>'
    return f"""<article class="card" id="{esc(p['id'])}">
<div class="plate">{icon(CAT_ICON.get(p['category'], 'spark'))}{chips}</div>
<div class="body">
<div class="brand-line">{esc(p['brand'])}</div>
<h3>{esc(p['name'])}</h3>
<p>{esc(p['pitch'])}</p>
<ul>{facts}</ul>
<div class="buy"><a class="btn" href="{esc(amazon_url(p['asin']))}" rel="sponsored nofollow noopener" target="_blank">Check price on Amazon</a><span class="paid">Paid link</span></div>
</div></article>"""

def latest_checked(ids):
    return max(products[i]["checked"] for i in ids if i in products)

def ghero(eyebrow, title, dek, pills, extra=""):
    pills_html = "".join(f'<span class="pill">{esc(p)}</span>' for p in pills)
    return (f'<section class="ghero">{TOPO}<div class="wrap"><span class="eyebrow">{esc(eyebrow)}</span>'
            f'<h1>{esc(title)}</h1><p class="dek">{esc(dek)}</p><div class="meta-row">{pills_html}</div>{extra}</div></section>')

def build_guide(g):
    ids = [i for i in g["products"] if i in products]
    missing = [i for i in g["products"] if i not in products]
    if missing: print(f"WARN {g['slug']}: unknown products {missing}", file=sys.stderr)
    path = f"/{g['slug']}/"
    checked = nice_date(latest_checked(ids))
    top = g.get("top_pick")
    eyebrow = {"holiday": "Holiday gift guide", "evergreen": "Buying guide"}.get(g.get("season"), "Guide")
    intro = "".join(f"<p>{esc(t.replace('{checked}', checked))}</p>" for t in g["intro"])
    warnings, body, jump = [], [], ""
    if g["mode"] == "tiers":
        present = [(s, l) for s, l, _ in TIERS if any(tier_slug(products[i]["price"]) == s for i in ids)]
        jump = '<div class="jump">' + "".join(f'<a href="#{s}">{esc(l)}</a>' for s, l in present) + "</div>"
        for s, l, _ in TIERS:
            items = [products[i] for i in ids if tier_slug(products[i]["price"]) == s]
            if not items: continue
            body.append(f'<div class="tier-head" id="{s}"><h2>{esc(l)}</h2><span>{len(items)} pick{"s" if len(items) > 1 else ""}</span></div>')
            body.append('<div class="grid">' + "".join(product_card(p, top=p["id"] == top, show_tier=False) for p in items) + "</div>")
    elif g["mode"] == "under":
        over = [products[i]["name"] for i in ids if products[i]["price"] > g["max_price"]]
        if over: warnings.append(f"{g['slug']}: over ${g['max_price']}: {over}")
        ok = [products[i] for i in ids if products[i]["price"] <= g["max_price"]]
        body.append(f'<div class="tier-head"><h2>The picks</h2><span>{len(ok)} under ${g["max_price"]}</span></div>')
        body.append('<div class="grid">' + "".join(product_card(p, top=p["id"] == top, show_tier=False) for p in ok) + "</div>")
    elif g["mode"] == "kit":
        items = [products[i] for i in ids]
        total = sum(p["price"] for p in items)
        if total > g["budget"]: warnings.append(f"{g['slug']}: kit total ${total:.2f} is over ${g['budget']}")
        body.append(f'<div class="kitbar"><strong>{len(items)} pieces. <em>Under ${g["budget"]}.</em></strong>'
                    f'<span class="muted">Priced together on {checked}. Prices move, so check each one.</span></div>')
        body.append('<div class="grid">' + "".join(product_card(p, top=p["id"] == top) for p in items) + "</div>")
    body.append(f'<div class="outro">{esc(g["outro"])}</div>')
    body.append(f'<p class="muted" style="margin:18px 0 0;font-size:14px">Prices checked {checked}. Prices and stock change, so the button always shows today\'s price on Amazon.</p>')
    for w in warnings: print("WARN", w, file=sys.stderr)
    dek = g["description"].replace("{checked}", checked)
    html_ = (ghero(eyebrow, g["title"], dek, [f"Checked {checked}", f"{len(ids)} real products", "Affiliate links labeled"], jump)
             + f'<div class="wrap" style="padding-top:36px;padding-bottom:72px"><p class="disclosure">{esc(FTC_LINE)} {esc(AMAZON_LINE)}</p>'
             + f'<div class="prose" style="margin-top:28px">{intro}</div>{"".join(body)}</div>')
    return path, page(f"{g['title']} | True EDC", dek, html_, path), warnings

def listing_page(path, eyebrow, title, dek, items):
    cards = "".join(product_card(p) for p in items)
    checked = nice_date(latest_checked([p["id"] for p in items]))
    body = (ghero(eyebrow, title, dek, [f"{len(items)} pick{'s' if len(items) > 1 else ''}", f"Checked {checked}"])
            + f'<div class="wrap" style="padding-top:36px;padding-bottom:72px"><p class="disclosure">{esc(FTC_LINE)} {esc(AMAZON_LINE)}</p>'
            + f'<div class="grid" style="margin-top:28px">{cards}</div></div>')
    return page(f"{title} | True EDC", dek, body, path)

def home():
    path = "/"
    L = lambda t: esc(rel(path, t))
    allp = list(products.values())
    tiers = ""
    for s, l, b in TIERS:
        n = sum(1 for p in allp if tier_slug(p["price"]) == s)
        big = "Splurge" if s == "splurge" else l
        tiers += (f'<a class="tier" href="{L("/budget/" + s + "/")}"><span class="n">{n} picks</span>'
                  f'<div class="lbl">Budget</div><div class="amt">{esc(big)}</div><p>{esc(b)}</p></a>')
    cats = ""
    for slug, label, pcats, _ in CATS:
        n = sum(1 for p in allp if p["category"] in pcats)
        if not n: continue
        cats += (f'<a class="cat" href="{L("/gear/" + slug + "/")}">{icon(CAT_ICON[pcats[0]])}'
                 f'<div><strong>{esc(label)}</strong><br><span>{n} pick{"s" if n > 1 else ""}</span></div></a>')
    featured_ids = ["victorinox-classic-sd", "olight-imini-2", "gerber-dime", "civivi-elementum", "fisher-space-pen-bullet", "leatherman-wave-plus"]
    featured = "".join(product_card(products[i], top=(i == "victorinox-classic-sd")) for i in featured_ids if i in products)
    gl = "".join(
        f'<a class="guide" href="{L("/" + g["slug"] + "/")}"><div><div class="num">0{n}</div><h3>{esc(g["title"])}</h3>'
        f'<p>{esc(g["description"].replace("{checked}", nice_date(latest_checked(g["products"]))))}</p></div><div class="go">Read the guide →</div></a>'
        for n, g in enumerate(guides, 1))
    if site.get("newsletter_url"):
        drop_cta = f'<a class="btn" href="{esc(site["newsletter_url"])}">Get the Drop, free</a>'
    else:
        drop_cta = (f'<div class="soon"><a class="btn" href="{esc(site["pinterest"])}" rel="noopener">Follow on Pinterest</a>'
                    f'<a class="btn ghost" href="{esc(site["instagram"])}" rel="noopener">Instagram</a></div>'
                    '<p style="margin-top:12px;font-size:13px">The weekly email launches soon. Follow along until then.</p>')
    layout = "".join(f'<div class="slot">{icon(i)}<small>{esc(t)}</small></div>'
                     for i, t in [("light", "Light"), ("tool", "Tool"), ("pen", "Pen"), ("watch", "Watch")])
    body = f"""<section class="hero">{TOPO}<div class="wrap">
<div>
<span class="eyebrow">2026 holiday gift guide is live</span>
<h1 style="margin-top:18px">Gear worth <em>carrying.</em></h1>
<p class="lead">Knives, lights, multitools and pocket gear, picked by budget and re-checked every week. Real products only. No fluff.</p>
<div class="ctas"><a class="btn" href="{L('/best-edc-gifts-2026/')}">Shop the gift guide</a><a class="btn ghost" href="{L('/first-edc-kit-under-100/')}">Build a kit under $100</a></div>
<div class="trust"><span>Real products only</span><span>Prices re-checked weekly</span><span>Every affiliate link labeled</span></div>
</div>
<div class="layout" aria-hidden="true">{layout}</div>
</div></section>
<section class="band" id="budget"><div class="wrap">
<div class="sec-head"><div><span class="eyebrow">Shop by budget</span><h2 style="margin-top:12px">What do you want to spend?</h2></div></div>
<div class="tiers">{tiers}</div>
</div></section>
<section class="band" id="gear"><div class="wrap">
<div class="sec-head"><div><span class="eyebrow">Shop by gear</span><h2 style="margin-top:12px">Pick your category</h2></div></div>
<div class="cats">{cats}</div>
</div></section>
<section class="band"><div class="wrap">
<div class="sec-head"><div><span class="eyebrow">Top picks</span><h2 style="margin-top:12px">What we would carry</h2>
<p>Six picks that earn their pocket space, from a keychain light to a tool that gets handed down.</p></div>
<a href="{L('/best-edc-gifts-2026/')}">See all 10 →</a></div>
<div class="grid">{featured}</div>
</div></section>
<section class="band"><div class="wrap">
<div class="sec-head"><div><span class="eyebrow">Guides</span><h2 style="margin-top:12px">Start here</h2></div></div>
<div class="guides">{gl}</div>
</div></section>
<section class="band"><div class="wrap"><div class="how">
<div><h3>Real products only</h3><p>Every pick is a real listing we checked ourselves. No made-up products, no AI pictures pretending to be gear.</p></div>
<div><h3>Re-checked every week</h3><p>Every price and listing gets re-checked weekly, and anything out of stock gets swapped out.</p></div>
<div><h3>Honest about money</h3><p>We earn a small commission on some links. Every one is labeled, and it never decides what makes the list.</p></div>
</div></div></section>
<section style="padding:72px 0"><div class="wrap">
<div class="drop"><div><span class="eyebrow">{esc(site['newsletter_name'])}</span><h2 style="margin-top:12px">Three picks. One real deal. Weekly.</h2>
<p>A short email with three useful pieces of gear and one genuine price drop. No spam, unsubscribe anytime.</p></div>
<div>{drop_cta}</div></div>
</div></section>"""
    return page("True EDC | Everyday carry gear and gift guides, picked by budget", site["tagline"], body, path)

def static_pages():
    about = """<span class="eyebrow">About</span><h1 style="margin-top:14px">Gear worth carrying.</h1>
<p>True EDC picks everyday-carry gear by budget: small tools, lights, pens, watches and the rest of what people actually keep on them.</p>
<p>Every pick is a real product with a real listing, and prices are re-checked every week. We do not use AI pictures of products, and we do not list anything we could not verify.</p>
<p>True EDC is supported by affiliate links. See the <a href="../disclosure/">affiliate disclosure</a>.</p>"""
    disclosure = f"""<span class="eyebrow">Disclosure</span><h1 style="margin-top:14px">How we make money</h1>
<p>{esc(FTC_LINE)}</p>
<p>{esc(AMAZON_LINE)}</p>
<p>We may also earn commissions from other retailers and brand programs. Links that can earn a commission are marked "paid link" and tagged as sponsored, and posts with affiliate links on social media are labeled #ad.</p>"""
    privacy = """<span class="eyebrow">Privacy</span><h1 style="margin-top:14px">Privacy</h1>
<p>This site has no accounts and sets no cookies of its own. Fonts load from Google Fonts. Retailers you click through to, such as Amazon, may set their own cookies to track a referral; their privacy policies apply on their sites.</p>
<p>If you sign up for our email, your address is stored by our newsletter provider only to send that email, and every email has an unsubscribe link.</p>"""
    wrap = lambda b: f'<div class="wrap"><div class="page">{b}</div></div>'
    return {"/about/": ("About | True EDC", "What True EDC is and how picks are made.", wrap(about)),
            "/disclosure/": ("Affiliate disclosure | True EDC", "How True EDC earns money.", wrap(disclosure)),
            "/privacy/": ("Privacy | True EDC", "True EDC privacy policy.", wrap(privacy))}

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
    allp = list(products.values())
    for s, l, b in TIERS:
        items = sorted([p for p in allp if tier_slug(p["price"]) == s], key=lambda p: p["price"])
        if not items: continue
        path = f"/budget/{s}/"
        title = "EDC gear worth the splurge" if s == "splurge" else f"EDC gear {l.lower()}"
        write(path, listing_page(path, "Shop by budget", title, b, items)); urls.append(path)
    for slug, label, pcats, blurb in CATS:
        items = [p for p in allp if p["category"] in pcats]
        if not items: continue
        path = f"/gear/{slug}/"
        write(path, listing_page(path, "Shop by gear", label, blurb, items)); urls.append(path)
    write("/", home())
    for path, (t, d, b) in static_pages().items():
        write(path, page(t, d, b, path)); urls.append(path)
    base = site["base_url"].rstrip("/")
    write("/sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{base}{u}</loc></url>" for u in urls) + "</urlset>\n")
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    write("/CNAME", "trueedc.com\n")
    write("/.nojekyll", "")
    if PREVIEW:
        print(f"Preview: built {len(urls)} pages into {OUT}"); return
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
