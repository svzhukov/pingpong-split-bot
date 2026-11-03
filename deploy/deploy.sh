#!/bin/bash
# Push the code to the server and restart it.
#   ./deploy/deploy.sh                    # target from DEPLOY_HOST in .env
#   ./deploy/deploy.sh ubuntu@1.2.3.4
# Never copies .env, pingpong.db or .venv — the server keeps its own.
set -e

cd "$(dirname "$0")/.."

TARGET="${1:-$(sed -n 's/^DEPLOY_HOST=//p' .env 2>/dev/null)}"
if [ -z "$TARGET" ]; then
    echo "No target: pass user@host, or set DEPLOY_HOST=user@host in .env" >&2
    exit 1
fi

KEY="${KEY:-$HOME/.ssh/oracle_pingpong}"
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"

rsync -av --delete -e "$SSH" \
    --exclude '.venv/' \
    --exclude '.env' \
    --exclude '*.db' \
    --exclude '__pycache__/' \
    --exclude '.git/' \
    ./ "$TARGET:~/pingpong-split-bot/"

$SSH "$TARGET" 'cd ~/pingpong-split-bot && .venv/bin/pip install -q -r requirements.txt && sudo systemctl restart pingpong && sleep 3 && systemctl is-active pingpong'

echo "deployed"
