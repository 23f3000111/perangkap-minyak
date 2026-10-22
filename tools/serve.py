"""Local preview server with caching switched off.

    python tools/serve.py          # http://127.0.0.1:8080/perangkap-minyak/  and  /tests/checks.html
    python tools/serve.py 9000     # another port

Serves the repository root, so the site and the check harness both resolve,
and also serves site/ at /perangkap-minyak/, the path GitHub Pages gives it,
answering a missing page there with site/404.html as Pages does.
Nothing is cached, so an edit shows on the next reload.
"""
import functools
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = '/perangkap-minyak/'


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith(PREFIX):
            path = '/site/' + path[len(PREFIX):]
        return super().translate_path(path)

    def send_error(self, code, message=None, explain=None):
        if code != 404 or not self.path.startswith(PREFIX):
            return super().send_error(code, message, explain)
        with open(os.path.join(ROOT, 'site', '404.html'), 'rb') as fh:
            body = fh.read()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, max-age=0')
        super().end_headers()

    def log_message(self, *args):
        pass


class Server(http.server.ThreadingHTTPServer):
    request_queue_size = 256   # a page asks for dozens of images at once
    daemon_threads = True


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f'Serving {ROOT} at http://127.0.0.1:{port}{PREFIX}')
    Server(('127.0.0.1', port), functools.partial(Handler, directory=ROOT)).serve_forever()
