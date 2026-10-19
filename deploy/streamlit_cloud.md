# Deploy on Streamlit Community Cloud (free, public, no server)

Use this for a public URL **now** — it needs no Nebius Cloud / Compute access, no VM and no SSH.
(When your Nebius Cloud access is approved, you can additionally run the always-on VM deploy in
[deploy/README.md](README.md). Both can coexist.)

## Steps (you do this once in your browser)

1. Go to **https://share.streamlit.io** and sign in with the GitHub account that can see this repo.
2. **Create app → Deploy a public app from GitHub**, then:
   - **Repository:** `SirPhlittes/Agentic-Deep-Research-with-Token-Factory-and-Tavily`
   - **Branch:** `milanamagurina`
   - **Main file path:** `ui/streamlit_app.py`
3. (Optional — only if you want judges to run **Live** mode) open **Advanced settings → Secrets** and paste:
   ```toml
   NEBIUS_API_KEY = "your-token-factory-key"
   TAVILY_API_KEY = "your-tavily-key"
   NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
   NEBIUS_MODEL = "MiniMaxAI/MiniMax-M3"
   # keep public live usage bounded (every visitor who runs Live spends your credits)
   MAX_RESEARCH_ITERATIONS = "4"
   MAX_SEARCH_QUERIES = "14"
   MAX_EXTRACTED_SOURCES = "16"
   MAX_MODEL_CALLS = "60"
   ```
   **Leave Secrets empty** for a zero-cost public demo: the two offline synthetic scenarios, the saved live
   Nebius run, and the one-click Citation Check all work without any keys.
4. **Deploy.** You get a durable public URL like `https://<app-name>.streamlit.app` — share it with the judges.

## Notes

- Dependencies install from `requirements.txt` at the repo root. The app adds `src/` to `sys.path`, so
  `evidence_research` imports without a build step.
- The app reads secrets via the environment; a shim in `ui/streamlit_app.py` copies Streamlit secrets into the
  environment on start, so the same code runs locally (`.env`), in Docker (`--env-file`), and on Cloud (Secrets).
- The app sleeps after a long idle period and wakes on the next visit — normal for the free tier.
- To update the live app, just push to `milanamagurina`; Streamlit Cloud redeploys automatically.
