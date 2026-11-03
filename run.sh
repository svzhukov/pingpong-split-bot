#!/bin/bash
# Keeps the bot alive: restarts it if it exits for any reason, including the
# watchdog killing a wedged connection.
cd "$(dirname "$0")" || exit 1
while true; do
    .venv/bin/python bot.py --pingpong
    echo "$(date '+%Y-%m-%d %H:%M:%S')  bot exited — restarting in 3s"
    sleep 3
done
