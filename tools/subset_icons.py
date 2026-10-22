"""Cut the Phosphor icon font down to the icons the site actually uses.

The full font has some 1,500 icons; the site draws about forty. This scans
the page shells, scripts, data and stylesheets for ph-* class names, keeps
only those glyphs, and writes site/assets/icons/ph-regular.css with the
smaller font embedded. The full stylesheet stays in tools/vendor so a newly
used icon can be added by running this again.

    python tools/subset_icons.py

Needs fontTools and brotli (pip install fonttools brotli).
"""
import base64
import glob
import io
import os
import re
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
FULL = os.path.join(ROOT, 'tools', 'vendor', 'ph-regular.full.css')
OUT = os.path.join(SITE, 'assets', 'icons', 'ph-regular.css')

NAME = re.compile(r'\bph-[a-z0-9]+(?:-[a-z0-9]+)*')
RULE = re.compile(r'\.ph\.(ph-[a-z0-9-]+):before \{\s*content: "\\([0-9a-f]+)";\s*\}')
FONT = re.compile(r'url\("data:font/woff2;charset=utf-8;base64,([A-Za-z0-9+/=]+)"\) format\("woff2"\)')


def used_names():
    files = glob.glob(os.path.join(SITE, '*.html'))
    for sub in ('js', 'data', 'css'):
        files += glob.glob(os.path.join(SITE, 'assets', sub, '*.*'))
    names = set()
    for f in files:
        with io.open(f, encoding='utf-8') as fh:
            names.update(NAME.findall(fh.read()))
    names.discard('ph-regular')   # the stylesheet's own file name
    return names


def main():
    with io.open(FULL, encoding='utf-8') as fh:
        css = fh.read()
    codes = {m.group(1): m.group(2) for m in RULE.finditer(css)}
    names = used_names()
    unknown = sorted(n for n in names if n not in codes)
    if unknown:
        sys.exit('Not Phosphor icons: ' + ', '.join(unknown))

    font = TTFont(io.BytesIO(base64.b64decode(FONT.search(css).group(1))))
    options = subset.Options()
    options.flavor = 'woff2'
    options.layout_features = []          # the CSS uses code points, not ligatures
    options.name_IDs = ['*']
    sub = subset.Subsetter(options)
    sub.populate(unicodes=[int(codes[n], 16) for n in names])
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = 'woff2'
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode('ascii')

    face_end = css.index('}', css.index('@font-face')) + 1
    face = FONT.sub('url("data:font/woff2;charset=utf-8;base64,' + data + '") format("woff2")',
                    css[:face_end])
    base = css[css.index('.ph {'):css.index('}', css.index('.ph {')) + 1]
    rules = ''.join('.ph.%s:before {\n  content: "\\%s";\n}\n' % (n, codes[n]) for n in sorted(names))
    out = ('/* Phosphor Icons (MIT), regular weight, cut to the %d icons this site uses\n'
           '   by tools/subset_icons.py. Run it again after using a new icon. */\n'
           % len(names)) + face + '\n\n' + base + '\n\n' + rules
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(out)
    print('%d icons, %d bytes (was %d)' % (len(names), len(out.encode('utf-8')), len(css.encode('utf-8'))))


if __name__ == '__main__':
    main()
