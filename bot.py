import asyncio
import json
import logging
import os
import re
import weakref
from datetime import datetime
from html import escape
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import Command, CommandObject
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, LinkPreviewOptions, Message)
from dotenv import load_dotenv

from i18n import LANGUAGES, t
from model import (BLANK, CURRENCY_RE, DAY, DEFAULT_LENGTH, NAME_LIMIT, SYMBOL_BY_CODE, Player,
                   Session, clamp_span,
                   compute, extract_span, fmt_money, parse_paid, parse_roster,
                   parse_amount_note, parse_table, sheet_export_url,
                   COPIED_FIELDS, copy_code, new_id, parse_date, parse_entry, parse_time, shift_date,
                   today, transfer_minimum)
from render import (Keyboard, plain_title, players_label, posted_title, render, summary,
                    table_csv)
from store import Store

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "pingpong.db")

if not TOKEN:
    raise SystemExit(
        "TELEGRAM_BOT_TOKEN is not set.\n"
        "Copy .env.example to .env and paste your token from @BotFather."
    )

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("pingpong")

bot = Bot(token=TOKEN)
dp = Dispatcher()
store = Store(DB_PATH)


def markup(keyboard: Keyboard) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=data) for label, data in row]
        for row in keyboard
    ])


# a caption caps at 1024 characters, so the screenshot rides above the text as
# a link preview and the guide can be any length; the URL is pinned to a gist revision,
# because Telegram caches previews per URL — a new image needs a new revision
FAQ_IMAGE_URL = ("https://gist.githubusercontent.com/svzhukov/232fe370500a628be15c14afa77f4ff6"
                 "/raw/5a1689a300db1bebc647ff678e44c1219a0acde4/faq-guide.png")
FAQ_PREVIEW = LinkPreviewOptions(url=FAQ_IMAGE_URL, prefer_large_media=True, show_above_text=True)
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


def preview_of(session: Session) -> LinkPreviewOptions:
    return FAQ_PREVIEW if session.screen == "help" else NO_PREVIEW


def body_of(session: Session):
    title, text, keyboard = render(session)
    return "<b>{}</b>\n\n{}".format(escape(title), text), markup(keyboard)


_busy = set()
_dirty = set()
_locks = weakref.WeakValueDictionary()


def chat_lock(chat_id: int) -> asyncio.Lock:
    """Every handler mutates load-then-save, and some await in between (the
    sheet fetch takes seconds), so two people acting at once would otherwise
    lose one of the changes to last-write-wins. Held weakly: whoever is inside
    the `async with` keeps it alive, and it disappears once the chat goes
    quiet, so idle groups cost nothing."""
    lock = _locks.get(chat_id)
    if lock is None:
        lock = _locks[chat_id] = asyncio.Lock()
    return lock


async def push(chat_id: int) -> None:
    _dirty.add(chat_id)
    if chat_id in _busy:
        return

    _busy.add(chat_id)
    try:
        while chat_id in _dirty:
            _dirty.discard(chat_id)
            session = store.load(chat_id)
            if session:
                await draw(session)
    finally:
        _busy.discard(chat_id)


async def draw(session: Session, force_new: bool = False) -> None:
    text, keys = body_of(session)

    if session.message_id and not force_new:
        try:
            await bot.edit_message_text(
                chat_id=session.chat_id, message_id=session.message_id,
                text=text, reply_markup=keys, parse_mode="HTML",
                link_preview_options=preview_of(session),
            )
            return
        except TelegramRetryAfter as err:
            await asyncio.sleep(err.retry_after)
            return await draw(session, force_new)
        except TelegramBadRequest as err:
            if "not modified" in str(err).lower():
                return
            log.info("edit failed (%s) — sending a fresh panel", err)

    message = await bot.send_message(session.chat_id, text, reply_markup=keys, parse_mode="HTML",
                                     link_preview_options=preview_of(session))
    session.message_id = message.message_id
    store.save(session)


def lang_of(chat_id: int) -> str:
    return store.settings(chat_id)[2]


def replies_to_panel(message: Message, session: Session) -> bool:
    """In a group, privacy mode means Telegram only hands us replies to our own
    message; checking it here too keeps a reply to the posted summary from being
    read as input. A one-to-one chat has nothing to overhear and no other
    conversation to confuse us with, so anything sent there is for us.
    (Telegram gives private chats a positive id and groups a negative one.)"""
    if session.chat_id > 0:
        return True

    reply = message.reply_to_message
    return bool(reply and session.message_id and reply.message_id == session.message_id)


def roster_from(args):
    return parse_roster(args or "")


def handle_of(user) -> str:
    return "@" + user.username if user.username else (user.first_name or "?")


def blank_session(chat_id: int) -> Session:
    rate, currency, lang, rounding, blocks, min_transfer = store.settings(chat_id)
    return Session(chat_id=chat_id, date=today(),
                   rate=rate, currency=currency, lang=lang, rounding=rounding, blocks=blocks,
                   min_transfer=min_transfer)


def looks_like_table(args: str) -> bool:
    """A pasted table always arrives with newlines or tabs; a hand-typed roster
    like "@миша 19-21 @паша" never does."""
    return "\n" in (args or "") or "\t" in (args or "")


def apply_rows(session: Session, rows, only_new: bool = False,
               editing: bool = False) -> int:
    """A name repeated across rows is the same person with another window;
    a row with no name at all continues the row above it. With only_new, names
    already in the session are left untouched — /add never edits; with
    editing, a row naming someone already in the session with nothing beside
    it leaves them alone, as /edit typed on one line does."""
    touched, last, stated = set(), None, {}

    for name, frm, to, paid in rows:
        player = session.find_by_name(name) if name else last

        if name and only_new and player is not None and player.id not in touched:
            last = None
            continue
        if name and editing and player is not None and frm is None and paid is None:
            last = None
            continue
        if player is None and not name:
            continue

        if player is None:
            player = Player(id=new_id(), name=name[:NAME_LIMIT])
            session.players.append(player)
        elif player.id not in touched:
            player.spans = []

        if frm is not None:
            player.add_span(frm, to)
        touched.add(player.id)
        last = player

        if paid is not None:
            stated[player.id] = paid

    # after every row, so a second window's empty money cell can't zero the first's
    for player_id in touched:
        apply_paid(session, session.player(player_id), stated.get(player_id))

    return len(touched)


def apply_paid(session: Session, player: Player, paid) -> None:
    """Money as stated, and "-" puts it back for them to fill in. None stated
    next to a time is 0 — nobody types the obvious — unless they already had an
    amount, which a command naming only their time leaves alone."""
    if paid == BLANK:
        session.clear_paid(player.id)
    elif paid is not None:
        session.set_paid(player.id, paid)
    elif player.spans and not player.paid_set:
        session.set_paid(player.id, 0)


def session_from_table(chat_id: int, rows) -> Session:
    session = blank_session(chat_id)
    apply_rows(session, rows)
    return session


def copied_session(chat_id: int, source: Session) -> Session:
    """Everything that decides the numbers comes from the copy; how the chat
    reads it — language, table style — stays this chat's own."""
    session = blank_session(chat_id)
    for name in COPIED_FIELDS:
        setattr(session, name, getattr(source, name))
    return session


def fresh_session(chat_id: int, roster) -> Session:
    session = blank_session(chat_id)
    add_roster(session, roster)
    return session


def add_roster(session: Session, roster) -> int:
    """Names already in the session are skipped — adding never edits. No time
    leaves the player on "-" until they fill it in."""
    added = 0

    for name, handle, frm, to, paid in roster:
        if not name or session.find_by_name(name):
            continue
        spans = [clamp_span(frm, to)] if frm is not None else []
        player = Player(id=new_id(), name=name[:NAME_LIMIT], handle=handle, spans=spans)
        session.players.append(player)
        apply_paid(session, player, paid)
        added += 1

    return added


def edit_roster(session: Session, roster) -> int:
    """A name not in the session yet is added, as add_roster would; for anyone
    already in it a stated span replaces their time."""
    changed = 0

    for name, handle, frm, to, paid in roster:
        player = session.find_by_name(name)
        if not player:
            changed += add_roster(session, [(name, handle, frm, to, paid)])
            continue

        if frm is None and paid is None:
            continue

        if frm is not None:
            player.spans = [clamp_span(frm, to)]
        apply_paid(session, player, paid)
        changed += 1

    return changed


def own_roster(session: Session, user, args: str):
    """/edit with no name at all edits whoever sent it, found by their @username."""
    roster = roster_from(args)
    if roster or not user.username or not session.find_by_name(user.username):
        return roster
    return roster_from("@{} {}".format(user.username, args))


@dp.message(Command("start", "help"))
async def on_help(message: Message):
    await message.answer(t(lang_of(message.chat.id), "help"), parse_mode="HTML",
                         link_preview_options=FAQ_PREVIEW)


SHEET_TIMEOUT = 8


async def fetch_sheet(url: str):
    # the chat's lock is held for the whole fetch, so this doubles as the
    # longest the panel can sit frozen for everyone else
    session = await bot.session.create_session()
    async with session.get(url, allow_redirects=True,
                           timeout=aiohttp.ClientTimeout(total=SHEET_TIMEOUT)) as resp:
        if resp.status != 200:
            return None
        body = await resp.text()
    return body if "<html" not in body[:200].lower() else None


async def retire_panel(chat_id: int) -> None:
    previous = store.load(chat_id)
    if not previous or not previous.message_id:
        return

    if previous.status != "closed":
        return await replace_panel(previous, t(previous.lang, "txt_replaced"))

    try:
        # a settled panel is a record — keep it readable, just take its buttons away
        await bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=previous.message_id, reply_markup=None)
    except TelegramBadRequest:
        pass


async def replace_panel(session: Session, line: str) -> None:
    try:
        await bot.edit_message_text(
            chat_id=session.chat_id, message_id=session.message_id,
            text="<b>{}</b>".format(escape(line)), parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass


async def start_session(chat_id: int, user, args: str, reply) -> None:
    export = sheet_export_url(args or "")
    source = store.load_copy((args or "").strip().lower())
    if source:
        session = copied_session(chat_id, source)
    elif export:
        try:
            body = await fetch_sheet(export)
        except Exception as err:
            log.info("sheet fetch failed (%s)", err)
            body = None
        if body is None:
            return await reply.answer(t(lang_of(chat_id), "txt_sheet_failed"))
        rows = parse_table(body)
        if not rows:
            return await reply.answer(t(lang_of(chat_id), "txt_sheet_empty"))
        session = session_from_table(chat_id, rows)
    else:
        rows = parse_table(args or "", bare_handles=True)
        if rows and looks_like_table(args):
            session = session_from_table(chat_id, rows)
        else:
            session = fresh_session(chat_id, roster_from(args))

    await retire_panel(chat_id)

    session.editor = handle_of(user)
    store.save(session)
    await draw(session, force_new=True)
    store.save(session)


@dp.message(Command("split"))
async def on_split(message: Message, command: CommandObject):
    async with chat_lock(message.chat.id):
        await handle_split(message, command)


async def handle_split(message: Message, command: CommandObject):
    current = store.load(message.chat.id)

    if current and current.players and current.status != "closed":
        current.pending = command.args or ""
        store.save(current)
        total = compute(current)
        return await message.answer(
            t(current.lang, "txt_confirm_new", players=players_label(current),
              money=fmt_money(total.total_cost, current.currency)),
            reply_markup=markup([[(t(current.lang, "btn_yes"), "renew"),
                                  (t(current.lang, "btn_no"), "renewno")]]),
        )

    await start_session(message.chat.id, message.from_user, command.args, message)


async def repost_panel(session: Session) -> None:
    """Move the panel to the bottom of the chat: drop the old message and send
    a fresh one, so there is still exactly one panel."""
    if session.message_id:
        try:
            await bot.delete_message(session.chat_id, session.message_id)
        except TelegramBadRequest as err:
            log.info("could not remove the old panel (%s)", err)

    await draw(session, force_new=True)
    store.save(session)


@dp.message(Command("edit"))
async def on_edit(message: Message, command: CommandObject):
    async with chat_lock(message.chat.id):
        await handle_edit(message, command)


async def handle_edit(message: Message, command: CommandObject):
    session = store.load(message.chat.id)
    if not session or session.status == "closed" or not command.args:
        return

    if looks_like_table(command.args):
        changed = apply_rows(session, parse_table(command.args, bare_handles=True), editing=True)
    else:
        changed = edit_roster(session, own_roster(session, message.from_user, command.args))

    if not changed:
        return

    session.awaiting = None
    store.save(session)
    await push(session.chat_id)


@dp.message(Command("add"))
async def on_add(message: Message, command: CommandObject):
    async with chat_lock(message.chat.id):
        await handle_add(message, command)


async def handle_add(message: Message, command: CommandObject):
    session = store.load(message.chat.id)
    if not session or session.status == "closed":
        return

    if not command.args:
        session.awaiting = "newplayer"
        store.save(session)
        return await push(session.chat_id)

    if looks_like_table(command.args):
        added = apply_rows(session, parse_table(command.args, bare_handles=True), only_new=True)
    else:
        added = add_roster(session, roster_from(command.args))

    if not added:
        return

    session.awaiting = None
    store.save(session)
    await push(session.chat_id)


@dp.callback_query()
async def on_tap(query: CallbackQuery):
    if not query.message:
        return await query.answer()
    async with chat_lock(query.message.chat.id):
        await handle_tap(query)


async def handle_tap(query: CallbackQuery):
    chat_id = query.message.chat.id
    session = store.load(chat_id)
    if not session:
        return await query.answer(t(lang_of(chat_id), "txt_gone"), show_alert=True)

    data = query.data or ""
    session.awaiting = None
    session.focus.pop("retry", None)

    if session.status == "closed" and data not in ("unlock", "renew", "renewno", "export"):
        return await query.answer(t(session.lang, "txt_locked"), show_alert=True)

    if data == "unlock":
        who = query.from_user
        session.snapshot = None
        session.snapshot = json.dumps(session.to_dict(), ensure_ascii=False)
        session.settled_at = None
        session.status = "editing"
        session.editor = handle_of(who)
        session.screen = "home"
        store.save(session)
        await query.answer()
        return await push(session.chat_id)

    if data == "editno":
        if session.snapshot:
            restored = Session.from_dict(json.loads(session.snapshot))
            restored.snapshot = None
            store.save(restored)
            session = restored
        await query.answer()
        return await push(session.chat_id)

    if data in ("renew", "renewno"):
        await query.answer()
        try:
            await query.message.delete()
        except TelegramBadRequest:
            pass

        if data == "renewno":
            session.pending = None
            store.save(session)
            return

        return await start_session(session.chat_id, query.from_user,
                                   session.pending or "", query.message)

    if data == "drop":
        await query.answer()
        store.delete(chat_id)
        return await replace_panel(session, t(session.lang, "txt_dropped", date=session.date,
                                              name=handle_of(query.from_user)))

    if data == "repost":
        # bring the panel back down when chat has buried it: in a group input
        # is reply-only, so an unreachable panel is an unusable bot
        await query.answer()
        session.screen = "home"
        return await repost_panel(session)

    if data == "export":
        await query.answer()
        payload = table_csv(session).encode("utf-8-sig")
        await bot.send_document(
            session.chat_id,
            BufferedInputFile(payload, filename="session-{}.tsv".format(session.date)),
            caption=plain_title(session),
        )
        return

    if data == "post":
        incomplete = session.incomplete()
        if incomplete:
            names = ", ".join(p.handle or p.name for p in incomplete)
            return await query.answer(t(session.lang, "txt_incomplete", names=names)[:ALERT_LIMIT],
                                      show_alert=True)
        if not compute(session).slices:
            return await query.answer(t(session.lang, "txt_nothing_yet"), show_alert=True)
        who = query.from_user
        await query.answer()
        session.settled_at = datetime.now().strftime("%H:%M")
        session.snapshot = None
        session.status = "closed"
        session.editor = handle_of(who)
        session.screen = "home"
        # both land at the bottom together: the closed panel first, then the
        # settle-up under it, instead of the panel staying buried up the chat
        await repost_panel(session)
        await post_summary(session)
        store.save(session)
        return

    note = apply_tap(session, data)
    store.save(session)

    await query.answer(note or None)
    await push(session.chat_id)


ALERT_LIMIT = 200


def apply_tap(s: Session, data: str) -> Optional[str]:
    parts = data.split(":")
    head = parts[0]

    if head == "nav":
        target = parts[1]
        if target == "time":
            open_time(s, parts[2])
        elif target == "pay":
            open_pay(s, parts[2])
        elif target in ("player", "debt"):
            s.screen = target
            s.focus = {"player": parts[2]}
        else:
            s.screen = target
        return None

    if head == "askt":
        s.focus = {"player": parts[1], "span": int(parts[2]), "field": parts[3]}
        s.awaiting = "time"
        return t(s.lang, "txt_send_time")

    if head == "ask":
        s.awaiting = parts[1]
        return t(s.lang, {
            "newplayer": "txt_send_name",
            "time": "txt_send_time",
            "amount": "txt_send_amount",
            "rate": "txt_send_rate",
            "date": "txt_send_date",
            "mintransfer": "txt_send_amount",
            "rename": "txt_send_rename",
        }[parts[1]])

    if head == "player":
        return tap_player(s, parts)

    if head == "time":
        return tap_time(s, parts)

    if head == "span":
        return tap_span(s, parts)

    if head == "set":
        return tap_settings(s, parts)

    if head == "paid":
        return tap_paid(s, parts)

    if head == "debt":
        s.focus = {"player": parts[1], "creditor": parts[2]}
        s.screen = "debt"
        s.awaiting = "debt"
        return t(s.lang, "txt_send_debt")

    if head == "debtdel":
        s.debts = [d for d in s.debts if d.id != parts[1]]
        return None

    if head == "copy":
        code = copy_code(s)
        store.save_copy(code, s)
        s.screen, s.focus = "copy", {"code": code}
        return None

    return None


def open_time(s: Session, player_id: str) -> None:
    """Someone still on "-" starts from the session's span, so the nudges have
    something to move instead of an empty screen asking for a window first."""
    player = s.player(player_id)
    if player and not player.spans:
        player.add_span(*s.bounds())
    s.screen = "time"
    s.focus = {"player": player_id, "span": 0}


def open_pay(s: Session, player_id: str) -> None:
    """Same as the time screen: someone still on "-" starts from 0."""
    player = s.player(player_id)
    if player and not player.paid_set:
        s.set_paid(player_id, 0)
    s.screen = "pay"
    s.focus = {"player": player_id}


def tap_player(s: Session, parts):
    action, player_id = parts[1], parts[2]

    if action == "del":
        s.forget_player(player_id)
        s.screen = "home"

    elif action == "full":
        player = s.player(player_id)
        if player:
            player.spans = [clamp_span(*s.bounds())]

    elif action == "solo":
        player = s.player(player_id)
        if player:
            player.excluded = not player.excluded

    return None


def tap_time(s: Session, parts):
    player = s.player(parts[1])
    index = int(parts[2])
    span = player.span(index) if player else None
    if not span:
        return None

    frm, to = span
    if parts[3] == "frm":
        frm += int(parts[4])
    else:
        to += int(parts[4])

    span[0], span[1] = clamp_span(frm, to)
    s.focus = {"player": player.id, "span": player.reorder(index)}
    return None


def tap_span(s: Session, parts):
    action, player_id = parts[1], parts[2]
    player = s.player(player_id)
    if not player:
        return None

    if action == "pick":
        s.focus = {"player": player_id, "span": int(parts[3])}

    elif action == "add":
        start = player.to if player.spans else s.bounds()[0]
        s.focus = {"player": player_id,
                   "span": player.add_span(start, start + DEFAULT_LENGTH)}

    elif action == "clear":
        player.spans = []
        s.screen, s.focus = "player", {"player": player_id}

    elif action == "del" and len(player.spans) > 1:
        del player.spans[int(parts[3])]
        s.focus = {"player": player_id, "span": 0}

    return None


def tap_settings(s: Session, parts):
    key, value = parts[1], parts[2]

    if key == "date":
        # the date belongs to this session, not the group, so nothing to remember
        s.date = shift_date(s.date, int(value))
        return None

    if key == "rate":
        s.rate = max(0, s.rate + int(value))
    elif key == "min":
        s.min_transfer = max(0, transfer_minimum(s) + int(value))
    elif key == "lang" and value in LANGUAGES:
        s.lang = value
    elif key == "round":
        s.rounding = float(value)
    elif key == "blocks":
        s.blocks = value == "1"
    elif key == "cur":
        s.currency = SYMBOL_BY_CODE.get(value, s.currency)
        # an amount set in one currency means nothing in another
        s.min_transfer = None

    store.remember_settings(s)
    return None


def tap_paid(s: Session, parts):
    player_id, arg = parts[1], parts[2]
    if not s.player(player_id):
        return None

    if arg == "=0":
        s.set_paid(player_id, 0)
        return None

    if arg == "clear":
        s.clear_paid(player_id)
        s.screen, s.focus = "player", {"player": player_id}
        return None

    try:
        # a panel left over from an older version may still carry a button
        # this build no longer understands — ignore it rather than blow up
        delta = int(arg)
    except ValueError:
        return None

    # set_paid replaces the payment, so the window it covered goes back in with it
    s.set_paid(player_id, s.paid_by(player_id) + delta, *(s.paid_span(player_id) or ()))
    return None


@dp.message(F.text)
async def on_text(message: Message):
    async with chat_lock(message.chat.id):
        await handle_text(message)


async def handle_text(message: Message):
    session = store.load(message.chat.id)
    if not session:
        return

    text = (message.text or "").strip()
    if text.startswith("/") or session.status == "closed":
        return

    if not replies_to_panel(message, session):
        return

    # a table is never a valid name/time/amount, so it wins outright and the
    # paste works whether or not the panel happens to be asking for something
    if await absorb_table(session, text):
        pass
    elif not handle_awaited(session, text) and not handle_in_context(session, text):
        # keep the prompt live and say so on the panel — a silent no-op
        # leaves the sender staring at an unchanged screen
        session.focus["retry"] = True
        store.save(session)
        return await push(session.chat_id)

    session.focus.pop("retry", None)
    session.awaiting = None
    store.save(session)
    await push(session.chat_id)


async def absorb_table(session: Session, text: str) -> bool:
    export = sheet_export_url(text)
    if export:
        try:
            body = await fetch_sheet(export)
        except Exception as err:
            log.info("sheet fetch failed (%s)", err)
            return False
        text = body or ""

    rows = parse_table(text)
    if len(rows) < 2 and not ("\t" in text and rows):
        return False

    apply_rows(session, rows)
    return True


def is_name(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def handle_in_context(s: Session, text: str) -> bool:
    """Nothing was asked for, but the panel is sitting on somebody's screen — so
    read the reply as being about them. A lone time moves the start and leaves
    the end alone; a range sets both."""
    player = s.player(s.focus.get("player", ""))
    if not player or s.screen not in ("player", "time", "pay", "debt"):
        return False

    if s.screen == "debt":
        # "<кому> <сколько> [за что]" in one go, without picking a name first
        head, _, rest = text.partition(" ")
        creditor = s.find_by_name(head)
        parsed = parse_amount_note(rest) if rest else None
        if not creditor or creditor.id == player.id or not parsed:
            return False
        s.add_debt(player.id, creditor.id, parsed[0], parsed[1])
        s.screen, s.focus = "player", {"player": player.id}
        return True

    if s.screen == "pay":
        parsed = parse_paid(text)
        if parsed is None:
            return False
        s.set_paid(player.id, *parsed)
        # same as answering the prompt: the value is in, so step up to the player
        s.screen, s.focus = "player", {"player": player.id}
        return True

    index = int(s.focus.get("span", 0))
    span = player.span(index)
    if not span and player.spans:
        return False

    found = extract_span(text)
    if not found:
        return False
    frm, to = found[0], found[1]

    if span:
        span[0], span[1] = clamp_span(frm, to)
        s.focus = {"player": player.id, "span": player.reorder(index)}
    else:
        # their first window: whoever was on "-" has just filled it in
        s.focus = {"player": player.id, "span": player.add_span(frm, to)}
    return True


def handle_awaited(s: Session, text: str) -> bool:
    if s.awaiting == "newplayer":
        entry = parse_entry(text)
        if entry:
            return is_name(entry[0]) and bool(add_roster(s, [entry]))

        # same grammar as /edit, so "@маша 20:30" means the same typed or commanded
        roster = roster_from(text)
        if not any(is_name(name) for name, _, _, _, _ in roster):
            return False
        return bool(add_roster(s, roster))

    if s.awaiting == "time":
        value = parse_time(text)
        if value is None:
            return False
        player = s.player(s.focus.get("player", ""))
        index = int(s.focus.get("span", 0))
        span = player.span(index) if player else None
        if not span:
            return False

        frm, to = span
        if s.focus.get("field", "frm") == "frm":
            frm = value
        else:
            to = value + (DAY if value <= frm else 0)

        span[0], span[1] = clamp_span(frm, to)
        s.focus = {"player": player.id, "span": player.reorder(index)}
        return True

    if s.awaiting == "amount":
        parsed = parse_paid(text)
        player_id = s.focus.get("player", "")
        if parsed is None or not s.player(player_id):
            return False
        s.set_paid(player_id, *parsed)
        # the value is set, so the sub-screen has nothing left to offer —
        # step back up to the player, where the new figure is on show
        s.screen, s.focus = "player", {"player": player_id}
        return True

    if s.awaiting == "debt":
        parsed = parse_amount_note(text)
        debtor, creditor = s.focus.get("player", ""), s.focus.get("creditor", "")
        if not parsed or not s.player(debtor) or not s.player(creditor):
            return False
        amount, note = parsed
        s.add_debt(debtor, creditor, amount, note)
        s.screen, s.focus = "player", {"player": debtor}
        return True

    if s.awaiting == "rename":
        player = s.player(s.focus.get("player", ""))
        if not player or not text.strip():
            return False
        if text.startswith("@"):
            player.handle, player.name = text[:NAME_LIMIT], text.lstrip("@")[:NAME_LIMIT]
        else:
            player.handle, player.name = "", text[:NAME_LIMIT]
        return True

    if s.awaiting == "rate":
        amount = to_number(text)
        if amount is None:
            return False
        s.rate = int(amount)
        store.remember_settings(s)
        return True

    if s.awaiting == "date":
        day = parse_date(text)
        if day is None:
            return False
        s.date = day
        return True

    if s.awaiting == "mintransfer":
        amount = to_number(text)
        if amount is None:
            return False
        s.min_transfer = amount
        store.remember_settings(s)
        return True

    return False


def to_number(text: str) -> Optional[float]:
    """Strict: throwing away every character that isn't a digit turned "-5"
    into 5 and "1e9" into 19. A currency sign is the only thing tolerated."""
    cleaned = CURRENCY_RE.sub("", text or "").strip().replace(",", ".")
    if not re.match(r"^\d+(?:\.\d+)?$", cleaned):
        return None
    return round(float(cleaned), 1)


async def mark_stale(session: Session) -> None:
    if not session.posted_id:
        return
    head = session.posted_head or t(session.lang, "title_session", date=session.date)
    try:
        await bot.edit_message_text(
            chat_id=session.chat_id, message_id=session.posted_id,
            text="<b>{}</b>".format(
                t(session.lang, "txt_stale", head="<s>{}</s>".format(escape(head)))),
            parse_mode="HTML",
        )
    except TelegramBadRequest as err:
        log.info("could not mark previous result stale (%s)", err)


async def post_summary(session: Session) -> None:
    head = plain_title(session)
    await mark_stale(session)
    message = await bot.send_message(
        session.chat_id,
        "<b>{}</b>\n\n{}".format(escape(posted_title(session)), summary(session)),
        parse_mode="HTML",
    )
    session.posted_id = message.message_id
    session.posted_head = head


PROBE_EVERY = 60
PROBE_TIMEOUT = 20
PROBE_FAILURES = 3


async def watchdog() -> None:
    """Telegram outages can poison the HTTP pool: polling then hangs forever
    without the process ever exiting. Probe the same session and die so a
    supervisor can restart us."""
    failures = 0
    while True:
        await asyncio.sleep(PROBE_EVERY)
        try:
            await asyncio.wait_for(bot.get_me(), timeout=PROBE_TIMEOUT)
            failures = 0
        except Exception as err:
            failures += 1
            log.warning("watchdog probe failed (%s) — %d/%d", err, failures, PROBE_FAILURES)
            if failures >= PROBE_FAILURES:
                log.error("connection wedged — exiting so the supervisor restarts us")
                os._exit(1)


async def main():
    me = await bot.get_me()
    log.info("running as @%s", me.username)
    asyncio.create_task(watchdog())
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("stopped")
