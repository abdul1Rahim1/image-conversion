# Deploying the service on AWS Lightsail

You can deploy this on your **existing** Lightsail box — no need to buy a new one. The service is a small FastAPI app; it coexists happily with a WordPress install as long as it runs on its own port (default 8000) behind Nginx.

If you'd rather isolate it, spin up a fresh $5/mo Lightsail Ubuntu 22.04 instance and follow the same steps. Everything below assumes Ubuntu 22.04 or 24.04.

## 1. Prep the box

SSH into your Lightsail instance:

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git nginx
sudo timedatectl set-timezone UTC   # optional but keeps logs sane
```

Open port 443 (HTTPS) in the Lightsail firewall UI: Instance → Networking → **Add rule** → HTTPS. Leave 80 open for Let's Encrypt renewals. Do **not** open 8000 to the internet — Nginx will front it on localhost.

## 2. Get the code

```bash
sudo mkdir -p /opt && cd /opt
sudo git clone https://github.com/abdul1Rahim1/image-conversion.git imageconv
sudo chown -R $USER:$USER /opt/imageconv
cd /opt/imageconv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Create the `.env` on the server (never commit this)

```bash
cp .env.example .env
nano .env
```

Fill in the same values you used locally — OpenAI key, Anthropic key, R2 credentials, `SERVICE_API_KEY`, `CATALOG_PATH`, `PUBLIC_BASE_URL`. **Set `ALLOWED_ORIGINS=https://yourstore.com`** (comma-separate if you have staging + prod) — do not leave `*` in production.

Upload your 50-product catalog to the server too:

```bash
# From your laptop:
scp -i ~/.ssh/lightsail-key.pem catalog.json ubuntu@<lightsail-ip>:/opt/imageconv/
```

Then in `.env` set `CATALOG_PATH=catalog.json`.

## 4. systemd unit — auto-start + auto-restart

```bash
sudo tee /etc/systemd/system/imageconv.service >/dev/null <<'EOF'
[Unit]
Description=ImageConv product materialization API
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/imageconv
Environment="PATH=/opt/imageconv/.venv/bin"
EnvironmentFile=/opt/imageconv/.env
ExecStart=/opt/imageconv/.venv/bin/uvicorn service.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now imageconv
sudo systemctl status imageconv --no-pager
```

Verify the app is running locally:

```bash
curl -s http://127.0.0.1:8000/health
# {"ok":true,"catalog_size":50,"cached":0}
```

## 5. Nginx reverse proxy + HTTPS

Point a subdomain — for example `api.yourdomain.com` — at your Lightsail public IP (A record in your DNS provider). Wait a few minutes for propagation, then:

```bash
sudo tee /etc/nginx/sites-available/imageconv >/dev/null <<'EOF'
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        client_max_body_size 20m;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/imageconv /etc/nginx/sites-enabled/imageconv
sudo nginx -t
sudo systemctl reload nginx
```

Issue a free Let's Encrypt cert:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com --redirect --agree-tos -m you@yourdomain.com
```

Verify HTTPS works:

```bash
curl -s https://api.yourdomain.com/health
```

The `--redirect` flag also rewrites HTTP → HTTPS automatically. Renewals are cron-scheduled by certbot; no further action needed.

## 6. Point the WordPress plugin at it

In WP admin → Settings → ImageConv:

- **API URL**: `https://api.yourdomain.com`
- **API Key**: same value as `SERVICE_API_KEY` in the server's `.env`

Save. Search for something in your catalog → external matches should appear.

## 7. Operations

**Deploy a new version:**

```bash
cd /opt/imageconv
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart imageconv
```

**Tail logs:**

```bash
sudo journalctl -u imageconv -f
```

**Update the catalog** :

```bash
scp new_catalog.json ubuntu@<lightsail-ip>:/opt/imageconv/catalog.json
sudo systemctl restart imageconv
```

**Reset the cache** (e.g. after tweaking prompts and wanting fresh regenerations):

```bash
rm /opt/imageconv/cache.sqlite
sudo systemctl restart imageconv
```

## 8. Security checklist before you hand out URLs

- [ ] `SERVICE_API_KEY` in `.env` is at least 32 random chars (`python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] `.env` is `chmod 600` and owned by the service user
- [ ] `ALLOWED_ORIGINS` in `.env` is your storefront domain, not `*`
- [ ] Port 8000 is NOT exposed in the Lightsail firewall (only 80 and 443)
- [ ] R2 API token is scoped to Object Read/Write on the product bucket only
- [ ] `.env` is in `.gitignore` (already is)
- [ ] Nginx access logs rotated by default via `logrotate` — nothing to do

## 9. If you'd rather use a fresh Lightsail box

Buy Instance → Linux/Unix → Ubuntu 22.04 → **$5/mo** (1 vCPU, 512 MB RAM, 20 GB SSD). That's enough for the 50-product test — bump to $10 (1 GB RAM) if you're going to run the pipeline concurrently for many products.

Everything above works identically.
