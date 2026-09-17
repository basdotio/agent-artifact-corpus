---
name: homelab-deploy
description: Deploy a service or static site publicly via CasaOS + VPS reverse proxy. Covers DNS, SSL, nginx config, Docker containers, and static files.
---

# Homelab Deploy Workflow

Deploys services from the homelab to the public internet via:
`Client → VPS nginx (104.168.64.181) → [VPS local | CasaOS:port via WireGuard]`

## Credentials & Access
- **VPS SSH**: `root@104.168.64.181`
- **CasaOS SSH**: `nerfherder@farmstand` (Tailscale only — LAN IP 192.168.50.19 unreachable from this machine)
- **Porkbun API**: stored in Recall — query `porkbun API key`
- **Domain**: `streamy.tube` (all public subdomains live here)

## Decision: VPS-local vs CasaOS tunnel

| Type | Host on VPS | Host on CasaOS |
|------|-------------|----------------|
| Static files (HTML, SPA build) | ✅ Preferred | ❌ Overkill |
| Simple pass-through (no state) | ✅ OK | ✅ OK if port is open |
| Stateful service (DB, media, AI) | ❌ | ✅ Required |

> **WireGuard tunnel constraint**: Only ports **80** and **9010** on CasaOS are currently
> reachable from the VPS via WireGuard. Any new CasaOS service on a custom port requires
> opening that port on OPNsense (Interfaces → WireGuard → Firewall rules).

---

## Path A: Static File (serve from VPS)

### 1. Copy file to VPS
```bash
scp /path/to/file.html root@104.168.64.181:/var/www/{name}/index.html
# Or for a build directory:
scp -r dist/ root@104.168.64.181:/var/www/{name}/
```

### 2. Add DNS A record via Porkbun API
```bash
curl -s -X POST "https://api.porkbun.com/api/json/v3/dns/create/streamy.tube" \
  -H "Content-Type: application/json" \
  -d '{
    "apikey": "PORKBUN_API_KEY",
    "secretapikey": "PORKBUN_SECRET_KEY",
    "type": "A",
    "name": "SUBDOMAIN",
    "content": "104.168.64.181",
    "ttl": "300"
  }'
```

### 3. HTTP-only nginx + certbot
```bash
# Write HTTP config first so certbot can do ACME challenge
ssh root@104.168.64.181 "cat > /etc/nginx/sites-enabled/{subdomain}.streamy.tube << 'EOF'
server {
    listen 80; listen [::]:80;
    server_name {subdomain}.streamy.tube;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
EOF
nginx -t && systemctl reload nginx"

# Issue cert
ssh root@104.168.64.181 "certbot certonly --nginx -d {subdomain}.streamy.tube --non-interactive --agree-tos"
```

### 4. Full HTTPS config (static)
```nginx
server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name {subdomain}.streamy.tube;

    ssl_certificate /etc/letsencrypt/live/{subdomain}.streamy.tube/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{subdomain}.streamy.tube/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    root /var/www/{name};
    index index.html;
    location / { try_files $uri $uri/ =404; }
}

server {
    listen 80; listen [::]:80;
    server_name {subdomain}.streamy.tube;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://$host$request_uri; }
}
```

### 5. Test
```bash
curl -sI https://{subdomain}.streamy.tube | head -3
```

---

## Path B: CasaOS Docker Service (tunnel through WireGuard)

### 1. Deploy container on CasaOS
```bash
ssh nerfherder@farmstand "mkdir -p /DATA/AppData/{name}"
# Write docker-compose.yml, then:
ssh nerfherder@farmstand "cd /DATA/AppData/{name} && docker compose up -d"
```

### 2. Open port on OPNsense (if not port 80)
Firewall → Rules → WireGuard interface → Add rule:
- Protocol: TCP, Destination: CasaOS (192.168.50.19), Port: {service_port}

### 3. Add DNS + VPS nginx (proxy config)
Same DNS step as Path A, then use proxy nginx template:

```nginx
upstream {name} {
    server 192.168.50.19:{port};
    keepalive 16;
}

server {
    listen 443 ssl; listen [::]:443 ssl;
    server_name {subdomain}.streamy.tube;

    ssl_certificate /etc/letsencrypt/live/{subdomain}.streamy.tube/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{subdomain}.streamy.tube/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://{name};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
    }
}
```

---

## Existing VPS Nginx Sites
All configs at `/etc/nginx/sites-enabled/` on VPS. Pattern: one file per subdomain.

Currently deployed: authentik, casa, code-server, codevv, jellyfin, jellyseerr, livekit, mural, n8n, recall, revive, riven, riven-api, sim

## Porkbun API Reference
- Create: `POST /api/json/v3/dns/create/{domain}`
- Delete: `POST /api/json/v3/dns/delete/{domain}/{record_id}`
- List: `POST /api/json/v3/dns/retrieve/{domain}`
- Response includes `id` — save it if you need to delete later
