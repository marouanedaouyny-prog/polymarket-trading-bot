FROM python:3.11-slim

RUN useradd -m -u 1000 user

WORKDIR /app

RUN echo '{"status":"ok"}' > /app/response.json

USER user

EXPOSE 7860

CMD python -u -c "
import http.server, json, os, sys
port = int(os.environ.get('PORT', '7860'))

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({'status': 'ok', 'path': self.path}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, format, *args):
        sys.stderr.write('[HTTP] %s - %s\n' % (self.client_address[0], format % args))
        sys.stderr.flush()

sys.stderr.write('STARTING on port %d\n' % port)
sys.stderr.flush()
http.server.HTTPServer(('0.0.0.0', port), H).serve_forever()
"