# 🏓 Table tennis split bot

Splits table tennis costs across a group, by clock time.

Cost accrues at the hourly rate whenever at least one person is playing.
Everyone present at that moment splits it equally — the only input is when each
person arrived and left.

```
19:00–20:00  Sasha, Nina, Misha         16 ₾ ÷ 3 = 5.33 ₾ each
20:00–21:00  Sasha, Nina, Misha, Pasha  16 ₾ ÷ 4 = 4.00 ₾ each
```

The hourly rate is only an estimator. As soon as anyone records a contribution,
the total comes from the money actually put in, and the rate stops mattering —
so the session title drops its `· N ₾/час` part from then on (Settings still shows it).

Interface is Russian by default, English available in Settings.

The whole UI is one bot message that redraws itself as you tap — no new
messages, no notifications, no chat spam. Only the final settle-up is posted.

## Setup

**1. Get a token.** Message [@BotFather](https://t.me/BotFather) → `/newbot` →
follow the prompts. It hands you a token.

**2. Put the token in `.env`.** Never paste it into a chat or commit it —
`.env` is gitignored.

```bash
cp .env.example .env
open -e .env          # paste the token after TELEGRAM_BOT_TOKEN=
```

**3. Turn off privacy mode.** Back in @BotFather: `/setprivacy` → pick the bot →
**Disable**. Without this the bot can't see plain messages in a group, so
pasting a table won't work.

**4. Install and run.**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh              # restarts the bot if it ever dies
```

**5. Add the bot to your group** and send `/split`.

**6. Privacy mode must be ON** (`/setprivacy` → Enable), and the bot has to be
**removed and re-added to the group** for the change to take effect. With it on,
Telegram delivers only commands and replies to the bot's own message — the bot
never sees ordinary conversation. Never make it a group admin: admins receive
all messages regardless of the privacy setting, which silently undoes this.

---

## The live deployment

Running 24/7 on Oracle Cloud (Always Free tier), independent of any laptop.

| | |
| --- | --- |
| Host | `DEPLOY_HOST` in `.env` — kept out of the repo; **ephemeral IP**, see below |
| Provider | Oracle Cloud, Frankfurt, AD-2 |
| Shape | `VM.Standard.E2.1.Micro` (always free) — 1 GB RAM, 45 GB disk |
| OS | Ubuntu 24.04 |
| Path | `/home/ubuntu/pingpong-split-bot` |
| Service | `pingpong.service` (systemd, enabled — starts on boot) |
| SSH key | `~/.ssh/oracle_pingpong` (local, dedicated to this box) |
| OCI CLI profile | `pingpong`, token auth |

Ampere (`A1.Flex`, the 4-core/24 GB shape) was out of host capacity in all three
Frankfurt ADs. The AMD micro runs the bot at ~165 MB, so there is no reason to
chase Ampere; retry only if you want the bigger box for something else.

### Everyday commands

```bash
./deploy/deploy.sh                            # rsync code + reinstall deps + restart
ssh -i ~/.ssh/oracle_pingpong <DEPLOY_HOST>
journalctl -u pingpong -f                     # live log (on the server)
sudo systemctl restart pingpong
```

`deploy.sh` never copies `.env`, `pingpong.db` or `.venv` — the server keeps its
own, so a deploy can't clobber a live session or overwrite the token.

### If the IP changes

The public IP is **ephemeral**: it survives reboots, but a stop/start assigns a
new one. To find it again:

```bash
export OCI_CLI_AUTH=security_token OCI_CLI_PROFILE=pingpong
oci compute instance list --compartment-id <tenancy-ocid> --display-name pingpong-bot --query 'data[0].id' --raw-output
oci compute instance list-vnics --instance-id <instance-ocid> --query 'data[0]."public-ip"' --raw-output
```

Then put the new address in `DEPLOY_HOST` in `.env`. The OCI session token
expires after about an hour; renew with
`oci session authenticate --region eu-frankfurt-1 --profile-name pingpong`.

### Only one poller at a time

A bot token can be long-polled by exactly one process. If the bot starts
behaving erratically — updates landing sometimes and not others — check that
nothing is still running locally:

```bash
pgrep -fl "bot.py --pingpong|run.sh"
```

`run.sh` is for local development only; it respawns the bot, so kill the wrapper
and not just the Python process.

### Keeping the account alive

Oracle deems accounts idle for 30+ days eligible for reclamation, and terminations
of Always Free tenancies do happen without warning. Log into the console
occasionally. If the box disappears, everything here is reproducible: the code is
in this repo, and the only unrecoverable thing is `.env`, which is just the token
from @BotFather.

## Commands

There are two, and they're the same command.

| Command | What it does |
| --- | --- |
| `/split` | Empty session with a table template — fill it in and send it back |
| `/split @misha @pasha masha` | Start with those players, tagged or not — time and paid show `-` until each fills them in |
| `/split @misha 19-21 @pasha 20-22` | …with a time each — a time belongs only to the name before it |
| `/split <Google Sheets link>` | Reads the table from the sheet |
| `/split <code>` | Opens a copy of a session from another chat — see Copying a session |

`/start` and `/help` print the FAQ. Everything else is buttons.

The FAQ — both the `/help` reply and the panel's FAQ screen — opens with a
three-step guide image (`/split` → copy the table → reply with the rows) shown as
a large link preview above the text (a photo caption caps at 1024 characters; the
FAQ is longer). The image is `assets/faq-guide.png`,
served from a public gist at a revision-pinned URL (`FAQ_IMAGE_URL` in `bot.py`).
Telegram caches previews per URL, so to change the picture push a new revision to
the gist and point `FAQ_IMAGE_URL` at it. Every other panel screen sends with
previews disabled, so the image disappears when you leave the FAQ.

## What the bot reads from the chat

Nothing, by default. It only listens inside a window that somebody opened, and
only to that person:

| Window | Opened by | Accepts | Closes |
| --- | --- | --- | --- |
| table | `/split` creating the session | a pasted table or a Sheets link | on the first table that parses, or once the session has any player |
| new player | ＋ Игрок | a name, or `Имя 19-21 35` | on success, or after 3 minutes |
| time / contribution / name / debt / rate | their own buttons | the value asked for | on success, or after 3 minutes |

A time is always a start and an end joined by a dash: `21-23`, `21:30 - 22:30`.
A bare number after a name is what they paid — `@misha 45`, `@misha 20-22 45`.
The order is name, time, money everywhere — `/split`, `/add`, `/edit`, ＋ Игрок
and pasted tables alike. A number typed ahead of the time is ignored
(`@misha 45 20-22` keeps the time and drops the 45, so paid is 0), and a number is never
part of a name. Punctuation after a time or an amount is fine — `@misha 20-22 45, @pasha`.
Times roll past midnight automatically — `22:00-01:30` is three and
a half hours. A single window is capped at 12 hours.

Existing players are edited from their own screen, never by typing in the chat.
That screen and the ones under it (🕐 Время, 💰 Взнос, Прошлый долг) show only
that player's line and hint — the session tables are on the main screen alone,
so nobody takes a player screen for the main one and forgets to tap back.

## Multiple windows per player

Someone who left and came back gets more than one window. On their time screen,
＋ Окно adds one; the chips at the top switch between them. Gaps cost nobody —
billing only runs while at least one person is present.

In a table it needs no special syntax: repeat the name, or leave the name cell
empty to continue the row above. Both forms below give Anton two windows.

```
Anton  19:00  20:00  35        Anton  19:00  20:00  35
Boris  19:00  22:00       ≡           21:00  22:00
Anton  21:00  22:00            Boris  19:00  22:00
```

Overlapping windows for one person are not double-billed.

## Not filled in yet

Paid left out next to a time is 0 — nobody types the obvious, so
`/edit 21:20-00:00` means paid nothing. Left out with no time either, both are
`-` (`/split @misha @pasha`). A `-` keeps a value for the player to fill in:
`@misha - 35`, `@misha 20-22 -`, a table row `Misha  -  -`. That is also how
⬇️ Скачать таблицу writes an unfilled amount, so a downloaded table pastes back
unchanged. A command naming only someone's time leaves an amount they already
entered alone; `/edit 20-22 -` puts it back to `-`. This holds for every command,
＋ Игрок and pasted tables; the 🕐 Время screen leaves paid as it was.

The panel shows `-` in an unfilled cell, and right under its title
names everyone who still has something to fill in — each taps their name →
🕐 Время / 💰 Взнос, or sends `/edit 20-22 35`. An `/edit` with no name edits
the sender, matched by their @username. **`0` is an answer — paid nothing; `-` is not.**
Until every player has both a time and a paid amount the button reads
⏳ Рассчитать (ждём данные всех игроков), and tapping it names who is missing.

Opening 🕐 Время for someone on `-` gives them the session's span straight
away (earliest start to latest end among the others, 19:00–21:00 when nobody
has a time), ready to nudge; opening 💰 Взнос for someone on `-` sets it to 0.
Очистить on either screen puts that value back to `-` and steps back to the player.
On 💰 Взнос, rows of −1 / ＋1, −5 / ＋5 and −10 / ＋10 nudge the amount — never
below 0, and a payment tied to a window (`12.5 21:30-22:15`) keeps its window.
Like 🕐 Время's 5, 15 and 60 мин rows (start on the left, end on the right),
they sit between the ✏ buttons and Очистить, the last row above ‹ Назад.

A player with no time yet counts toward nothing — they stay out of the split
and the ИТОГО block until their time is in.

Sessions saved before this existed read an empty contribution as 0, as they
always did.

## Settles separately

A player left out of the transfers — settling in cash, no card, no contact to
send to. Their contribution still counts; the difference is spread evenly
across everyone else.

## Closing without settling

⚙️ Настройки → 🗑 Закрыть сессию (the last row, above ‹ Назад, right of 📋 Копировать сессию) asks once — it
names how many players and how much money are in the session — and on 🗑 Да,
закрыть deletes the session outright. No settle-up is posted; the panel is left
as one line, `🗑 Сессия 03.11.26 закрыта @misha без расчёта`, with no buttons,
and the next `/split` starts fresh without asking. The group's settings — rate,
currency, language, rounding, table style — stay.

## Copying a session

⚙️ Настройки → 📋 Копировать сессию saves a snapshot of the session as it is
at that tap and shows a command like `/split k3mq7xwd2p` — tap it in Telegram
to copy it. Sent in any other chat (or the same one), it opens that snapshot as
a new session: the same players, times, payments, debts, date, rate, currency and
rounding, while the language and table style stay that chat's own. It replaces
whatever session the chat has like any other `/split`, asking first when that
one has players.

The code is worked out from what the copy carries, so tapping again with nothing
changed gives the same code, and any change to those fields gives a new one — a
code already handed out keeps meaning exactly what it meant. Moving around the
panel isn't a change. Codes are 10 characters with no 0/o or 1/l/i, matched
case-insensitively, and never expire.

## What gets remembered

In SQLite (`pingpong.db`):

- **The active session**, per group — survives restarts, so the panel keeps working.
- **The rate, currency, language, rounding and table style**, per group.
- **Every session copy**, by its code.

Past sessions aren't stored. The posted settle-up message in the group is the
record, and ⬇️ Скачать таблицу exports the current one as TSV.

## Files

| File | Role |
| --- | --- |
| `model.py` | Session data, the time-slice algorithm, settlement, parsers |
| `render.py` | One function per screen — returns title, body, keyboard |
| `i18n.py` | Every user-facing string in Russian and English |
| `store.py` | SQLite persistence |
| `bot.py` | Handlers, callback routing, coalesced message edits |
| `run.sh` | Supervisor loop — restarts the bot when it exits |

## Notes

Edits are coalesced per chat: if a tap arrives while an edit is in flight, it's
folded into the next one. A single tap still redraws immediately — mashing
`+15` collapses into one API call instead of tripping Telegram's rate limit.
Handlers hold a per-chat lock, so simultaneous taps from two people can't lose
one another's changes.

Tables render as monospace text so the columns line up. Settings switches
between plain monospace and a tinted `<pre>` block.

Rounding to whole amounts is on by default. Shares are apportioned by largest
remainder, and any sub-unit residue lands on the largest balance, so the
transfers always cancel exactly.

Transfers are planned for the fewest payments, and among plans with that count
the one that spreads them most evenly — nobody sends three while someone else
sends one (then the same evenness for who receives). Each plan walks payers and
receivers in some order, each payer filling receivers until their debt runs out;
every ordering is tried. That search runs on every redraw, so past 800 orderings
(e.g. 5 payers × 4 receivers, 386 ms on the VM) only the largest-first ordering
is used; 4 × 4 and 5 × 3 are still searched.

A Telegram outage can poison the HTTP pool and leave polling hung forever
without the process exiting. A watchdog probes the same connection every
minute and exits after three failures; `run.sh` brings it back.
