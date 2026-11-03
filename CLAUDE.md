# pingpong-split-bot

Splits table tennis costs by clock time. Runs as a systemd service on an Oracle Always Free VM whose public IP is **ephemeral**, so a failed deploy is usually a reassigned IP rather than a broken box.

`README.md` is the source of truth for behaviour, setup and deployment — read it rather than the code, and **update it in the same change that alters behaviour**, never as a follow-up.

## Every change ships

A change ships by redeploying. After the last edit of any change, redeploy and report it — no separate ask, and never leave the change running only in the old process. Deploy with the script in `README.md` under "The live deployment"; the host is `DEPLOY_HOST` in `.env`.

## The repo is public

[svzhukov/pingpong-split-bot](https://github.com/svzhukov/pingpong-split-bot) is a public GitHub repo. The server address, the token and `pingpong.db` (real players' names and group chat ids) live only in gitignored files — never write any of them into a tracked file. Boundary: standing authorization for this repo and `orim-ios-bot` only; every other outward-facing action still needs its own ask. A failed deploy (IP changed, SSH refused) is reported, not retried blind.
