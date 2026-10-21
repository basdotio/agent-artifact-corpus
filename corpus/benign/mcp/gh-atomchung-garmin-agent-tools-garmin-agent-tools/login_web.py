"""Short-lived loopback login form. Credentials never enter command arguments or chat."""
from __future__ import annotations
import html
import queue
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from .core import save_session, state_home


def serve(region: str, port: int = 8765, timeout: int = 600) -> None:
    """Serve a same-host, nonce-protected login for the user's private browser takeover."""
    from garminconnect import Garmin
    state_home()
    nonce=secrets.token_urlsafe(24)
    shared={'stage':'login','error_type':None}
    lock=threading.Lock()
    otp=queue.Queue(maxsize=1)
    origin=f'http://127.0.0.1:{port}'
    root=f'/{nonce}'

    def stage(value, error_type=None):
        with lock:
            shared.update(stage=value,error_type=error_type)

    def mfa():
        stage('mfa')
        try:
            return otp.get(timeout=min(timeout,300))
        except queue.Empty:
            raise TimeoutError('Private MFA timed out') from None

    def worker(email,password):
        try:
            g=Garmin(email=email,password=password,is_cn=region=='china',prompt_mfa=mfa)
            g.login()
            save_session(g,region)
            stage('success')
        except Exception as exc:
            stage('failed',type(exc).__name__)
        finally:
            email=password=None

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass

        def allowed(self):
            return self.headers.get('Host')==f'127.0.0.1:{port}' and urlsplit(self.path).path==root and not urlsplit(self.path).query

        def send_page(self,status,body):
            encoded=body.encode()
            self.send_response(status)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(encoded)))
            self.send_header('Cache-Control','no-store')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; style-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(encoded)

        def do_GET(self):
            if not self.allowed():
                self.send_page(404,'Not found'); return
            with lock:
                current=dict(shared)
            refresh='<meta http-equiv="refresh" content="2">' if current['stage']=='working' else ''
            head='<!doctype html><html><head><meta charset="utf-8">'+refresh+'<title>Private Garmin login</title></head><body><main>'
            info='<h1>Garmin Agent Tools — private login</h1><p>This is an unofficial tool on your agent computer. This form sends your credentials to the local tool, which authenticates directly with Garmin over HTTPS. Nothing is sent to the tool publisher. Tokens are stored privately on this computer; they are not end-to-end encrypted from the agent platform. Do not enter secrets into chat.</p>'
            hidden=f'<input type="hidden" name="csrf" value="{nonce}">'
            form=f'<form action="{root}" method="post">'+hidden
            if current['stage']=='login':
                body=form+'<label>Garmin email <input type="email" name="email" autocomplete="username" required></label><br><label>Garmin password <input type="password" name="password" autocomplete="off" required></label><br><button type="submit">Sign in to Garmin</button></form>'
            elif current['stage']=='mfa':
                body=form+'<label>Garmin verification code <input type="password" name="otp" autocomplete="one-time-code" required></label><button type="submit">Verify</button></form>'
            elif current['stage']=='success':
                body='<h2>Login completed</h2><p>The private session was saved. You can close this page and ask your agent to run snapshot. No workout has been written.</p>'
            elif current['stage']=='failed':
                body='<h2>Login did not complete</h2><p>Error type: '+html.escape(current['error_type'] or 'unknown')+'</p><p>Restart the helper to try again. No password or provider response is logged.</p>'
            else:
                body='<h2>Signing in…</h2><p>This page refreshes while the Garmin login is running.</p>'
            self.send_page(200,head+info+body+'</main></body></html>')

        def do_POST(self):
            if not self.allowed() or self.headers.get('Origin')!=origin or self.headers.get('Content-Type','').split(';')[0]!='application/x-www-form-urlencoded':
                self.send_page(403,'Refused'); return
            try:
                length=int(self.headers.get('Content-Length','0'))
            except ValueError:
                self.send_page(400,'Invalid request'); return
            if not 0<length<=8192:
                self.send_page(413,'Invalid request'); return
            try:
                values=parse_qs(self.rfile.read(length).decode(),max_num_fields=4)
            except (ValueError,UnicodeDecodeError):
                self.send_page(400,'Invalid request'); return
            if not secrets.compare_digest(values.get('csrf',[''])[0],nonce):
                self.send_page(403,'Refused'); return
            with lock:
                current=shared['stage']
                if current=='login' and values.get('email') and values.get('password'):
                    shared['stage']='working'
                    threading.Thread(target=worker,args=(values['email'][0],values['password'][0]),daemon=True).start()
                elif current=='mfa' and values.get('otp') and otp.empty():
                    shared['stage']='working'
                    otp.put_nowait(values['otp'][0])
                else:
                    self.send_page(409,'Login stage changed; reload'); return
            self.send_response(303); self.send_header('Location',root); self.send_header('Cache-Control','no-store'); self.end_headers()

    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    server.timeout=0.5
    print(origin+root,flush=True)
    deadline=time.monotonic()+timeout
    try:
        while time.monotonic()<deadline:
            server.handle_request()
    finally:
        server.server_close()
