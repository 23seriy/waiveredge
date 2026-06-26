#!/usr/bin/env python3
"""Tiny HTTPS-to-HTTP reverse proxy for local Yahoo OAuth callbacks.

Yahoo requires redirect URIs to use https://. This script listens on
https://localhost:8000 and forwards to http://localhost:8001 (the
kubectl port-forward target).

Usage:
    # Generate a self-signed cert (once):
    openssl req -x509 -newkey rsa:2048 -keyout k8s/localhost.key \
        -out k8s/localhost.crt -days 365 -nodes -subj '/CN=localhost'
    # Run:
    python k8s/https-proxy.py
"""
import http.client
import ssl
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

LISTEN_PORT = 8000       # HTTPS (what Yahoo redirects to)
BACKEND_PORT = 8001      # HTTP  (kubectl port-forward target)
CERT_DIR = Path(__file__).parent

class ProxyHandler(BaseHTTPRequestHandler):
    def _proxy(self):
        conn = http.client.HTTPConnection("localhost", BACKEND_PORT)
        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))
        conn.request(self.command, self.path, body=body, headers=dict(self.headers))
        resp = conn.getresponse()
        self.send_response(resp.status)
        for key, val in resp.getheaders():
            # Sanitize/validate header names and values to prevent response splitting.
            safe_key = key.replace("\r", "").replace("\n", "")
            if (
                safe_key
                and ":" not in safe_key
                and safe_key.strip() == safe_key
                and safe_key.lower() not in ("transfer-encoding",)
            ):
                safe_val = val.replace("\r", "").replace("\n", "")
                self.send_header(safe_key, safe_val)
        self.end_headers()
        self.wfile.write(resp.read())

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _proxy

    def log_message(self, fmt, *args):
        print(f"[https-proxy] {fmt % args}")


def main():
    cert = CERT_DIR / "localhost.crt"
    key = CERT_DIR / "localhost.key"
    if not cert.exists() or not key.exists():
        import subprocess
        print("[https-proxy] Generating self-signed certificate...")
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key), "-out", str(cert),
            "-days", "365", "-nodes", "-subj", "/CN=localhost",
        ], check=True)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(cert), str(key))

    server = HTTPServer(("0.0.0.0", LISTEN_PORT), ProxyHandler)
    server.socket = ctx.wrap_socket(server.socket, server_side=True)
    print(f"[https-proxy] Listening on https://localhost:{LISTEN_PORT} → http://localhost:{BACKEND_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
