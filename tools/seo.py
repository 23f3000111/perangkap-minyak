"""Write the search and link-preview tags into every page, and the sitemap.

The pages are rendered in the browser, but crawlers and link previews
(WhatsApp, Facebook, LinkedIn) read the HTML as it is served, so the
canonical address, the share card and the company details have to be in
the shells themselves. Everything between <!-- seo --> and <!-- /seo --> is
rewritten on each run; site/sitemap.xml and site/robots.txt are rewritten
whole.

    python tools/seo.py                                     # the github.io address
    python tools/seo.py --base https://www.example.com.my/  # after a move to a domain

Reads the catalogue through Node, so needs node on PATH.
"""
import argparse
import datetime
import glob
import html
import io
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
BASE = 'https://23f3000111.github.io/perangkap-minyak/'

# One shell renders every item of its kind, so it has no single address of
# its own; the page sets the canonical once it knows the item.
DYNAMIC = {'product.html', 'service.html', 'article.html'}
SKIP = {'404.html'}

DUMP = r"""
global.window = {};
['site.js', 'catalog.js'].forEach(function (f) { require(process.argv[1] + '/assets/data/' + f); });
var S = window.PM_SITE, C = window.PM_CATALOG;
process.stdout.write(JSON.stringify({
  brand: S.brand, contact: S.contact,
  products: C.products.map(function (p) { return p.slug; }),
  services: C.services.map(function (s) { return s.slug; }),
  articles: S.news.map(function (n) { return n.slug; })
}));
"""


def data():
    out = subprocess.run(['node', '-e', DUMP, SITE], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def organisation(d, base):
    c = d['contact']
    street, town, _ = c['hq']['lines']
    postcode, locality = town.split(',')[1].strip().split(' ', 1)
    return {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        'name': d['brand']['legal'],
        'alternateName': [d['brand']['name'], 'KAH Group'],
        'url': base,
        'logo': base + 'assets/img/brand/icon-512.png',
        'image': base + 'assets/img/brand/og-image.jpg',
        'foundingDate': str(d['brand']['since']),
        'email': c['email'],
        'telephone': c['officePhone'],
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': street + ', ' + town.split(',')[0].strip(),
            'postalCode': postcode,
            'addressLocality': locality,
            'addressRegion': 'Selangor',
            'addressCountry': 'MY'
        },
        'contactPoint': [{
            '@type': 'ContactPoint',
            'telephone': '+' + c['whatsapp'],
            'contactType': 'sales',
            'areaServed': 'MY',
            'availableLanguage': ['en', 'ms']
        }]
    }


def block(page, title, desc, base, org):
    attr = lambda s: html.escape(s, quote=True)
    url = base + ('' if page == 'index.html' else page)
    lines = ['<!-- seo -->']
    if page not in DYNAMIC:
        lines.append('<link rel="canonical" href="%s">' % url)
    lines += [
        '<link rel="apple-touch-icon" href="assets/img/brand/apple-touch-icon.png">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="Perangkap Minyak">',
        '<meta property="og:title" content="%s">' % attr(title),
        '<meta property="og:description" content="%s">' % attr(desc),
    ]
    if page not in DYNAMIC:
        lines.append('<meta property="og:url" content="%s">' % url)
    lines += [
        '<meta property="og:image" content="%sassets/img/brand/og-image.jpg">' % base,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Perangkap Minyak: grease traps, made in Malaysia">',
        '<meta property="og:locale" content="en_MY">',
        '<meta property="og:locale:alternate" content="ms_MY">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if org:
        lines.append('<script type="application/ld+json">%s</script>'
                     % json.dumps(org, ensure_ascii=False, separators=(',', ':')))
    lines.append('<!-- /seo -->')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=BASE, help='the address the site is published at, ending in /')
    base = ap.parse_args().base.rstrip('/') + '/'
    d = data()

    home = io.open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
    home_title = html.unescape(re.search(r'<title>(.*?)</title>', home).group(1))
    home_desc = html.unescape(re.search(r'<meta name="description" content="(.*?)">', home).group(1))

    pages = sorted(os.path.basename(f) for f in glob.glob(os.path.join(SITE, '*.html')))
    for page in pages:
        if page in SKIP:
            continue
        path = os.path.join(SITE, page)
        s = io.open(path, encoding='utf-8').read()
        s = re.sub(r'\n<!-- seo -->.*?<!-- /seo -->', '', s, flags=re.S)
        title = html.unescape(re.search(r'<title>(.*?)</title>', s).group(1))
        desc_m = re.search(r'<meta name="description" content="(.*?)">', s)
        desc = html.unescape(desc_m.group(1))
        if page in DYNAMIC:
            # Link previews do not run the page, so a shared product link
            # shows the company rather than "Product".
            title, desc = home_title, home_desc
        org = organisation(d, base) if page == 'index.html' else None
        s = s[:desc_m.end()] + '\n' + block(page, title, desc, base, org) + s[desc_m.end():]
        io.open(path, 'w', encoding='utf-8', newline='\n').write(s)

    today = datetime.date.today().isoformat()
    urls = [base + ('' if p == 'index.html' else p) for p in pages if p not in SKIP | DYNAMIC]
    urls += [base + 'product.html?p=' + x for x in d['products']]
    urls += [base + 'service.html?s=' + x for x in d['services']]
    urls += [base + 'article.html?a=' + x for x in d['articles']]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += ['  <url><loc>%s</loc><lastmod>%s</lastmod></url>' % (html.escape(u), today) for u in urls]
    xml.append('</urlset>')
    io.open(os.path.join(SITE, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n').write('\n'.join(xml) + '\n')
    io.open(os.path.join(SITE, 'robots.txt'), 'w', encoding='utf-8', newline='\n').write(
        'User-agent: *\nAllow: /\n\nSitemap: %ssitemap.xml\n' % base)
    print('%d pages tagged, %d addresses in the sitemap, base %s' % (len(pages) - len(SKIP), len(urls), base))


if __name__ == '__main__':
    main()
