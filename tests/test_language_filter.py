"""Emoji and English-only filters for Phase 2 corpus."""

from datetime import datetime, timezone

from src.normalize.language import is_emoji_review, is_english, language_skip_reason
from src.normalize.pipeline import normalize_rows

PACKAGE = "com.nextbillion.groww"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def test_emoji_only_detected():
    assert is_emoji_review("👍")
    assert is_emoji_review("🙌🏻🙌🏻")
    assert is_emoji_review("🔥🔥🔥")
    assert not is_emoji_review(
        "KYC verification failed after uploading my aadhaar card documents"
    )


def test_non_english_detected():
    assert not is_english("आवेदन प्रक्रिया बहुत खराब है और सपोर्ट नहीं मिलता")
    assert not is_english("আমার অ্যাকাউন্ট খুলতে সমস্যা হচ্ছে বারবার")
    assert is_english(
        "Withdrawal to my bank account has been pending for several days now"
    )


def test_language_skip_reasons():
    assert language_skip_reason("👍👍") == "emoji_review"
    assert (
        language_skip_reason("यह ऐप बिल्कुल काम नहीं कर रहा है कृपया ठीक करें")
        == "non_english"
    )
    assert (
        language_skip_reason(
            "The trading charts freeze whenever I switch between stocks quickly"
        )
        is None
    )


def test_normalize_drops_emoji_and_non_english():
    rows = [
        {
            "store": "play",
            "rating": 5,
            "text": "👍👍👍👍👍👍👍👍👍",
            "date": "2026-09-01",
        },
        {
            "store": "play",
            "rating": 1,
            "text": "यह ऐप बिल्कुल काम नहीं कर रहा है और सपोर्ट नहीं मिलता है",
            "date": "2026-09-02",
        },
        {
            "store": "play",
            "rating": 2,
            "text": "UPI payment failed while trying to add money to my account today",
            "date": "2026-09-03",
        },
    ]
    result = normalize_rows(
        rows,
        play_package_id=PACKAGE,
        window_weeks=10,
        min_review_words=8,
        drop_emoji_reviews=True,
        require_english=True,
        now=NOW,
    )
    assert result.stats["kept"] == 1
    assert result.stats["skipped"].get("emoji_review", 0) >= 1
    assert result.stats["skipped"].get("non_english", 0) >= 1
    assert "UPI payment" in result.reviews[0].text
