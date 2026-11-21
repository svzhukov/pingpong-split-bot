import json
import logging
import os
import pathlib
import re
from datetime import datetime
from typing import List, Optional, Tuple

HERE = pathlib.Path(__file__).resolve().parent
PROMPT = (HERE / "chat_prompt.md").read_text(encoding="utf-8")
SCHEMA = json.loads((HERE / "chat_schema.json").read_text(encoding="utf-8"))

MODEL = "claude-haiku-5-5"
MAX_TOKENS = 8000
# about 4k tokens of chat: a long evening's reports fit, a pasted novel doesn't
MAX_CHARS = 12000
TIMEOUT = 60.0

# "Миша, [17 Nov 2026 at 22:49:50]:", "Миша, [20 ноя. 2026 в 21:24]" — a name,
# then brackets holding a clock time
HEADER_RE = re.compile(r"^\s*[^\n\[\]]{1,80}, \[[^\]\n]*\d{1,2}:\d{2}[^\]\n]*\]:?\s*$", re.M)

log = logging.getLogger("pingpong")

_client = None


class ChatTooLong(Exception):
    pass


class ChatUnreadable(Exception):
    pass


def enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def looks_like_chat(text: str) -> bool:
    return bool(HEADER_RE.search(text or ""))


COMMENT_LIMIT = 500
COMMENT_TAG = "sender_comment"


def transcript(entries: List[Tuple[datetime, str, str]], comment: Optional[str] = None) -> str:
    """Forwarded messages as the text a copied chat would be: one header per
    message, in the order they were sent. Times stay in UTC and say so. A
    comment typed with the forward goes first, in its own marked block, which
    the prompt reads as facts about the session and never as instructions."""
    blocks = []
    if comment and comment.strip():
        cleaned = comment.replace("<" + COMMENT_TAG, "").replace("</" + COMMENT_TAG, "").strip()
        blocks.append("<{0}>\n{1}\n</{0}>".format(COMMENT_TAG, cleaned[:COMMENT_LIMIT]))
    for sent, sender, text in sorted(entries, key=lambda entry: entry[0]):
        blocks.append("{}, [{} UTC]:\n{}".format(sender, sent.strftime("%d %b %Y at %H:%M:%S"), text.strip()))
    return "\n\n".join(blocks)


COMMENT_RE = re.compile(r"<{0}>\n(.*?)\n</{0}>".format(COMMENT_TAG), re.S)


def comment_of(chat: str) -> Optional[str]:
    found = COMMENT_RE.search(chat or "")
    return found.group(1).strip() if found else None


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.AsyncAnthropic(timeout=TIMEOUT)
    return _client


async def read_chat(chat: str) -> dict:
    """-> {"date", "rate", "players": [{"name", "windows", "paid", "settles_separately", "note"}]}"""
    if len(chat) > MAX_CHARS:
        raise ChatTooLong()

    response = await client().messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=PROMPT,
        messages=[{"role": "user", "content": chat}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    log.info("chat read: %s, %d in / %d out tokens", response.stop_reason,
             response.usage.input_tokens, response.usage.output_tokens)

    if response.stop_reason != "end_turn":
        raise ChatUnreadable(response.stop_reason)
    text: Optional[str] = next((block.text for block in response.content if block.type == "text"), None)
    if text is None:
        raise ChatUnreadable("no text")
    return json.loads(text)
