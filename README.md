# Perangkap Minyak

The website of Kualiti Alam Hijau (M) Sdn Bhd: SIRIM certified grease traps, oil interceptors, auto dosing units, GoodBac bio-enzyme and the GreaseGo cleaning services, in English and Bahasa Melayu.

**Live:** https://23f3000111.github.io/perangkap-minyak/

## Layout

| Folder | What it holds | Published |
| --- | --- | --- |
| `site/` | The website: 27 pages, `404.html`, `sitemap.xml`, `robots.txt` and `assets/` | Yes |
| `tests/` | The browser check harness and the asset check | No |
| `tools/` | Preview server, store sync, SEO writer, icon subsetter, share-card sources | No |

The site is static HTML with no build step. Each page is a small shell; `site/assets/js/site.js` renders it from the data files:

- `site/assets/data/site.js`: company details, navigation, news, videos, interface wording
- `site/assets/data/catalog.js`: the 17-model specification table, every product and service, in the store's order
- `site/assets/data/library.js`: common issues, scheduled waste, cleaning range, field installations, catalogue and drawing PDFs

All wording is written as `{ en: '…', bm: '…' }` pairs.

## Working on it

```sh
python tools/serve.py                 # http://127.0.0.1:8080/perangkap-minyak/, as GitHub Pages serves it
```

Then open http://127.0.0.1:8080/tests/checks.html to run the 118 checks, and before a push:

```sh
node tests/check-assets.js            # every image, video, poster and PDF the pages name exists
node tests/check-assets.js --orphans  # also lists media nothing uses
```

## Publishing

Push to `main`. The `Publish site` workflow checks the assets and publishes `site/` to GitHub Pages; the live site updates a minute or two later.

## Housekeeping

- **Products from the store.** `python tools/sync_autodosing.py` pulls every product and service picture and video from autodosing.my and writes `tools/autodosing-media.json`; `catalog.js` mirrors it in its `MEDIA` table. Needs Pillow and ffmpeg.
- **A new domain.** `python tools/seo.py --base https://www.example.com.my/` rewrites the canonical addresses, link-preview tags, `sitemap.xml` and `robots.txt`. Run it without `--base` after adding a page.
- **A new icon.** The icon font is cut down to the icons in use. After using another Phosphor icon, run `python tools/subset_icons.py` (needs `pip install fonttools brotli`).
- **Share image.** `site/assets/img/brand/og-image.jpg` is a screenshot of `tools/og-card.html` at 1200 × 630.

## Enquiries

There is no server. The enquiry form and the chat assistant write the visitor's details into a WhatsApp message to the sales desk (017-878 5593); nothing is stored or sent until the visitor presses send in WhatsApp.
