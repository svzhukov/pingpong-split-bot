# 🏓 Table tennis split bot

Splits table tennis costs across a group, by clock time.

Cost accrues at the hourly rate whenever at least one person is playing.
Everyone present at that moment splits it equally — the only input is when each
person arrived and left.

```
19:00–20:00  Sasha, Nina, Misha         16 ₾ ÷ 3 = 5.33 ₾ each
20:00–21:00  Sasha, Nina, Misha, Pasha  16 ₾ ÷ 4 = 4.00 ₾ each
```

The hourly rate is the price of one table. Until anyone records a contribution,
everything is estimated from it. Once money is in, the total is the money
actually put in, and it is spread like this:

- **Tables are bounded by the players**: at least one, at most one per pair
  (`max_tables` in `model.py`) — 1–3 players are one table, 4–5 one or two,
  6–7 up to three.
- **The money says how many table-hours there were**: paid ÷ rate. Every stretch
  starts at one table, and the rest is shared in proportion to each stretch's
  room for more.
- **A stretch costs** its tables × its length × the rate, split equally between
  whoever was playing.
- **Less money than one table for the whole session** means the rate is off, so
  every minute is priced alike instead. **More than every stretch's maximum**
  means the rate is higher than set, so every stretch sits at its maximum,
  scaled up to the money.
- **Money tied to a window** (`12.5 21:30-22:15`) is spread over that window by
  length: it already says what that window cost.

5 people for an hour, then 3 for another, with 48 ₾ paid at 16 ₾/час: that is 3
table-hours, one table each hour plus the one extra the five had room for, so
the first hour is 2 tables (32 ₾ ÷ 5) and the second one (16 ₾ ÷ 3). Someone who
stays on alone pays one table's price for that time, not the evening's average,
which includes the tables the whole group took. The session
title always ends with that price, `· 16 ₾/час`, since it counts both before and
after money is in.

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

`/split` starts a session and `/edit` changes it.

| Command | What it does |
| --- | --- |
| `/split` | Empty session with a table template — fill it in and send it back |
| `/split @misha @pasha masha` | Start with those players, tagged or not — time and paid show `-` until each fills them in |
| `/split @misha 19-21 @pasha 20-22` | …with a time each — a time belongs only to the name before it |
| `/split <Google Sheets link>` | Reads the table from the sheet |
| `/split <code>` | Opens a copy of a session from another chat — see Copying a session |
| `/split <copied chat>` | Reads players, times and money from a copied group chat — see Reading a chat |
| `/edit @masha 20-22 35` | Adds Masha, or fixes her row if she's already in — same name, time, money; several names, or one per line, work too |
| `/edit 20-22 35` | Fixes the sender's own row, found by their @username |

`/start` and `/help` print the guide, «Как это работает». Everything else is
buttons. On the main screen, ＋ Игрок is the row right under the player list, and
❓ Как это работает sits left of ⚙️ Настройки on the row below it; its ‹ Назад
returns to the main screen.

`/add` still works for groups used to it, but the guide no longer lists it:
it takes the same input as `/edit` and only ever adds, leaving anyone already
in the session alone.

⚙️ Настройки → ⬇️ Панель вниз, between 📋 Копировать сессию and
🗑 Закрыть сессию, brings the panel back down when the chat has buried it: the
old message is deleted and a fresh one opens on the main screen. In a group the
bot only reads replies to its panel, so a panel nobody can reach is unusable.

⚙️ Настройки → Дата сессии is the date in the session title, the settle-up and
the downloaded file's name. A new session takes the day it was opened; the row
above the price reads −1 день · ✏ 20.11.26 · ＋1 день, and ✏ takes a reply like
`20.11.2026` (`20.11.26` works too). It belongs to that session alone — the next
`/split` starts on its own day again.

The guide — both the `/help` reply and the panel's ❓ Как это работает screen —
opens with a three-step image (`/split` → copy the table → reply with the rows)
shown as a large link preview above the text, so the guide isn't held to a
photo caption's 1024 characters. The image is `assets/faq-guide.png`,
served from a public gist at a revision-pinned URL (`FAQ_IMAGE_URL` in `bot.py`).
Telegram caches previews per URL, so to change the picture push a new revision to
the gist and point `FAQ_IMAGE_URL` at it. Every other panel screen sends with
previews disabled, so the image disappears when you leave the guide.

## What the bot reads from the chat

Nothing, by default. It only listens inside a window that somebody opened, and
only to that person:

| Window | Opened by | Accepts | Closes |
| --- | --- | --- | --- |
| table | `/split` creating the session | a pasted table, a Sheets link, or a copied chat | on the first table that parses, or once the session has any player |
| new player | ＋ Игрок | a name, or `Имя 19-21 35` | on success, or after 3 minutes |
| time / contribution / name / debt / rate | their own buttons | the value asked for | on success, or after 3 minutes |

A time is always a start and an end joined by a dash: `21-23`, `21:30 - 22:30`,
`21.30-22.30`.
A bare number after a name is what they paid — `@misha 45`, `@misha 20-22 45`.
The order is name, time, money everywhere — `/split`, `/edit`, ＋ Игрок
and pasted tables alike. A number typed ahead of the time is ignored
(`@misha 45 20-22` keeps the time and drops the 45, so paid is 0), and a number is never
part of a name. Punctuation after a time or an amount is fine — `@misha 20-22 45, @pasha`.
Times roll past midnight automatically — `22:00-01:30` is three and
a half hours. A single window is capped at 12 hours.

Existing players are edited from their own screen, never by typing in the chat.
That screen and the ones under it (🕐 Время, 💰 Взнос, Прошлый долг) show only
that player's line and hint — the session tables are on the main screen alone,
so nobody takes a player screen for the main one and forgets to tap back.

## Reading a chat

People report in the group as they finish — `Оплатил 5 стол 17 лари`,
`Играл 19:20-21:25` — and the bot can turn those messages into the session
instead of anyone typing a table:

- **Pasted:** copy the messages (Telegram Desktop, the phone, anywhere that keeps
  the `Имя, [дата время]` header above each one) and send them after `/split`,
  or as a reply to the panel. Not in the guide for now: `/help` mentions only
  forwarding.
- **Forwarded:** select the messages and forward them to the bot in a private
  chat. A batch arrives as one message per forwarded message; the bot gathers
  them until 2 seconds pass with nothing new, then reads them together. The
  session opens in that private chat with its settings; copy it to the group with
  📋 Копировать сессию if wanted. Forwards carry each sender's @username unless
  they hide their account, so players come in tagged.

Claude Haiku (`MODEL` in `chat_ai.py`) reads the text with the instructions in
`chat_prompt.md` and answers in the shape `chat_schema.json` fixes: the date the
games were played, a table price per hour when a message states one, and per
player their windows, what they paid, whether they settle separately, and a
note of a sentence or two on anything it guessed or worked out, such as a guessed
window or money moved from one player to another. A stated price applies to that session only; otherwise
the group's saved rate does. Money a guest handed to a player moves from that
player's payment to the guest, who then settles separately. Unmentioned payment
is 0; a duration alone, or only a start or an end, becomes a guessed window.

Every chat read sends one message of its own just above the panel — the only
message besides the settle-up the bot posts — starting `🤖 Таблица была
сгенерирована из переписки, пожалуйста, перепроверьте и отредактируйте.` and,
when it guessed anything, `Вот мои предположения:` with one line per player,
`• @misha — <note>`. A chat sent as a reply to an existing panel moves the panel
down below that message, so the guesses always sit right above the table. A
name already in the session is updated rather than added twice. Nothing is read unless
`ANTHROPIC_API_KEY` is set in `.env`; a chat longer than 12 000 characters is
refused, and any failure says so in one message and leaves the session as it was.

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
`-` (`/split @misha @pasha`). Over several lines, `/split` and `/edit` read
a line of nothing but @handles (`@pasha,` under `@misha 22-00 75`) the same way;
a plain name alone on a line is skipped, since a table's header row looks just
like one. `/edit` naming someone already in the session with nothing beside them
leaves them as they are. A `-` keeps a value for the player to fill in:
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
On 💰 Взнос, rows of −1 / ＋1, −5 / ＋5 and −20 / ＋20 nudge the amount — never
below 0, and a payment tied to a window (`12.5 21:30-22:15`) keeps its window.
Those steps, and the ±1 next to the hourly price in Settings, are for ₾, ₼, $
and €; in ₽, ₴ and ₺ they are ten times larger (±10 / ±50 / ±200, price ±10),
in ֏ a hundred times (`STEP_SCALE` in `model.py`).
Like 🕐 Время's 5, 15 and 60 мин rows (start on the left, end on the right),
they sit between the ✏ buttons and Очистить, which on both screens is a row of
its own, the last one above ‹ Назад.

A player with no time yet counts toward nothing — they stay out of the split
and the ИТОГО block until their time is in.

Sessions saved before this existed read an empty contribution as 0, as they
always did.

## Settles separately

A player left out of the transfers — settling in cash, no card, no contact to
send to. Their contribution still counts; the difference is spread evenly
across everyone else. While anyone has it on, the main screen says so above the
tables — `Не участвуют в переводах: @misha` — under the list of who still has
something to fill in.

## Closing without settling

⚙️ Настройки → 🗑 Закрыть сессию (the last row, above ‹ Назад, right of ⬇️ Панель вниз) asks once — it
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
- **The rate, currency, language, rounding, table style and minimum transfer**, per group.
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
| `chat_ai.py` | Reads a copied or forwarded chat with Claude; spots a copied chat |
| `chat_prompt.md`, `chat_schema.json` | What the model is told, and the JSON shape it must answer in |
| `run.sh` | Supervisor loop — restarts the bot when it exits |

## Notes

Edits are coalesced per chat: if a tap arrives while an edit is in flight, it's
folded into the next one. A single tap still redraws immediately — mashing
`+15` collapses into one API call instead of tripping Telegram's rate limit.
Handlers hold a per-chat lock, so simultaneous taps from two people can't lose
one another's changes.

Tables render as monospace text so the columns line up. Settings switches
between plain monospace and a tinted `<pre>` block.

Rounding is exact (Точно) by default, and one setting covers every amount
the bot works out — played, balance, debts, the session total, К ОПЛАТЕ and the
transfers, all from paid amounts rounded the same way. The one exception is what
people typed: the Взнос column, the player screens and ⬇️ Скачать таблицу show
paid as entered (58.7 stays 58.7), so a downloaded file pastes back unchanged.
Each share is rounded on its own, so players with the same time always show the
same amount; the residue that leaves over lands on the largest balance, so the
transfers always cancel exactly.

Transfers are planned to avoid crumbs first: an amount to pay is never split into
transfers below the **minimum transfer** in Settings, even at the cost of one more
transfer, while an amount to pay or to receive that is itself below it still goes in one. The
minimum defaults to three of the smallest money step — 3 ₾, 30 ₽, 300 ֏
(`MIN_TRANSFER_STEPS`) — can be nudged or typed in, and goes back to that default
when the currency changes. After that, the fewest payments, and among plans with
that count the one that spreads them most evenly — nobody sends three while
someone else sends one (then the same evenness for who receives).

Each plan walks payers and receivers in some order, each payer filling receivers
until their debt runs out. Every pairing of orders is tried while there are at
most 800 of them (4 × 4 and 5 × 3 are); past that, each side's orders are tried
against the other kept largest-first, and a side of 7 or more isn't reordered.
Walking like that splits a payer only where a receiver fills up, which forces a
crumb with few receivers — six people owing about 12 to two owed 37.5 and 35
leaves someone sending 1 — so a crumb left in the chosen plan is mended: two
payers split the same pair of receivers instead, and every balance stays as it
was. A payer owing less than twice the minimum can't be split that way, so a
small crumb can still remain when debts are that close to it.

A Telegram outage can poison the HTTP pool and leave polling hung forever
without the process exiting. A watchdog probes the same connection every
minute and exits after three failures; `run.sh` brings it back.
