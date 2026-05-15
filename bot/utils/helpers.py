import re
import time

_RE_MENTION = re.compile(r"<[@#&!]{0,2}\d+>")
_RE_EMOJI = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
_RE_CODE = re.compile(r"(`{1,3}).*?\1", re.DOTALL)
_RE_URL = re.compile(
    r"https?://[^\s]+"
    r"|www\.[^\s]+"
    r"|[^\s]+\.(com|org|net|io|dev|gg|co)[^\s]*",
    re.IGNORECASE,
)
_RE_NUMBER = re.compile(r"\b\d+\w*\b")
_RE_MARKDOWN = re.compile(r"[*_~`|>]")
_RE_WORD = re.compile(r"[A-Za-z']+")


def extract_words(content: str) -> list[str]:
    """
    Strip Discord-specific and irrelevant tokens from *content*, then return
    a list of lowercase alphabetic words suitable for spell-checking.
    """
    text = _RE_CODE.sub(" ", content)
    text = _RE_URL.sub(" ", text)
    text = _RE_MENTION.sub(" ", text)
    text = _RE_EMOJI.sub(" ", text)
    text = _RE_NUMBER.sub(" ", text)
    text = _RE_MARKDOWN.sub(" ", text)
    return [m.group(0).lower() for m in _RE_WORD.finditer(text)]


def format_uptime(start_monotonic: float) -> str:
    """Return a human-readable uptime string given a ``time.monotonic()`` start value."""
    elapsed = int(time.monotonic() - start_monotonic)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes:02d}m {seconds:02d}s"
