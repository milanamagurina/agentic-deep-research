# Deploy on a Nebius VM (public, always-on)

The app is **CPU-only** — it just calls Token Factory + Tavily over HTTPS — so the smallest VM is plenty.
No GPU. It runs in Docker with `--restart unless-stopped`, so it survives reboots and stays up "forever"
as long as the VM is running.

> Token Factory (your inference keys) is *not* where this runs. You create the server in **Nebius AI Cloud
> → Compute**. Token Factory is only the model endpoint the app calls.

## 1. Create the VM (Nebius AI Cloud console)

- **Compute → Virtual machines → Create**.
- Image: **Ubuntu 22.04 or 24.04**.
- Size: smallest shared/CPU preset (≈ **2 vCPU / 4 GB**) is enough.
- **Public IP: enabled**, and add your **SSH public key**.
- **Allowed ports / security group:** allow inbound **TCP 22** (SSH) and **TCP 8501** (the app) from `0.0.0.0/0`.
  This is the step people forget — without 8501 open, the page will not load from outside.

Note the VM's **public IP**.

## 2. Deploy (one command, on the VM)

SSH in, then run the bootstrap script. It installs Docker, pulls this branch, asks for your two API keys
once, builds the image, and starts the container:

```bash
ssh ubuntu@<PUBLIC_IP>
curl -fsSL https://raw.githubusercontent.com/SirPhlittes/Agentic-Deep-Research-with-Token-Factory-and-Tavily/milanamagurina/deploy/bootstrap.sh -o bootstrap.sh
bash bootstrap.sh
```

(If the repo is private, either make it public, or `git clone` it with a GitHub token / `scp` the folder up,
then run `bash deploy/bootstrap.sh` from inside it.)

When it finishes it prints the URL. Open:

```
http://<PUBLIC_IP>:8501
```

Share that with the judges.

## 3. Day-2

```bash
docker logs -f evidence-research        # live logs
docker restart evidence-research        # restart
bash deploy/bootstrap.sh                # redeploy latest code (keeps your .env)
```

## Cost / safety

- A small CPU VM bills by the hour while it runs — stop/delete it after judging to stop charges.
- Every visitor who runs **Live** mode spends your Token Factory + Tavily budget. `bootstrap.sh` writes
  conservative caps into `.env` (`MAX_*`). For a zero-cost public demo, remove `NEBIUS_API_KEY` and
  `TAVILY_API_KEY` from `.env` and `docker restart evidence-research` — the synthetic demos, the saved live
  Nebius run, and the one-click Citation Check all work without keys.
- `.env` lives only on the VM (chmod 600) and is never committed.

## Optional: HTTPS on a domain

Point an A record at the VM, open 80/443, and run Caddy in front for automatic TLS:

```bash
docker run -d --name caddy --restart unless-stopped --network host \
  -v caddy_data:/data \
  caddy:2 caddy reverse-proxy --from your.domain.com --to localhost:8501
```

Then the app is at `https://your.domain.com` and you can close 8501 to the public.
