# pingpong-split-bot

Splits table tennis costs by clock time. Runs as a systemd service on an Oracle Always Free VM whose public IP is **ephemeral**, so a failed deploy is usually a reassigned IP rather than a broken box.

`README.md` is the source of truth for behaviour, setup and deployment — read it rather than the code, and **update it in the same change that alters behaviour**, never as a follow-up.

## Every change ships

After the last edit of any change, commit it and redeploy — no separate ask for either, and never leave the change running only in the old process. One commit per change, its message saying what changed and why. Deploy with the script in `README.md` under "The live deployment"; the host is `DEPLOY_HOST` in `.env`. **Never push** without an ask in the current message. Boundary: this commit-and-deploy authorization covers this repo only (`orim-ios-bot` holds its own); every other outward-facing action still needs its own ask. A failed deploy (IP changed, SSH refused) is reported, not retried blind.

## Every reply about the bot ends with the push reminder

Close every reply that touches this bot — a change or just an answer about it — with one line counting what GitHub doesn't have yet, taken from `git rev-list --count origin/master..HEAD` run right before writing it, never from memory: `Change deployed, N unpushed commits waiting.` after a change, `N unpushed commits waiting.` otherwise; with nothing unpushed, leave the line out. Why: pushing waits for an ask, so this count is the only thing that keeps commits from piling up unseen. Boundary: the line replaces the post-commit table the global output rules ask for — here commits go straight to `master`, and the count is what that table would say.

## The repo is public

[svzhukov/pingpong-split-bot](https://github.com/svzhukov/pingpong-split-bot) is a public GitHub repo. The server address, the token, the Anthropic API key and `pingpong.db` (real players' names and group chat ids) live only in gitignored files — never write any of them into a tracked file. The same goes for real players' names anywhere, including examples in `chat_prompt.md` and the guide: use made-up ones (Миша, Маша).

## Reading a chat is tested in the lab first

The test bench for `chat_prompt.md`, `chat_schema.json` and the input `chat_ai.py` builds is `../pingpong-split-lab` — outside this repo because its chats are real. Before changing any of them, read its `README.md`; after, run its cases (free, on the Max login) and only then commit.
