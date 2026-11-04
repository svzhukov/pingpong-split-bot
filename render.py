import re
from html import escape
from typing import List, Optional, Tuple

from i18n import t
from model import (CURRENCIES, ROUNDING_STEPS, Session, Result, Row, Player, compute, settle,
                   fmt_time, fmt_span, fmt_spans, fmt_dur, fmt_money, plural_ru)

Button = Tuple[str, str]
Keyboard = List[List[Button]]

def e(text) -> str:
    return escape(str(text))


def wrap(s: Session, text: str) -> str:
    tag_name = "pre" if s.blocks else "code"
    return "<{0}>{1}</{0}>".format(tag_name, text)


def bold(text) -> str:
    return "<b>{}</b>".format(text)


def money(s: Session, amount) -> str:
    return fmt_money(amount, s.currency)


RTL_RE = re.compile(r"[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFF]")
LTR_MARK = "\u200e"


ZERO_WIDTH = "\u200e\u200f\u200b\u2066\u2067\u2068\u2069"


def vlen(text: str) -> int:
    return sum(1 for ch in text if ch not in ZERO_WIDTH)


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - vlen(text))


def bidi_safe(text: str) -> str:
    return text + LTR_MARK if RTL_RE.search(text or "") else text


def raw_tag(row: Row) -> str:
    return row.handle if row.handle else row.name


def tag(row: Row) -> str:
    return bidi_safe(raw_tag(row))


def cell(row: Row) -> str:
    return bidi_safe(clip(raw_tag(row)))


def nudge_label(delta: int, unit: str) -> str:
    return "{}{} {}".format("−" if delta < 0 else "＋", abs(delta), unit)


def steps(s: Session, player_id: str, index: int, size: int) -> List[Button]:
    """One row of nudges: minus/plus for the start, then the same for the end,
    so each half sits under its own header button."""
    return [(nudge_label(delta, t(s.lang, "unit_min")),
             "time:{}:{}:{}:{}".format(player_id, index, field, delta))
            for field in ("frm", "to")
            for delta in (-size, size)]


def render(session: Session) -> Tuple[str, str, Keyboard]:
    result = compute(session)
    screen = SCREENS.get(session.screen, screen_home)
    return screen(session, result)


NAME_CAP = 10
GAP = 2
TEMPLATE_ROWS = 5
PAIRED_NAME_CAP = 14


def clip(text: str, width: int = NAME_CAP) -> str:
    return text if vlen(text) <= width else text[:width - 1].rstrip() + "…"


def columns_table(headers, body) -> str:
    last = len(headers) - 1
    widths = [max([vlen(headers[i])] + [vlen(r[i]) for r in body]) + GAP for i in range(last)]
    rows = [headers] + list(body)
    return "\n".join(
        ("".join(pad(r[i], widths[i]) for i in range(last)) + r[last]).rstrip()
        for r in rows)


ROUNDING_KEYS = ("exact", "half", "whole")


def rounding_key(s: Session) -> str:
    step = float(s.rounding or 0)
    return dict(zip(ROUNDING_STEPS, ROUNDING_KEYS)).get(step, "whole")


def headers_from(s: Session, key: str):
    return [c[:1].upper() + c[1:] for c in t(s.lang, key).split("\t")]


def ordered_rows(r: Result):
    # rows come in the order players were added, and sorted() is stable,
    # so equal times keep that order
    return sorted(r.rows, key=lambda row: (not row.spans, row.frm, row.to))


def span_text(spans) -> str:
    return fmt_spans(spans) if spans else "-"


def paid_text(s: Session, paid_set: bool, amount: float) -> str:
    return money(s, amount) if paid_set else "-"


def breakdown(s: Session, r: Result) -> str:
    if not r.rows:
        return ""

    body = []
    for row in ordered_rows(r):
        paid = paid_text(s, row.paid_set, row.paid)
        if not row.spans:
            body.append([cell(row), "-", paid])
        for i, (frm, to) in enumerate(row.spans):
            body.append([cell(row) if i == 0 else "",
                         "{}-{}".format(fmt_time(frm), fmt_time(to)),
                         paid if i == 0 else ""])

    return "{}\n{}".format(bold(t(s.lang, "lbl_players")),
                           wrap(s, e(columns_table(headers_from(s, "txt_template_cols"), body))))


def sign_money(s: Session, amount: float) -> str:
    if amount > 0.005:
        return "+" + money(s, amount)
    if amount < -0.005:
        return "−" + money(s, -amount)
    return money(s, 0)


def subtotal_block(s: Session, r: Result) -> str:
    if not r.rows:
        return ""

    headers = headers_from(s, "txt_subtotal_cols")
    body = [[cell(row), money(s, row.owed), sign_money(s, row.balance)]
            for row in ordered_rows(r) if row.spans]

    return "{}\n{}".format(bold(t(s.lang, "lbl_subtotal")),
                           wrap(s, e(columns_table(headers, body))))


def debts_block(s: Session, r: Result) -> str:
    if not s.debts:
        return ""
    by_id = {row.id: tag(row) for row in r.rows}
    lines = []
    for d in s.debts:
        line = "{} → {} — {}".format(e(by_id.get(d.debtor, "?")), e(by_id.get(d.creditor, "?")),
                                     bold(money(s, d.amount)))
        if d.note:
            line += " ({})".format(e(d.note))
        lines.append(line)
    return "{}\n{}".format(bold(t(s.lang, "lbl_debts")), "\n".join(lines))


def template_block(s: Session) -> str:
    low, high = s.bounds()
    body = [["@Player1", "{}-{}".format(fmt_time(low), fmt_time(high)), money(s, 0)]] + \
           [["@Player{}".format(i), "-", "-"] for i in range(2, TEMPLATE_ROWS + 1)]
    return "{}\n<pre>{}</pre>".format(t(s.lang, "txt_template_hint"),
                                      e(columns_table(headers_from(s, "txt_template_cols"), body)))


def home_body(s: Session, r: Result) -> str:
    if not s.players:
        return template_block(s)

    if not r.slices and not s.incomplete():
        return bold(t(s.lang, "txt_nothing_yet"))

    parts = [breakdown(s, r), subtotal_block(s, r) if r.slices else "", debts_block(s, r)]
    return "\n\n".join(part for part in parts if part)


def waiting_block(s: Session) -> str:
    incomplete = s.incomplete()
    if not incomplete:
        return ""
    names = ", ".join(e(bidi_safe(p.handle or p.name)) for p in incomplete)
    return "{}\n{}".format(t(s.lang, "txt_waiting", names=names),
                           t(s.lang, "txt_waiting_hint"))


def session_title(s: Session, r: Result) -> str:
    parts = [t(s.lang, "title_session", date=s.date)]
    if r.slices:
        parts.append(fmt_dur(r.minutes, s.lang))
        parts.append(money(s, r.total_cost))
    if r.estimated:
        parts.append(t(s.lang, "txt_rate_line", rate=s.rate, cur=s.currency))
    return " · ".join(parts)


def status_title(s: Session, r: Result) -> str:
    icon, key = {
        "closed": ("🔒", "txt_status_closed"),
        "editing": ("✏️", "txt_status_editing"),
    }.get(s.status, ("🏓", "txt_status_open"))

    if s.editor:
        status = t(s.lang, key, name=s.editor)
    else:
        status = t(s.lang, key + "_plain") if key != "txt_status_editing" \
            else t(s.lang, "txt_status_open_plain")

    return "{} {} — {}".format(icon, session_title(s, r), status)


def plain_number(amount: float) -> str:
    text = "{:.1f}".format(round(amount, 1))
    return text[:-2] if text.endswith(".0") else text


def table_csv(s: Session) -> str:
    r = compute(s)
    cols = ["col_name", "col_from", "col_to", "col_paid", "col_share", "col_balance"]
    lines = ["\t".join(t(s.lang, c) for c in cols)]
    for row in ordered_rows(r):
        paid = plain_number(row.paid) if row.paid_set else "-"
        if not row.spans:
            lines.append("\t".join([row.handle or row.name, "-", "-", paid, "", ""]))
        for i, (frm, to) in enumerate(row.spans):
            lines.append("\t".join([
                row.handle or row.name,
                fmt_time(frm), fmt_time(to),
                paid if i == 0 else "",
                plain_number(row.owed) if i == 0 else "",
                plain_number(row.balance) if i == 0 else "",
            ]))
    return "\n".join(lines)


def plain_title(s: Session) -> str:
    return session_title(s, compute(s))


def posted_title(s: Session) -> str:
    return "✅ {} — {}".format(session_title(s, compute(s)), t(s.lang, "txt_settled"))


def player_body(s: Session, label: str, hint: str) -> str:
    # no session tables here: with them on screen, people took a player screen
    # for the main one and never tapped back
    if s.focus.get("retry"):
        hint = t(s.lang, "txt_retry")
    body = bold(e(label))
    if hint:
        body += "\n" + e(hint)
    return body


def player_rows(items):
    return chunk(items, 1)


def screen_home(s: Session, r: Result):
    if s.status == "closed":
        return status_title(s, r), home_body(s, r), \
            [[(t(s.lang, "btn_unlock"), "unlock"),
              (t(s.lang, "btn_export"), "export")]]

    keyboard = player_rows([("👤 " + (row.handle or row.name), "nav:player:" + row.id)
                            for row in ordered_rows(r)])
    keyboard.append([(t(s.lang, "btn_add_player"), "ask:newplayer"),
                     (t(s.lang, "btn_settings"), "nav:settings")])

    waiting = "_waiting" if s.incomplete() else ""
    if s.status == "editing" and s.snapshot:
        keyboard.append([(t(s.lang, "btn_recalc" + waiting), "post"),
                         (t(s.lang, "btn_cancel_edit"), "editno")])
    else:
        keyboard.append([(t(s.lang, "btn_settle" + waiting), "post")])

    body = "\n\n".join(part for part in [waiting_block(s), home_body(s, r)] if part)
    return status_title(s, r), body, keyboard


def focused(s: Session) -> Optional[Player]:
    return s.player(s.focus.get("player", ""))


def player_title(s: Session, p: Player) -> str:
    return t(s.lang, "title_player_edit", name=bidi_safe(p.handle or p.name))


def screen_player(s: Session, r: Result):
    p = focused(s)
    if not p:
        s.screen = "home"
        return screen_home(s, r)

    keyboard = [
        [(t(s.lang, "btn_time"), "nav:time:" + p.id),
         (t(s.lang, "btn_paid"), "nav:pay:" + p.id)],
        [(t(s.lang, "btn_solo_on" if p.excluded else "btn_solo_off"), "player:solo:" + p.id),
         (t(s.lang, "btn_debt"), "nav:debt:" + p.id)],
        [(t(s.lang, "btn_rename"), "ask:rename"),
         (t(s.lang, "btn_remove"), "player:del:" + p.id)],
        [(t(s.lang, "btn_back"), "nav:home")],
    ]

    label = t(s.lang, "title_player", name=bidi_safe(p.handle or p.name),
              span=span_text(p.spans))
    label = "{} · 💰 {}".format(label, paid_text(s, p.paid_set, s.paid_by(p.id)))
    hint = t(s.lang, "hint_player", name=bidi_safe(p.handle or p.name))
    return player_title(s, p), player_body(s, label, hint), keyboard


def screen_time(s: Session, r: Result):
    p = focused(s)
    if not p or not p.spans:
        s.screen = "home"
        return screen_home(s, r)

    index = min(max(0, int(s.focus.get("span", 0))), len(p.spans) - 1)
    frm, to = p.spans[index]

    keyboard = []
    if len(p.spans) > 1:
        keyboard = chunk([("{}{}-{}".format("🕐 " if i == index else "", fmt_time(a), fmt_time(b)),
                           "span:pick:{}:{}".format(p.id, i))
                          for i, (a, b) in enumerate(p.spans)], 2)

    keyboard += [
        [(t(s.lang, "btn_from", time=fmt_time(frm)), "askt:{}:{}:frm".format(p.id, index)),
         (t(s.lang, "btn_to", time=fmt_time(to)), "askt:{}:{}:to".format(p.id, index))],
        steps(s, p.id, index, 5),
        steps(s, p.id, index, 15),
        steps(s, p.id, index, 60),
    ]
    if len(p.spans) > 1:
        keyboard.append([(t(s.lang, "btn_span_del"), "span:del:{}:{}".format(p.id, index))])
    keyboard.append([(t(s.lang, "btn_span_add"), "span:add:" + p.id)])
    keyboard.append([(t(s.lang, "btn_clear"), "span:clear:" + p.id)])
    keyboard.append([(t(s.lang, "btn_back"), "nav:player:" + p.id)])

    label = t(s.lang, "title_time", name=bidi_safe(p.handle or p.name),
              span=fmt_spans(p.spans))
    hint = t(s.lang, "hint_time", name=bidi_safe(p.handle or p.name))
    return player_title(s, p), player_body(s, label, hint), keyboard


PAID_STEPS = (1, 5, 10)


def screen_pay(s: Session, r: Result):
    p = focused(s)
    if not p:
        s.screen = "home"
        return screen_home(s, r)

    keyboard = [[("✏ {}".format(paid_text(s, p.paid_set, s.paid_by(p.id))), "ask:amount")]]
    keyboard += [[(nudge_label(delta, s.currency), "paid:{}:{}".format(p.id, delta))
                  for delta in (-size, size)]
                 for size in PAID_STEPS]
    keyboard += [
        [(t(s.lang, "btn_clear"), "paid:{}:clear".format(p.id))],
        [(t(s.lang, "btn_back"), "nav:player:" + p.id)],
    ]

    label = t(s.lang, "title_pay", name=bidi_safe(p.handle or p.name),
              money=paid_text(s, p.paid_set, s.paid_by(p.id)))
    window = s.paid_span(p.id)
    if window:
        label = "{} · {}".format(label, fmt_span(*window))
    hint = t(s.lang, "hint_pay", name=bidi_safe(p.handle or p.name))
    return player_title(s, p), player_body(s, label, hint), keyboard


def transfer_line(s: Session, x) -> str:
    linked = [d for d in s.debts if d.debtor == x.frm.id and d.creditor == x.to.id]
    base = x.amount - sum(d.amount for d in linked)

    if not linked or base < -0.005:
        return bold(money(s, x.amount))

    parts = [bold(money(s, base))] if base > 0.005 else []
    for d in linked:
        parts.append("{} ({})".format(bold(money(s, d.amount)),
                                      e(d.note) if d.note else t(s.lang, "txt_debt_generic")))

    return " + ".join(parts)


def solo_balance(s: Session, row: Row) -> str:
    """A player settling separately is out of the transfers, so their own
    over- or underpayment is the one number the summary never shows them."""
    if row.balance > 0.005:
        return t(s.lang, "txt_solo_over", money=bold(money(s, row.balance)))
    if row.balance < -0.005:
        return t(s.lang, "txt_solo_under", money=bold(money(s, -row.balance)))
    return t(s.lang, "txt_solo_even")


def screen_debt(s: Session, r: Result):
    p = focused(s)
    if not p:
        s.screen = "home"
        return screen_home(s, r)

    others = [s.player(row.id) for row in ordered_rows(r) if row.id != p.id]
    names = [x.handle or x.name for x in others]
    # two to a row while they fit side by side, one to a row once a name is long,
    # so a name is never cut to keep the pairing
    per_row = 2 if all(vlen(n) <= PAIRED_NAME_CAP for n in names) else 1
    keyboard = chunk([("👤 " + n, "debt:{}:{}".format(p.id, x.id))
                      for x, n in zip(others, names)], per_row)

    for d in s.debts_of(p.id):
        who = s.player(d.creditor)
        keyboard.append([("🗑 {} — {}".format(who.handle or who.name if who else "?",
                                              money(s, d.amount)), "debtdel:" + d.id)])

    keyboard.append([(t(s.lang, "btn_back"), "nav:player:" + p.id)])

    label = t(s.lang, "title_debt", name=bidi_safe(p.handle or p.name))
    hint = t(s.lang, "hint_debt", name=bidi_safe(p.handle or p.name))
    return player_title(s, p), player_body(s, label, hint), keyboard


def screen_settings(s: Session, r: Result):
    check = " ✓"
    text = "{}\n{}\n\n{}\n{}\n\n{}\n{}\n\n{}\n{}\n{}".format(
        bold(t(s.lang, "lbl_language")),
        "🇷🇺 Русский" if s.lang == "ru" else "🇬🇧 English",
        bold(t(s.lang, "lbl_style")),
        "{} — {}".format(t(s.lang, "btn_style_block" if s.blocks else "btn_style_plain"),
                         t(s.lang, "txt_style_block" if s.blocks else "txt_style_plain")),
        bold(t(s.lang, "lbl_rounding")),
        "{} — {}".format(t(s.lang, "btn_round_" + rounding_key(s)),
                         t(s.lang, "txt_round_" + rounding_key(s))),
        bold(t(s.lang, "lbl_rate")),
        bold(t(s.lang, "txt_rate_line", rate=s.rate, cur=s.currency)),
        t(s.lang, "txt_tap_price"),
    )

    keyboard = [
        [(t(s.lang, "btn_help"), "nav:help")],
        [(t(s.lang, "btn_lang_ru") + (check if s.lang == "ru" else ""), "set:lang:ru"),
         (t(s.lang, "btn_currency"), "nav:currency"),
         (t(s.lang, "btn_lang_en") + (check if s.lang == "en" else ""), "set:lang:en")],
        [(("◉ " if not s.blocks else "○ ") + t(s.lang, "btn_style_plain"), "set:blocks:0"),
         (("◉ " if s.blocks else "○ ") + t(s.lang, "btn_style_block"), "set:blocks:1")],
        [(("◉ " if rounding_key(s) == key else "○ ") + t(s.lang, "btn_round_" + key),
          "set:round:{:g}".format(step))
         for step, key in zip(ROUNDING_STEPS, ROUNDING_KEYS)],
        [(nudge_label(-1, s.currency), "set:rate:-1"),
         ("✏ {}".format(t(s.lang, "txt_rate_button", rate=s.rate, cur=s.currency)), "ask:rate"),
         (nudge_label(1, s.currency), "set:rate:1")],
        [(t(s.lang, "btn_copy_session"), "copy"),
         (t(s.lang, "btn_close_session"), "nav:close")],
        [(t(s.lang, "btn_back"), "nav:home")],
    ]

    return t(s.lang, "title_settings"), text, keyboard


def players_label(s: Session) -> str:
    n = len(s.players)
    return t(s.lang, "txt_players_count", n=n,
             word=plural_ru(n, "игрок", "игрока", "игроков"))


def screen_copy(s: Session, r: Result):
    code = s.focus.get("code")
    if not code:
        s.screen = "settings"
        return screen_settings(s, r)

    text = "{}\n\n<code>/split {}</code>\n\n{}".format(
        t(s.lang, "txt_copy_send"), e(code), t(s.lang, "txt_copy_tap"))
    return t(s.lang, "title_copy"), text, [[(t(s.lang, "btn_back"), "nav:settings")]]


def screen_close(s: Session, r: Result):
    text = t(s.lang, "txt_close_confirm", players=players_label(s),
             money=money(s, r.total_cost))
    return t(s.lang, "title_close"), text, \
        [[(t(s.lang, "btn_close_yes"), "drop"), (t(s.lang, "btn_no"), "nav:settings")]]


def screen_help(s: Session, r: Result):
    body = t(s.lang, "help").split("\n\n", 1)[1]
    return t(s.lang, "title_help"), body, \
        [[(t(s.lang, "btn_back"), "nav:settings")]]


def screen_currency(s: Session, r: Result):
    check = " ✓"
    rows = chunk([("{} {}{}".format(sym, code, check if s.currency == sym else ""),
                   "set:cur:" + code) for code, sym in CURRENCIES], 3)
    rows.append([(t(s.lang, "btn_back"), "nav:settings")])

    text = bold(t(s.lang, "txt_rate_line", rate=s.rate, cur=s.currency))
    return t(s.lang, "title_currency"), text, rows


def summary(s: Session) -> str:
    r = compute(s)

    if r.estimated:
        # nobody put money in, so there is nothing to move between people —
        # the useful answer is what each of them owes
        return owed_summary(s, r)

    transfers = settle(r.rows)

    if transfers:
        moves = "\n".join(
            "• {} → {} — {}".format(e(tag(x.frm)), e(tag(x.to)), transfer_line(s, x))
            for x in transfers
        )
    else:
        moves = t(s.lang, "txt_all_square")

    sections = [x for x in [debts_block(s, r)] if x]
    sections += ["{}\n{}".format(bold(t(s.lang, "lbl_settle")), moves)]

    solo = [row for row in r.rows if row.excluded]
    if solo:
        sections.append(t(s.lang, "txt_solo_note",
                          names=", ".join("{} ({})".format(e(tag(x)), solo_balance(s, x))
                                          for x in solo)))

    return "\n\n".join(sections)


def owed_summary(s: Session, r: Result) -> str:
    lines = "\n".join("• {} — {}".format(e(tag(row)), bold(money(s, row.owed)))
                      for row in ordered_rows(r))

    sections = [x for x in [debts_block(s, r)] if x]
    sections.append("{}\n{}".format(bold(t(s.lang, "lbl_owed")), lines))
    sections.append(t(s.lang, "txt_own_share"))
    return "\n\n".join(sections)


def chunk(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


SCREENS = {
    "home": screen_home,
    "player": screen_player,
    "time": screen_time,
    "pay": screen_pay,
    "debt": screen_debt,
    "settings": screen_settings,
    "currency": screen_currency,
    "help": screen_help,
    "close": screen_close,
    "copy": screen_copy,
}
