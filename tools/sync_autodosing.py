"""Pull product and service media from autodosing.my into site/assets.

autodosing.my is the client's Shopify store and the source of truth for the
product range. This script maps each of its products to the slug used on
this site, downloads every product image in order, the hosted videos, and
records the YouTube ones, then writes tools/autodosing-media.json, which
assets/data/catalog.js mirrors.

    python tools/sync_autodosing.py            # images, videos, manifest
    python tools/sync_autodosing.py --no-video # skip the video downloads

Needs Pillow, and ffmpeg on PATH for the videos.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from io import BytesIO

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'site', 'assets')
CACHE = os.path.join(ROOT, 'tools', '.cache')
STORE = 'https://www.autodosing.my'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/130 Safari/537.36'}

# autodosing.my handle -> (kind, slug on this site)
MAP = {
    # undersink, in the store's order
    'undersink-grease-trap-10-gpm-23-liter': ('product', 'undersink-grease-trap-gts01'),
    'undersink-grease-trap-12gpm-40-liter': ('product', 'undersink-grease-trap-gts02'),
    'undersink-grease-trap-supplier': ('product', 'undersink-grease-trap-gts02a'),
    'undersink-grease-trap-15-gpm-57-liter': ('product', 'undersink-grease-trap-gta01'),
    'undersink-grease-trap-20-gpm-80-liter': ('product', 'undersink-grease-trap-gta02'),
    'undersink-grease-trap-20-gpm-56-liter': ('product', 'pantries-grease-trap-gts03p'),
    'automatic-grease-trap-malaysia': ('product', 'undersink-automatic-grease-trap-gta03auto'),
    'custom-made-undersink-grease-trap-malaysia': ('product', 'custom-made-undersink-grease-trap'),
    # centralized
    'centralized-grease-trap-25-gpm-149-liter': ('product', 'centralized-grease-trap-gta325'),
    'grease-trap-35-gpm-189-liter': ('product', 'centralized-grease-trap-gta335'),
    'grease-trap-50-gpm-262-liter': ('product', 'centralized-grease-trap-gta350'),
    'centralized-grease-trap-75-gpm-447-liter': ('product', 'centralized-grease-trap-gta375'),
    'centralized-grease-trap-100-gpm-866-liter': ('product', 'centralized-grease-trap-gta3100'),
    'centralized-grease-trap-150-gpm-1197-liter': ('product', 'centralized-grease-trap-gta3150'),
    'grease-trap-200-gpm-1712-liter': ('product', 'centralized-grease-trap-gta3200'),
    'centralized-grease-trap-gta3250-250-gpm-2188-liter': ('product', 'centralized-grease-trap-gta3250'),
    'centralized-grease-trap-300-gpm-2635-liter': ('product', 'centralized-grease-trap-gta3300'),
    'centralized-grease-trap-350-gpm-2928-liter': ('product', 'centralized-grease-trap-gta3350'),
    'grease-trap-400-gpm-3466-liter': ('product', 'centralized-grease-trap-gta3400'),
    'centralized-grease-trap-malaysia': ('product', 'centralized-grease-trap-gta3450'),
    'centralized-grease-trap-500-gpm-4839-liter': ('product', 'centralized-grease-trap-gta3500'),
    'grease-trap-supplier-malaysia': ('product', 'commercial-drainage-grease-trap-gta3800'),
    'custom-made-centralized-grease-trap': ('product', 'custom-made-centralized-grease-trap'),
    'onsite-grease-trap-free-inspection-service': ('product', 'free-onsite-grease-trap-inspection'),
    # oil interceptors
    'automatic-oil-interceptor': ('product', 'automatic-oil-interceptor'),
    'oil-interceptor-for-carwash-workshop': ('product', 'oil-interceptor-carwash-workshop-gta03c'),
    'oil-seperator-oil-interceptor': ('product', 'oil-interceptor-petrol-station-gta9001'),
    'oil-interceptor-700-gpm-1360-liter': ('product', 'oil-interceptor-petrol-station-gta9002'),
    # auto dosing
    'auto-dosing-unit-malaysia': ('product', 'auto-dosing-unit-adu9291p'),
    'grease-trap-auto-dosing-system-demo-malaysia': ('product', 'free-grease-management-demo'),
    # bio-enzyme
    'goodbac-grease-trap-bio-enzyme-500ml': ('product', 'goodbac-bio-enzyme-500ml'),
    'goodbac-grease-trap-bio-enzyme-1-liter': ('product', 'goodbac-bio-enzyme-1-liter'),
    'goodbac-grease-trap-bio-enzyme-5-liter': ('product', 'goodbac-bio-enzyme-5-liter'),
    'grease-trap-bio-enzyme-malaysia': ('product', 'goodbac-bio-enzyme-5-liter-x4'),
    # others
    'adu-lockable-cabinet': ('product', 'auto-dosing-lockable-cabinet'),
    'auto-dosing-unit-hanging-panel': ('product', 'auto-dosing-unit-hanging-panel'),
    'grease-trap-bio-brick-malaysia': ('product', 'goodbac-bio-brick'),
    'water-leaking-sensor-system-malaysia': ('product', 'water-leaking-sensor-system-gta03wlss'),
    # services
    'grease-trap-services': ('service', 'grease-trap-cleaning-maintenance'),
    'sewerage-and-manhole-services': ('service', 'sewerage-and-manhole-services'),
    'pome-pond-cleaning-desludging-services-malaysia': ('service', 'pome-pond-cleaning-desludging'),
    'schedule-waste-collection-register': ('service', 'schedule-waste-collection-register'),
    'water-supply-and-pumping-services-to-palm-oil-mills': ('service', 'water-supply-pumping-palm-oil-mills'),
    'toilet-floor-trap-declogging-service': ('service', 'toilet-floor-trap-declogging'),
    'gpt-gross-pollution-trap-cleaning-service': ('service', 'gpt-gross-pollution-trap-cleaning'),
    'public-drain-cleaning-service': ('service', 'public-drain-cleaning'),
    'emergency-pipeline-declogging-service': ('service', 'emergency-pipeline-declogging'),
}

FULL_W, SMALL_W = 1200, 600


def fetch(url, binary=False, tries=4):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=60).read()
            return data if binary else data.decode('utf-8')
        except Exception as e:  # rate limits come back as 429
            if n == tries - 1:
                raise
            time.sleep(2 + 3 * n)


def product_json(handle):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, handle + '.json')
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(fetch(f'{STORE}/products/{handle}.js'))
        time.sleep(0.6)
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def save_image(url, dest_full, dest_small):
    raw = fetch(url + ('&' if '?' in url else '?') + 'width=1600', binary=True)
    im = Image.open(BytesIO(raw))
    im = im.convert('RGBA' if im.mode in ('RGBA', 'LA', 'P') else 'RGB')
    if im.mode == 'RGBA':  # flatten onto white; the artwork is designed on white
        bg = Image.new('RGB', im.size, 'white')
        bg.paste(im, mask=im.split()[3])
        im = bg
    for dest, width in ((dest_full, FULL_W), (dest_small, SMALL_W)):
        out = im if im.width <= width else im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        out.save(dest, 'WEBP', quality=80, method=6)
    return im.size


# Seconds into a clip for its poster, where the default first second is a blur.
POSTER_AT = {'video/undersink-grease-trap-gts01-1.jpg': 2.4}


def save_video(url, dest_mp4, dest_poster, poster_at=1):
    tmp = dest_mp4 + '.src.mp4'
    with open(tmp, 'wb') as f:
        f.write(fetch(url, binary=True))
    # H.264 at no more than 720p, sized for the web; audio kept, quietly compressed.
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp,
                    '-vf', "scale='min(1280,iw)':-2", '-c:v', 'libx264', '-preset', 'slow',
                    '-crf', '28', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    '-c:a', 'aac', '-b:a', '96k', dest_mp4], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(poster_at), '-i', dest_mp4,
                    '-frames:v', '1', '-q:v', '4', dest_poster], check=True)
    os.remove(tmp)


def main():
    videos_on = '--no-video' not in sys.argv
    manifest = {}
    seen_video = {}
    for handle, (kind, slug) in MAP.items():
        d = product_json(handle)
        folder = 'products' if kind == 'product' else 'service'
        os.makedirs(os.path.join(ASSETS, 'img', folder), exist_ok=True)
        entry = {'kind': kind, 'source': f'{STORE}/products/{handle}', 'title': d['title'],
                 'images': [], 'videos': []}
        n_img = n_vid = 0
        for m in d.get('media', []):
            if m['media_type'] == 'image':
                n_img += 1
                rel = f'{folder}/{slug}-{n_img}.webp'
                full = os.path.join(ASSETS, 'img', rel)
                small = full[:-5] + '-sm.webp'
                if not (os.path.exists(full) and os.path.exists(small)):
                    save_image(m['src'], full, small)
                entry['images'].append(rel)
            elif m['media_type'] == 'video':
                srcs = [s for s in m.get('sources', []) if s.get('format') == 'mp4'] or m['sources']
                best = max(srcs, key=lambda s: s.get('height', 0))
                key = best['url'].split('?')[0]
                if key in seen_video:  # GTA9001 and GTA9002 share four clips
                    entry['videos'].append(seen_video[key])
                    continue
                n_vid += 1
                os.makedirs(os.path.join(ASSETS, 'video'), exist_ok=True)
                rel = f'video/{slug}-{n_vid}.mp4'
                poster = f'video/{slug}-{n_vid}.jpg'
                if videos_on and not os.path.exists(os.path.join(ASSETS, rel)):
                    save_video(best['url'], os.path.join(ASSETS, rel), os.path.join(ASSETS, poster),
                               POSTER_AT.get(poster, 1))
                v = {'src': rel, 'poster': poster, 'seconds': round((m.get('duration') or 0) / 1000)}
                seen_video[key] = v
                entry['videos'].append(v)
            elif m['media_type'] == 'external_video' and m.get('host') == 'youtube':
                entry['videos'].append({'youtube': m['external_id']})
        manifest[slug] = entry
        print(f'{slug:46s} images={len(entry["images"])} videos={len(entry["videos"])}')
    with open(os.path.join(ROOT, 'tools', 'autodosing-media.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
