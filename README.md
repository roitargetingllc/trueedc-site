# True EDC site

Static site for trueedc.com, built by `tools/build.py` into `docs/` and served free by GitHub Pages.

## Build

```
python3 tools/build.py
```

Needs Python 3 and Pillow. Exit code 2 means a guide broke its own rule (an item over a guide's price cap, or a kit over budget). Fix the data before publishing.

## Files

- `site.json`: name, tagline, `amazon_tag` (empty until Amazon Associates approves), `newsletter_url` (the signup box only shows once this is set).
- `data/products.json`: every product, with its ASIN, the price last seen, the date it was checked and only facts taken from the listing.
- `data/guides.json`: the guides. `mode` is `tiers` (sorted into Under $25, Under $50, Splurge), `under` (with `max_price`) or `kit` (with `budget`). `{checked}` becomes the latest checked date.
- `data/feed_dates.json`: first-seen date of every feed item. Keep it in the repo, so old pins are not re-sent as new.
- `docs/`: generated. Never edit by hand.

## Rules the build enforces, and why

- No exact Amazon prices on pages. Amazon only allows prices that come from its own API and refresh at least daily; stored prices are used only to sort items into budget tiers.
- No product photos. Amazon images may only be used through Amazon's own tools. Pins are text graphics.
- Every page has the FTC disclosure and Amazon's line, "As an Amazon Associate, True EDC earns from qualifying purchases." Affiliate links carry `rel="sponsored nofollow noopener"`.
- No Amazon customer reviews or star ratings, in part or in whole, until they come through Amazon's API. Never quote or paraphrase reviews from any store unless its terms allow it in writing.
- Only real products, real listings, and facts that appear on the listing.

## Weekly refresh (for the scheduled run)

1. Re-check each ASIN's price and availability with Keepa (`get_products`, 1 token per ASIN). Update `price` and `checked`.
2. Drop or replace any product that is out of stock, has no offers or no longer fits its guide's cap.
3. Draft at most one new guide or one new product, from real listings only. Add it to the data.
4. Run the build. If it exits 2, fix the data.
5. Commit and push. Pages redeploys on its own, and the new items reach Pinterest through `feed.xml`.

## Pinterest

Pinterest auto-publishes from `https://trueedc.com/feed.xml` once the site is claimed in a Pinterest business account and the feed is added under Settings, Bulk create Pins. Each new item becomes a Pin, linked to its guide.
