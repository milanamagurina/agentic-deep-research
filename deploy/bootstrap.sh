#!/usr/bin/env bash
# Deploy the Probabilistic Evidence Research UI on a fresh Nebius Ubuntu VM.
#
# Run ON THE VM (Ubuntu 22.04/24.04), as a user with sudo:
#   curl -fsSL https://raw.githubusercontent.com/SirPhlittes/Agentic-Deep-Research-with-Token-Factory-and-Tavily/milanamagurina/deploy/bootstrap.sh -o bootstrap.sh
#   bash bootstrap.sh
#
# It installs Docker, fetches the repo, asks for your API keys once, builds the image,
# and runs the app on port 8501 with --restart unless-stopped so it survives reboots.
#
# Re-running it redeploys the latest code without touching your saved keys.
set -euo pipefail

REPO="https://github.com/SirPhlittes/Agentic-Deep-Research-with-Token-Factory-and-Tavily.git"
BRANCH="milanamagurina"
DIR="$HOME/evidence-research"
IMAGE="evidence-research:latest"
PORT="${PORT:-8501}"

echo "==> 1/5 Installing Docker (if missing)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
  echo "    Docker installed. (You may need to log out/in for group changes; this script uses sudo meanwhile.)"
fi
DOCKER="docker"; docker info >/dev/null 2>&1 || DOCKER="sudo docker"

echo "==> 2/5 Fetching the repository ($BRANCH)"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" fetch --depth 1 origin "$BRANCH" && git -C "$DIR" checkout -f "$BRANCH" && git -C "$DIR" reset --hard "origin/$BRANCH"
else
  git clone --depth 1 --branch "$BRANCH" "$REPO" "$DIR"
fi
cd "$DIR"

echo "==> 3/5 Configuring credentials (.env)"
if [ ! -f .env ]; then
  cp .env.example .env 2>/dev/null || touch .env
  read -rp "    NEBIUS_API_KEY (Token Factory): " NEBIUS_KEY
  read -rp "    TAVILY_API_KEY: " TAVILY_KEY
  {
    echo "NEBIUS_API_KEY=$NEBIUS_KEY"
    echo "TAVILY_API_KEY=$TAVILY_KEY"
    echo "NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1"
    echo "NEBIUS_MODEL=MiniMaxAI/MiniMax-M3"
    echo "STREAMLIT_SERVER_HEADLESS=true"
    # Keep public live usage bounded: every visitor who runs 'Live' spends these budgets.
    echo "MAX_RESEARCH_ITERATIONS=4"
    echo "MAX_SEARCH_QUERIES=14"
    echo "MAX_EXTRACTED_SOURCES=16"
    echo "MAX_MODEL_CALLS=60"
  } > .env
  chmod 600 .env
  echo "    Wrote .env (chmod 600). Edit it to change caps or run synthetic-only (remove the two keys)."
else
  echo "    .env already present — keeping it."
fi

echo "==> 4/5 Building the image"
$DOCKER build -t "$IMAGE" .

echo "==> 5/5 Starting the container on :$PORT (restart unless-stopped)"
$DOCKER rm -f evidence-research >/dev/null 2>&1 || true
$DOCKER run -d --name evidence-research --restart unless-stopped \
  -p "${PORT}:8501" --env-file .env -v "$DIR/data:/app/data" "$IMAGE"

IP="$(curl -fsS https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
echo
echo "Done. Open:  http://${IP}:${PORT}"
echo "Logs:        $DOCKER logs -f evidence-research"
echo "Redeploy:    bash deploy/bootstrap.sh   (pulls latest $BRANCH, keeps your .env)"
echo
echo "IMPORTANT: open port ${PORT}/tcp to the internet in the Nebius security group /"
echo "allowed-ports for this VM, or the page will not load from outside."
