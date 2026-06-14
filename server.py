"""Minimal HTTP health-check server for HF Spaces routing test."""
import http.server, json, os, sys

port = int(os.environ.get("PORT", "7860"))


class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok", "path": self.path}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.client_address[0], fmt % args))
        sys.stderr.flush()


if __name__ == "__main__":
    sys.stderr.write("SERVING on 0.0.0.0:%d\n" % port)
    sys.stderr.flush()
    http.server.HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()
