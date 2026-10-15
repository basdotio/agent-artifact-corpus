"""A callback-only receiver. Exposes no UI, local files, credentials or job mutation."""
import http.server,json,os,re,secrets,shutil,subprocess,threading
from config import ROOT

def main():
    executable=shutil.which('cloudflared')
    if not executable:raise SystemExit('Install cloudflared or configure ENHANCOR_WEBHOOK_URL. See docs/SETUP-AGENT.md.')
    route='/callback/'+secrets.token_urlsafe(24)
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):self.send_error(404)
        def do_POST(self):
            if self.path!=route:self.send_error(404);return
            try:size=int(self.headers.get('Content-Length','0'))
            except ValueError:self.send_error(400);return
            if not 0<size<=65536:self.send_error(413);return
            try:json.loads(self.rfile.read(size))
            except ValueError:self.send_error(400);return
            # Polling remains authoritative; unverified callbacks cannot alter jobs.
            self.send_response(200);self.end_headers();self.wfile.write(b'{"received":true}')
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    proc=subprocess.Popen([executable,'tunnel','--url',f'http://127.0.0.1:{server.server_port}','--no-autoupdate'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    state=ROOT/'.runtime-webhook.json'
    try:
        for line in proc.stdout:
            match=re.search(r'https://[a-z0-9-]+\.trycloudflare\.com',line)
            if match:
                fd=os.open(state,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                with os.fdopen(fd,'w') as f:json.dump({'url':match.group(0)+route},f)
                print('Callback tunnel ready. Keep this process running.',flush=True)
        raise SystemExit('Callback tunnel stopped.')
    finally:
        state.unlink(missing_ok=True);proc.terminate();server.shutdown()
if __name__=='__main__':main()
