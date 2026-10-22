"""Local preview server with caching switched off.

    python tools/serve.py          # http://127.0.0.1:8080/site/  and  /tests/checks.html
    python tools/serve.py 9000     # another port

Serves the repository root, so the site and the check harness both resolve.
Nothing is cached, so an edit shows on the next reload.
"""
import functools
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
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
    print(f'Serving {ROOT} at http://127.0.0.1:{port}/site/')
    Server(('127.0.0.1', port), functools.partial(Handler, directory=ROOT)).serve_forever()
