/* =========================================================================
   Perangkap Minyak - asset check. Development only, like checks.html.

   A page cannot ask whether a file exists, so this runs in Node instead:
   every image, video, poster and PDF that the data, the page code, the
   stylesheets and the page shells name must be on disk under site/.
   Exits non-zero listing every missing path.

     node tests/check-assets.js             check
     node tests/check-assets.js --orphans   also list media nothing names
   ========================================================================= */
'use strict';

var fs = require('fs');
var path = require('path');

var SITE = path.resolve(__dirname, '..', 'site');
var ASSETS = path.join(SITE, 'assets');

/* Load the data files the way a browser would, into a stand-in window. */
global.window = {};
['site.js', 'catalog.js', 'library.js'].forEach(function (f) {
  require(path.join(ASSETS, 'data', f));
});
var S = window.PM_SITE, C = window.PM_CATALOG, L = window.PM_LIBRARY;

/* Data and page code store media paths relative to assets/img, except the
   folders that sit at the assets root (see PM.asset in core.js). */
var ROOTED = /^(?:video|docs|img|fonts|icons|css|js|data)\//;
var MEDIA = /^(?:[a-z0-9-]+\/)+[^\/\s'"]+\.(?:webp|jpe?g|png|gif|svg|mp4|pdf)$/i;

var wanted = {};
function want(p) { wanted[ROOTED.test(p) ? p : 'img/' + p] = 1; }

/* Every media path anywhere in the three data files. */
(function walk(v) {
  if (typeof v === 'string') { if (MEDIA.test(v)) want(v); return; }
  if (v && typeof v === 'object') Object.keys(v).forEach(function (k) { walk(v[k]); });
})([S, C, L]);

/* The paths the page code builds rather than names. */
L.documents.forEach(function (m) {
  var key = m.model.toLowerCase();
  [['catalogue', 'catalogue'], ['drawing', 'drawings']].forEach(function (k) {
    var spec = m[k[0]];
    want('docs/' + k[1] + '/' + key + '.pdf');
    want('docs/thumbs/' + k[0] + '-' + key + '.webp');
    for (var i = 1; i <= spec.pages; i++) want('docs/pages/' + k[0] + '-' + key + '-' + i + '.webp');
  });
});
L.issues.forEach(function (it) {
  [it.sheet].concat(it.more || []).forEach(function (s) { want(s.img + '.webp'); want(s.img + '-sm.webp'); });
});
want(L.wasteOil.sheet.img + '.webp');
want(L.wasteOil.sheet.img + '-sm.webp');
/* Product and service photos also come as a -sm copy for cards. */
C.products.concat(C.services).forEach(function (x) {
  (x.images || []).forEach(function (src) { want(src.replace(/\.webp$/, '-sm.webp')); });
});

/* Every media path written as a literal in the page code. */
fs.readdirSync(path.join(ASSETS, 'js')).forEach(function (f) {
  var code = fs.readFileSync(path.join(ASSETS, 'js', f), 'utf8');
  var re = /'([^'\s]+)'/g, m;
  while ((m = re.exec(code))) if (MEDIA.test(m[1])) want(m[1]);
});

/* Stylesheet url()s, resolved from the stylesheet that names them. */
['css', 'fonts', 'icons'].forEach(function (dir) {
  fs.readdirSync(path.join(ASSETS, dir)).filter(function (f) { return /\.css$/.test(f); }).forEach(function (f) {
    var css = fs.readFileSync(path.join(ASSETS, dir, f), 'utf8');
    var re = /url\(\s*["']?([^"')]+)["']?\s*\)/g, m;
    while ((m = re.exec(css))) {
      if (/^(?:data:|https?:|#|%23)/.test(m[1])) continue;
      wanted[path.relative(ASSETS, path.join(ASSETS, dir, m[1].split(/[?#]/)[0])).split(path.sep).join('/')] = 1;
    }
  });
});

/* Everything the page shells name: what they load, and the share image and
   logo in their link-preview tags, which are absolute addresses. */
fs.readdirSync(SITE).filter(function (f) { return /\.html$/.test(f); }).forEach(function (f) {
  var html = fs.readFileSync(path.join(SITE, f), 'utf8');
  var re = /\bassets\/((?:img|video|docs|css|js|data|fonts|icons)\/[^"'\s?#)]+)/g, m;
  while ((m = re.exec(html))) wanted[m[1]] = 1;
});

/* A path passed on the command line is checked too, which is how the
   check itself is shown to fail when it should. */
process.argv.slice(2).filter(function (a) { return a.indexOf('--') !== 0; }).forEach(function (p) {
  wanted[p] = 1;
});

var all = Object.keys(wanted).sort();
var missing = all.filter(function (p) { return !fs.existsSync(path.join(ASSETS, p)); });

if (process.argv.indexOf('--orphans') !== -1) {
  var orphans = [];
  ['img', 'video', 'docs'].forEach(function scan(dir) {
    fs.readdirSync(path.join(ASSETS, dir)).forEach(function (f) {
      var rel = dir + '/' + f;
      if (fs.statSync(path.join(ASSETS, rel)).isDirectory()) scan(rel);
      else if (!wanted[rel]) orphans.push(rel);
    });
  });
  console.log('ORPHANS ' + orphans.length + ':');
  orphans.forEach(function (p) { console.log('  assets/' + p); });
}

if (missing.length) {
  console.error('MISSING ' + missing.length + ' of ' + all.length + ' assets:');
  missing.forEach(function (p) { console.error('  assets/' + p); });
  process.exit(1);
}
console.log('OK ' + all.length + ' assets present');
