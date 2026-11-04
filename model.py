import hashlib
import itertools
import json
import math
import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

DAY = 24 * 60
DEFAULT_RATE = 16
DEFAULT_CURRENCY = "₾"

# Only the table columns clip a name; everywhere else it is shown whole,
# so this is a sanity bound rather than a display width.
NAME_LIMIT = 64


def new_id() -> str:
    return uuid.uuid4().hex[:6]


# no 0/o, 1/l/i — a code read off a screen and retyped can't be misread
COPY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
COPY_LENGTH = 10
# what a copy carries: everything that decides the numbers, nothing about the
# chat it was made in
COPIED_FIELDS = ("date", "rate", "currency", "rounding", "players", "payments", "debts")


def copy_code(session: "Session") -> str:
    """Worked out from what the copy carries, so an unchanged session hands out
    the same code however often it's copied, and a changed one a new code."""
    raw = session.to_dict()
    content = {name: raw[name] for name in COPIED_FIELDS}
    # money typed in again gets a fresh random id, lands at the end of its list
    # and may come back as 30.0 where it was 30 — none of which is a change
    for name in ("payments", "debts"):
        content[name] = sorted(
            (dict(item, id=None, amount=float(item["amount"])) for item in content[name]),
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    text = json.dumps(content, sort_keys=True, ensure_ascii=False)
    number = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest(), "big")
    code = ""
    for _ in range(COPY_LENGTH):
        number, index = divmod(number, len(COPY_ALPHABET))
        code += COPY_ALPHABET[index]
    return code


def fmt_time(minutes: int) -> str:
    m = minutes % DAY
    return "{:02d}:{:02d}".format(m // 60, m % 60)


def fmt_span(frm: int, to: int) -> str:
    return "{} - {}".format(fmt_time(frm), fmt_time(to))


def fmt_spans(spans, sep: str = ", ") -> str:
    return sep.join(fmt_span(f, t) for f, t in spans)


MAX_SPAN = 12 * 60


def clamp_span(frm: int, to: int) -> List[int]:
    """One window never runs backwards and never outlives a night. Both the
    buttons and typed times go through here, so they can't disagree."""
    frm = min(max(0, frm), DAY - 1)
    return [frm, min(max(to, frm), frm + MAX_SPAN)]


def fmt_dur(minutes: int, lang: str = "ru") -> str:
    minutes = max(0, int(round(minutes)))
    h, m = divmod(minutes, 60)
    hour, minute = ("ч", "м") if lang == "ru" else ("h", "m")
    if not h:
        return "{}{}".format(m, minute)
    return "{}{} {}{}".format(h, hour, m, minute) if m else "{}{}".format(h, hour)


def plural_ru(count: int, one: str, few: str, many: str) -> str:
    if 11 <= count % 100 <= 14:
        return many
    last = count % 10
    if last == 1:
        return one
    if 2 <= last <= 4:
        return few
    return many


CURRENCIES = [("GEL", "₾"), ("RUB", "₽"), ("AMD", "֏"), ("AZN", "₼"),
              ("UAH", "₴"), ("TRY", "₺"), ("USD", "$"), ("EUR", "€")]
SYMBOL_BY_CODE = dict(CURRENCIES)
# a step that suits ₾ is lost in ₽ or ֏, so money buttons scale by currency
STEP_SCALE = {"₽": 10, "₴": 10, "₺": 10, "֏": 100}


def money_step(currency: str, step: int) -> int:
    return step * STEP_SCALE.get(currency, 1)
PREFIXED = {"$", "€"}
NBSP = "\u00a0"


def fmt_money(amount: float, currency: str = DEFAULT_CURRENCY) -> str:
    value = "{:.1f}".format(round(amount, 1))
    if value.endswith(".0"):
        value = value[:-2]
    if value == "-0":
        value = "0"
    if currency in PREFIXED:
        return currency + value
    return value + NBSP + currency


TIME_RE = re.compile(r"^(\d{1,2})(?:[:.\s]?(\d{2}))?$")

_T = r"\d{1,2}(?:[:.]?\d{2})?"

# only the dash form: a second bare number now means money, so "20 22" and
# "с 20 до 22" would both be ambiguous
SPAN_PATTERNS = [
    re.compile(r"(?<![\d:.])(" + _T + r")\s*[-–—]\s*(" + _T + r")(?![\d:.])"),
]

SINGLE_BARE = re.compile(r"(?<![\d:.])(" + _T + r")(?![\d:.])")

DEFAULT_LENGTH = 60


def extract_span(text: str, allow_bare: bool = False):
    for pattern in SPAN_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        frm, to = parse_time(m.group(1)), parse_time(m.group(2))
        if frm is None or to is None:
            continue
        if to <= frm:
            to += DAY
        return frm, to, text[:m.start()].strip(), text[m.end():].strip()

    for pattern in ([SINGLE_BARE] if allow_bare else []):
        m = pattern.search(text)
        if not m:
            continue
        frm = parse_time(m.group(1))
        if frm is None:
            continue
        return frm, frm + DEFAULT_LENGTH, text[:m.start()].strip(), text[m.end():].strip()

    return None


def parse_time(text: str) -> Optional[int]:
    m = TIME_RE.match(text.strip())
    if not m:
        return None
    hours = int(m.group(1))
    mins = int(m.group(2) or 0)
    if hours > 23 or mins > 59:
        return None
    return hours * 60 + mins


AMOUNT_NOTE_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)(?:\s+(.*))?\s*$", re.S)


def parse_amount_note(text: str):
    m = AMOUNT_NOTE_RE.match(text)
    if not m:
        return None
    try:
        amount = round(float(m.group(1).replace(",", ".")), 1)
    except ValueError:
        return None
    if amount <= 0:
        return None
    return amount, " ".join((m.group(2) or "").split())[:24]


TIME_CELL = r"\d{1,2}(?:[:.]?\d{2})?"
# the last column is whatever the sheet put there — a number, or the "-"
# this bot itself prints for nobody-paid. Anything without digits reads as none.
ROW_RE = re.compile(
    r"^(.+?)[ ]+(" + TIME_CELL + r")(?:[ ]*[-\u2013\u2014][ ]*|[ ]+)(" + TIME_CELL + r")"
    r"(?:[ ]+(\S+))?[ ]*$")
BLANK_ROW_RE = re.compile(r"^(.+?)[ ]+[-\u2013\u2014](?:[ ]+(.*))?$")


CURRENCY_RE = re.compile(r"[₾₽֏₼₴₺$€₸]")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _amount(text: str):
    m = re.search(r"(-?)(\d+(?:[.,]\d+)?)", text or "")
    if not m or m.group(1):
        return None        # "-35" is not 35
    return round(float(m.group(2).replace(",", ".")), 1)


PAID_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(.*)$", re.S)


def parse_paid(text: str):
    """-> (amount, frm, to) or None. "12.5" is a plain contribution; adding a
    span — "12.5 21:30-22:15" — says which stretch of court it paid for."""
    m = PAID_RE.match(CURRENCY_RE.sub("", text or "").strip())
    if not m:
        return None
    amount = round(float(m.group(1).replace(",", ".")), 1)

    rest = m.group(2).strip()
    if not rest:
        return amount, None, None

    found = extract_span(rest)
    if not found:
        return None        # trailing junk: reject rather than quietly drop it
    return amount, found[0], found[1]


SHEET_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)")
GID_RE = re.compile(r"[#&?]gid=(\d+)")


def sheet_export_url(text: str):
    m = SHEET_RE.search(text or "")
    if not m:
        return None
    gid = GID_RE.search(text)
    return "https://docs.google.com/spreadsheets/d/{}/export?format=tsv&gid={}".format(
        m.group(1), gid.group(1) if gid else "0")


AMOUNT_TOKEN_RE = re.compile(r"^\d+(?:[.,]\d+)?$")
TOKEN_PUNCT = ".,;!?()[]\"'«»"


def token_amount(token: str) -> Optional[float]:
    """A word that reads as money once punctuation is off it — "26," is 26."""
    word = token.strip(TOKEN_PUNCT)
    if not AMOUNT_TOKEN_RE.match(word):
        return None
    return round(float(word.replace(",", ".")), 1)


def drop_numbers(name: str) -> str:
    """A bare number is never part of a name: money goes after the time, and
    typed ahead of it is ignored. A name of nothing but numbers is left as is."""
    words = [w for w in name.split() if token_amount(w) is None]
    return " ".join(words) if any(c.isalpha() for c in "".join(words)) else name


def clean_name(text: str) -> str:
    """The panel clips long names, so a table copied out of it comes back with
    a trailing ellipsis — that is decoration, not part of anybody's name."""
    return drop_numbers((text or "").strip().rstrip("\u2026.").strip())


SPAN_CELL_RE = re.compile(r"^(" + TIME_CELL + r")[ ]*[-\u2013\u2014][ ]*(" + TIME_CELL + r")$")


DASHES = ("-", "\u2013", "\u2014")
BLANK = "-"     # a "-" where the money goes: left for the player to fill in


def paid_cell(text: str):
    """A money cell -> an amount, BLANK for a "-", None when it says nothing."""
    return BLANK if text.strip() in DASHES else _amount(text)


def parse_cells(cells):
    expanded = []
    for cell in cells:
        m = SPAN_CELL_RE.match(cell.strip())
        expanded.extend([m.group(1), m.group(2)] if m else [cell])
    cells = [c.strip() for c in expanded]
    for i in range(1, len(cells) - 1):
        frm, to = parse_time(cells[i]), parse_time(cells[i + 1])
        if frm is None or to is None:
            continue
        name = clean_name(" ".join(c for c in cells[:i] if c))
        if name and not any(c.isalpha() for c in name):
            return None
        amount = next((paid_cell(c) for c in cells[i + 2:] if c), None)
        return name, frm, to + (DAY if to <= frm else 0), amount

    # a dash where the time goes: the player is in, their time comes later
    for i in range(1, len(cells)):
        if cells[i] not in DASHES:
            continue
        name = clean_name(" ".join(c for c in cells[:i] if c))
        if not any(c.isalpha() for c in name):
            return None
        amount = next((_amount(c) for c in cells[i + 1:] if c and c not in DASHES), None)
        return name, None, None, amount
    return None


def parse_table(text: str):
    rows = []
    for raw in text.splitlines():
        line = CURRENCY_RE.sub("", raw.replace("\u00a0", " ")).rstrip()
        if not line.strip():
            continue

        if "|" in line:
            parsed = parse_cells(line.split("|"))
            if parsed:
                rows.append(parsed)
            continue

        if "\t" in line:
            parsed = parse_cells(line.split("\t"))
            if parsed:
                rows.append(parsed)
            continue

        m = ROW_RE.match(line)
        if not m:
            blank = BLANK_ROW_RE.match(line)
            if blank:
                parsed = parse_cells([blank.group(1), "-"] + (blank.group(2) or "").split())
                if parsed:
                    rows.append(parsed)
            continue
        frm, to = parse_time(m.group(2)), parse_time(m.group(3))
        if frm is None or to is None:
            continue
        rows.append((clean_name(m.group(1)), frm, to + (DAY if to <= frm else 0),
                     paid_cell(m.group(4)) if m.group(4) else None))
    return rows


SPAN_TOKEN_RE = re.compile(r"^(" + TIME_CELL + r")-(" + TIME_CELL + r")$")


def normalize_spans(text: str) -> str:
    """Collapse "20 - 22" to "20-22" so the span survives tokenising."""
    return re.sub(r"(" + TIME_CELL + r")\s*[-\u2013\u2014]\s*(" + TIME_CELL + r")",
                  r"\1-\2", text)


def parse_roster(args: str):
    """-> [(name, handle, frm, to, paid)]

    Same column order as a pasted row: name, time, money. A time is always a
    start and an end ("20-22") and belongs only to the name before it; a bare
    number is money. No time, or a "-" in place of either, leaves it for the
    player to fill in later — paid comes back as BLANK for a "-" and None when
    unstated. A time ahead of every name belongs to nobody."""
    people, blank = [], set()

    for token in normalize_spans(args or "").split():
        m = SPAN_TOKEN_RE.match(token.strip(TOKEN_PUNCT))
        if m:
            frm, to = parse_time(m.group(1)), parse_time(m.group(2))
            if frm is None or to is None:
                continue
            if to <= frm:
                to += DAY
            # name, time, money in that order: money typed ahead of the time is
            # out of place and dropped; a span after their "-", or a span they
            # already gave, is ignored
            if people and people[-1][2] is None and len(people) - 1 not in blank:
                people[-1] = people[-1][:2] + (frm, to, None)
            continue

        if token.strip(TOKEN_PUNCT) in DASHES:
            if people and people[-1][2] is None and len(people) - 1 not in blank:
                blank.add(len(people) - 1)
            elif people and people[-1][4] is None:
                people[-1] = people[-1][:4] + (BLANK,)
            continue

        # @handles are never numbers, so they are exempt from both branches
        if not token.startswith("@"):
            amount = token_amount(token)
            if people and people[-1][4] is None and amount is not None:
                people[-1] = people[-1][:4] + (amount,)
                continue

            if ":" in token:
                continue        # a lone clock time is half a span — not enough

        clean = token.strip(".,;:!?()[]\"'«»")
        if not clean or clean.startswith("/") or not any(c.isalpha() for c in clean):
            continue        # "35", "-5", "₾40" are stray numbers, not people
        people.append((clean.lstrip("@")[:NAME_LIMIT],
                       clean if clean.startswith("@") else "", None, None, None))

    return people


def parse_entry(text: str):
    """One player typed out in full -> (name, handle, frm, to, paid), or None
    without a time. Name, time, money, as everywhere else: the name may run to
    several words, and only a number right after the time is money."""
    found = extract_span(text.strip())
    if not found:
        return None
    frm, to, before, after = found
    head = after.split()[0].strip(TOKEN_PUNCT) if after else ""
    paid = BLANK if head in DASHES else token_amount(head)
    name = clean_name("{} {}".format(before, after).strip(" ,;:-–—"))
    if not name:
        return None
    if name.startswith("@") and " " not in name:
        return name.lstrip("@"), name, frm, to, paid
    return name, "", frm, to, paid


@dataclass
class Player:
    id: str
    name: str
    spans: List[List[int]] = field(default_factory=list)
    handle: str = ""
    excluded: bool = False
    paid_set: bool = False     # 0 is an answer; until then the cell reads "-"

    @property
    def frm(self) -> int:
        return min((s[0] for s in self.spans), default=0)

    @property
    def to(self) -> int:
        return max((s[1] for s in self.spans), default=0)

    def span(self, index: int) -> Optional[List[int]]:
        return self.spans[index] if 0 <= index < len(self.spans) else None

    def add_span(self, frm: int, to: int) -> int:
        self.spans.append(clamp_span(frm, to))
        return self.reorder(len(self.spans) - 1)

    def reorder(self, index: int) -> int:
        """Keep the windows in clock order after any edit, and report where the
        one being edited ended up so the screen stays on it."""
        edited = self.span(index)
        self.spans.sort(key=lambda s: (s[0], s[1]))
        return next((i for i, s in enumerate(self.spans) if s is edited), 0)

    @classmethod
    def from_raw(cls, raw: dict) -> "Player":
        spans = [list(s) for s in raw.get("spans") or []]
        if not spans and raw.get("to") is not None:
            spans = [[raw["frm"], raw["to"]]]
        # sessions saved before "-" existed read an empty contribution as 0
        return cls(id=raw["id"], name=raw["name"], spans=spans,
                   handle=raw.get("handle", ""), excluded=raw.get("excluded", False),
                   paid_set=raw.get("paid_set", True))


@dataclass
class Payment:
    id: str
    player_id: str
    amount: float
    frm: Optional[int] = None      # the window this money bought;
    to: Optional[int] = None       # None/None means the whole session


@dataclass
class Debt:
    id: str
    debtor: str
    creditor: str
    amount: float
    note: str = ""


@dataclass
class Slice:
    frm: int
    to: int
    present: List[Player]
    cost: float


@dataclass
class Row:
    id: str
    name: str
    handle: str
    spans: List[List[int]]
    owed: float
    paid: float
    excluded: bool = False
    paid_set: bool = True
    adjustment: float = 0.0
    extra: float = 0.0

    @property
    def frm(self) -> int:
        return min((s[0] for s in self.spans), default=0)

    @property
    def to(self) -> int:
        return max((s[1] for s in self.spans), default=0)

    @property
    def balance(self) -> float:
        return self.paid - self.owed + self.extra

    @property
    def settle_balance(self) -> float:
        return self.balance + self.adjustment


@dataclass
class Transfer:
    frm: Row
    to: Row
    amount: float


@dataclass
class Session:
    chat_id: int
    date: str
    rate: int = DEFAULT_RATE
    currency: str = DEFAULT_CURRENCY
    lang: str = "ru"
    rounding: float = 1.0
    blocks: bool = False
    settled_at: Optional[str] = None
    status: str = "open"
    editor: Optional[str] = None
    posted_id: Optional[int] = None
    posted_head: Optional[str] = None
    pending: Optional[str] = None
    snapshot: Optional[str] = None
    message_id: Optional[int] = None
    players: List[Player] = field(default_factory=list)
    payments: List[Payment] = field(default_factory=list)
    debts: List[Debt] = field(default_factory=list)
    screen: str = "home"
    focus: Dict[str, Any] = field(default_factory=dict)
    awaiting: Optional[str] = None

    def player(self, player_id: str) -> Optional[Player]:
        return next((p for p in self.players if p.id == player_id), None)

    def payment(self, payment_id: str) -> Optional[Payment]:
        return next((y for y in self.payments if y.id == payment_id), None)

    def add_debt(self, debtor: str, creditor: str, amount: float, note: str = "") -> None:
        for opposite in [d for d in self.debts if d.debtor == creditor and d.creditor == debtor]:
            if amount <= 0.005:
                break
            settled = min(amount, opposite.amount)
            opposite.amount = round(opposite.amount - settled, 1)
            amount = round(amount - settled, 1)

        self.debts = [d for d in self.debts if d.amount > 0.005]
        if amount > 0.005:
            self.debts.append(Debt(id=new_id(), debtor=debtor, creditor=creditor,
                                   amount=round(amount, 1), note=note))

    def net_debts(self) -> None:
        known = {p.id for p in self.players}
        pending = [d for d in self.debts if d.debtor in known and d.creditor in known]
        self.debts = []
        for d in pending:
            self.add_debt(d.debtor, d.creditor, d.amount, d.note)

    def forget_player(self, player_id: str) -> None:
        """Debts and payments die with the player — a debt pointing at someone
        who is gone is money the settlement can never hand to anyone."""
        self.players = [p for p in self.players if p.id != player_id]
        self.payments = [y for y in self.payments if y.player_id != player_id]
        self.debts = [d for d in self.debts
                      if d.debtor != player_id and d.creditor != player_id]

    def debts_of(self, player_id: str) -> List["Debt"]:
        return [d for d in self.debts if d.debtor == player_id]

    def paid_by(self, player_id: str) -> float:
        return sum(y.amount for y in self.payments if y.player_id == player_id)

    def set_paid(self, player_id: str, amount: float,
                 frm: Optional[int] = None, to: Optional[int] = None) -> None:
        amount = max(0.0, round(amount, 1))
        player = self.player(player_id)
        if player:
            player.paid_set = True
        self.payments = [y for y in self.payments if y.player_id != player_id]
        if amount > 0:
            self.payments.append(Payment(id=new_id(), player_id=player_id,
                                         amount=amount, frm=frm, to=to))

    def clear_paid(self, player_id: str) -> None:
        player = self.player(player_id)
        if player:
            player.paid_set = False
        self.payments = [y for y in self.payments if y.player_id != player_id]

    def paid_span(self, player_id: str):
        y = next((y for y in self.payments
                  if y.player_id == player_id and y.frm is not None), None)
        return (y.frm, y.to) if y else None

    def find_by_name(self, name: str) -> Optional[Player]:
        needle = name.strip().lower().lstrip("@")
        for p in self.players:
            if p.name.lower().lstrip("@") == needle or p.handle.lower().lstrip("@") == needle:
                return p
        return None

    def untimed(self) -> List[Player]:
        return [p for p in self.players if not p.spans]

    def unpaid(self) -> List[Player]:
        return [p for p in self.players if not p.paid_set]

    def incomplete(self) -> List[Player]:
        return [p for p in self.players if not p.spans or not p.paid_set]

    def bounds(self):
        timed = [p for p in self.players if p.spans]
        if not timed:
            return 19 * 60, 21 * 60
        return min(p.frm for p in timed), max(p.to for p in timed)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "Session":
        session = cls(
            chat_id=raw["chat_id"],
            date=raw["date"],
            rate=raw.get("rate", DEFAULT_RATE),
            currency=raw.get("currency", DEFAULT_CURRENCY),
            lang=raw.get("lang", "ru"),
            rounding=float(raw.get("rounding", 1) or 0),
            blocks=raw.get("blocks", False),
            settled_at=raw.get("settled_at"),
            status=raw.get("status") or ("closed" if raw.get("settled_at") else "open"),
            editor=raw.get("editor"),
            posted_id=raw.get("posted_id"),
            posted_head=raw.get("posted_head"),
            pending=raw.get("pending"),
            snapshot=raw.get("snapshot"),
            message_id=raw.get("message_id"),
            players=[Player.from_raw(p) for p in raw.get("players", [])],
            payments=[Payment(**y) for y in raw.get("payments", [])],
            debts=[Debt(**d) for d in raw.get("debts", [])],
            screen=raw.get("screen", "home"),
            focus=raw.get("focus", {}),
            awaiting=raw.get("awaiting"),
        )
        session.net_debts()
        return session


ROUNDING_STEPS = (0.0, 0.5, 1.0)


def spread(total: float, count: int, step: float) -> List[float]:
    """Hand out `total` across `count` people in whole multiples of `step`,
    so the pieces still add back up to it. step 0 means don't round at all."""
    if count <= 0:
        return []
    if not step:
        return [total / count] * count

    sign = 1 if total >= 0 else -1
    base, remainder = divmod(int(round(abs(total) / step)), count)
    return [sign * (base + (1 if i < remainder else 0)) * step for i in range(count)]


def apportion(values: Dict[str, float], target: float, step: float = 1.0) -> Dict[str, float]:
    """Largest-remainder apportionment in units of `step`: every share lands on
    a multiple of it and the shares still sum to exactly `target`."""
    units = {key: value / step for key, value in values.items()}
    floors = {key: math.floor(value) for key, value in units.items()}
    remainder = int(round(target / step)) - sum(floors.values())
    order = sorted(units, key=lambda key: (-(units[key] - floors[key]), key))

    result = dict(floors)
    for key in order[:max(0, remainder)]:
        result[key] += 1

    return {key: value * step for key, value in result.items()}


@dataclass
class Result:
    slices: List[Slice]
    rows: List[Row]
    minutes: int
    total_cost: float
    total_paid: float
    estimate: float
    estimated: bool


def within(slices, frm, to):
    return [i for i, s in enumerate(slices) if s.frm >= frm and s.to <= to]


def share_out(payments, slices, players):
    """Each payment is spread only across the slices it bought, and within a
    slice split equally between whoever was on court. Money with no window
    covers whatever no windowed payment claimed — so you only have to mark the
    odd one out, and the rest still adds up."""
    owed = {p.id: 0.0 for p in players}
    buckets, claimed = {}, set()

    for y in payments:
        buckets[(y.frm, y.to)] = buckets.get((y.frm, y.to), 0.0) + y.amount
        if y.frm is not None:
            claimed.update(within(slices, y.frm, y.to))

    for (frm, to), amount in buckets.items():
        if frm is None:
            covered = [i for i in range(len(slices)) if i not in claimed] or list(range(len(slices)))
        else:
            covered = within(slices, frm, to) or list(range(len(slices)))

        width = float(sum(slices[i].to - slices[i].frm for i in covered))
        if width <= 0:
            continue
        for i in covered:
            s = slices[i]
            part = amount * (s.to - s.frm) / width
            for p in s.present:
                owed[p.id] += part / len(s.present)

    return owed


def compute(session: Session) -> Result:
    points = set()
    for p in session.players:
        for a, b in p.spans:
            points.update((a, b))

    ordered = sorted(points)
    slices: List[Slice] = []

    for a, b in zip(ordered, ordered[1:]):
        if b <= a:
            continue
        present = [p for p in session.players
                   if any(f <= a and t >= b for f, t in p.spans)]
        if not present:
            continue
        slices.append(Slice(frm=a, to=b, present=present, cost=session.rate * (b - a) / 60))

    paid = {p.id: 0.0 for p in session.players}
    for y in session.payments:
        if y.player_id in paid:
            paid[y.player_id] += y.amount

    expected = {p.id: 0.0 for p in session.players}
    for s in slices:
        each = s.cost / len(s.present)
        for p in s.present:
            expected[p.id] += each

    estimate = sum(s.cost for s in slices)
    total_paid = sum(y.amount for y in session.payments)
    estimated = total_paid <= 0.005

    if estimated:
        factor = 1.0 if estimate > 0 else 0.0
        owed = {key: value * factor for key, value in expected.items()}
    else:
        owed = share_out(session.payments, slices, session.players)

    total_cost = estimate if estimated else total_paid

    step = float(session.rounding or 0)
    if step and owed and total_cost > 0:
        total_cost = round(total_cost / step) * step
        owed = apportion(owed, total_cost, step)

    extra = {p.id: 0.0 for p in session.players}
    for d in session.debts:
        if d.debtor in extra:
            extra[d.debtor] -= d.amount
        if d.creditor in extra:
            extra[d.creditor] += d.amount

    rows = [
        Row(id=p.id, name=p.name, handle=p.handle, spans=[list(x) for x in p.spans],
            owed=owed[p.id], paid=paid[p.id],
            excluded=p.excluded, paid_set=p.paid_set, extra=extra[p.id])
        for p in session.players
    ]

    included = [row for row in rows if not row.excluded]
    carried = sum(row.balance for row in rows if row.excluded)

    if included and abs(carried) > 0.005:
        for row, share in zip(included, spread(carried, len(included), step)):
            row.adjustment = share

    if included:
        # Rounding to whole amounts, and spreading an excluded player's balance,
        # both leave a sub-unit residue. Park it on the biggest balance so the
        # transfers cancel exactly instead of leaving someone short.
        residual = sum(row.settle_balance for row in included)
        if abs(residual) > 0.005:
            max(included, key=lambda row: abs(row.settle_balance)).adjustment -= residual

    return Result(
        slices=slices,
        rows=rows,
        minutes=sum(s.to - s.frm for s in slices),
        total_cost=total_cost,
        total_paid=total_paid,
        estimate=estimate,
        estimated=estimated,
    )


# every ordering of payers × receivers is tried, and settle runs on each panel
# redraw on a slow one-core VM; past this many combinations (4 payers × 4
# receivers is 576, 5 × 3 is 720, 5 × 4 is 2 880) the largest-first ordering
# alone is used
SETTLE_SEARCH_LIMIT = 800


def staircase(owing, due) -> List[Transfer]:
    """Walk both lists in the given order, each payer filling receivers until
    their debt runs out. At most payers + receivers − 1 transfers, fewer when
    a group of payers exactly covers a group of receivers."""
    owing = [[r, amount] for r, amount in owing]
    due = [[r, amount] for r, amount in due]
    transfers: List[Transfer] = []
    i = j = 0

    while i < len(owing) and j < len(due):
        amount = min(owing[i][1], due[j][1])
        if amount > 0.005:
            transfers.append(Transfer(frm=owing[i][0], to=due[j][0], amount=amount))
        owing[i][1] -= amount
        due[j][1] -= amount
        if owing[i][1] <= 0.005:
            i += 1
        if due[j][1] <= 0.005:
            j += 1

    return transfers


def plan_score(transfers: List[Transfer]):
    """Fewest transfers first; among those, nobody should be stuck sending
    most of them — then the same evenness on the receiving side."""
    sent: Dict[str, int] = {}
    got: Dict[str, int] = {}
    for x in transfers:
        sent[x.frm.id] = sent.get(x.frm.id, 0) + 1
        got[x.to.id] = got.get(x.to.id, 0) + 1
    return (len(transfers),
            max(sent.values(), default=0), sum(n * n for n in sent.values()),
            max(got.values(), default=0), sum(n * n for n in got.values()))


def settle(rows: List[Row]) -> List[Transfer]:
    rows = [r for r in rows if not r.excluded]
    owing = sorted([(r, -r.settle_balance) for r in rows if r.settle_balance < -0.005],
                   key=lambda x: -x[1])
    due = sorted([(r, r.settle_balance) for r in rows if r.settle_balance > 0.005],
                 key=lambda x: -x[1])

    best = staircase(owing, due)
    if math.factorial(len(owing)) * math.factorial(len(due)) > SETTLE_SEARCH_LIMIT:
        return best

    best_score = plan_score(best)
    for payers in itertools.permutations(owing):
        for receivers in itertools.permutations(due):
            plan = staircase(payers, receivers)
            score = plan_score(plan)
            if score < best_score:
                best, best_score = plan, score
    return best
