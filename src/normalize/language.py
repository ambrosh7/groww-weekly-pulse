"""Language and emoji filters for the review corpus (Phase 2 quality)."""

from __future__ import annotations

import re

from langdetect import DetectorFactory, LangDetectException, detect

# Deterministic langdetect
DetectorFactory.seed = 0

# Common emoji / pictograph blocks + variation selectors / ZWJ
_EMOJI_RE = re.compile(
    "["
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002700-\U000027BF"  # dingbats
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"  # ZWJ
    "]+",
    flags=re.UNICODE,
)

# Indic and other non-Latin scripts commonly seen in IN Play reviews
_NON_LATIN_SCRIPT_RE = re.compile(
    "["
    "\u0900-\u097F"  # Devanagari (Hindi etc.)
    "\u0980-\u09FF"  # Bengali
    "\u0A00-\u0A7F"  # Gurmukhi
    "\u0A80-\u0AFF"  # Gujarati
    "\u0B00-\u0B7F"  # Oriya
    "\u0B80-\u0BFF"  # Tamil
    "\u0C00-\u0C7F"  # Telugu
    "\u0C80-\u0CFF"  # Kannada
    "\u0D00-\u0D7F"  # Malayalam
    "\u0D80-\u0DFF"  # Sinhala
    "\u0600-\u06FF"  # Arabic
    "\u0750-\u077F"
    "\u0400-\u04FF"  # Cyrillic
    "\u4E00-\u9FFF"  # CJK
    "\u3040-\u30FF"  # Japanese kana
    "\uAC00-\uD7AF"  # Hangul
    "]"
)

_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")


def strip_emojis(text: str) -> str:
    return _EMOJI_RE.sub(" ", text)


def is_emoji_review(text: str) -> bool:
    """
    True if the review is emoji-only or emoji-dominated
    (too few Latin letters once emojis/punctuation are removed).
    """
    if not text or not text.strip():
        return True
    if not _EMOJI_RE.search(text):
        return False
    without = strip_emojis(text)
    letters = _LATIN_LETTER_RE.findall(without)
    # Fewer than 3 Latin letters ⇒ treat as emoji review
    if len(letters) < 3:
        return True
    # Emoji count outweighs letter count heavily
    emoji_chars = sum(len(m.group(0)) for m in _EMOJI_RE.finditer(text))
    if emoji_chars >= max(6, len(letters)):
        return True
    return False


def has_non_latin_script(text: str) -> bool:
    return bool(_NON_LATIN_SCRIPT_RE.search(text))


def is_english(text: str) -> bool:
    """
    Keep English (Latin) reviews only.

    Rejects non-Latin scripts and non-English langdetect results.
    """
    if not text or not text.strip():
        return False
    if has_non_latin_script(text):
        return False

    cleaned = strip_emojis(text)
    cleaned = re.sub(r"[^\w\s']+", " ", cleaned, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 3 or not _LATIN_LETTER_RE.search(cleaned):
        return False

    try:
        lang = detect(cleaned)
    except LangDetectException:
        # Very short / odd Latin text: keep only if strongly Latin-letter heavy
        letters = _LATIN_LETTER_RE.findall(cleaned)
        return len(letters) >= 8 and (len(letters) / max(len(cleaned), 1)) >= 0.5

    return lang == "en"


def language_skip_reason(
    text: str,
    *,
    drop_emoji_reviews: bool = True,
    require_english: bool = True,
) -> str | None:
    """Return skip reason or None if the review should be kept."""
    if drop_emoji_reviews and is_emoji_review(text):
        return "emoji_review"
    if require_english and not is_english(text):
        return "non_english"
    return None
