"""Phase 3: pulse writer, validation gates, sample golden path."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.config.settings import Settings
from src.ingest.run import run_ingest
from src.normalize.schema import Review
from src.pulse.gates import (
    PulseAction,
    PulseDraft,
    PulseGateError,
    PulseQuote,
    PulseTheme,
    count_words,
    find_pii_hits,
    validate_pulse,
)
from src.pulse.run import run_pulse
from src.pulse.writer import select_quotes, select_top_themes, write_pulse
from src.theme.engine import cluster_reviews
from src.theme.run import run_theme, write_themes_json

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = REPO_ROOT / "data" / "raw" / "groww_play_reviews_sample.csv"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        product_name="Groww",
        play_package_id="com.nextbillion.groww",
        window_weeks=10,
        max_themes=5,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        output_dir=tmp_path / "output",
        default_raw_file=SAMPLE,
        min_review_words=8,
        drop_emoji_reviews=True,
        require_english=True,
        quotes_per_theme=3,
        pulse_top_themes=3,
        quote_count=3,
        action_count=3,
        max_pulse_words=250,
        allow_soft_fail=False,
    )


def _r(rid: str, text: str, rating: int = 1) -> Review:
    return Review(
        id=rid,
        store="play",
        rating=rating,
        title="",
        text=text,
        date="2026-09-01",
        locale="en_IN",
    )


def _meta(**overrides):
    base = {
        "window_start": "2026-07-31",
        "window_end": "2026-10-09",
        "window_weeks": 10,
        "min_review_words": 8,
        "drop_emoji_reviews": True,
        "require_english": True,
        "kept": 3,
        "skipped": {},
        "data_starved": False,
    }
    base.update(overrides)
    return base


def test_count_words_whitespace():
    assert count_words("one two  three") == 3


def test_find_pii_hits():
    assert "email" in find_pii_hits("reach me at user@example.com please")
    assert find_pii_hits("no secrets here") == []


def test_select_top_themes_by_rank():
    themes = [
        {"theme_id": "kyc", "rank_score": 0.5, "label": "KYC"},
        {"theme_id": "trading", "rank_score": 0.9, "label": "Trading"},
        {"theme_id": "withdrawals", "rank_score": 0.7, "label": "Withdrawals"},
        {"theme_id": "payments", "rank_score": 0.4, "label": "Payments"},
    ]
    top = select_top_themes(themes, n=3)
    assert [t["theme_id"] for t in top] == ["trading", "withdrawals", "kyc"]


def test_invented_quote_rejected():
    reviews = [
        _r("a", "KYC verification failed after uploading my aadhaar card documents"),
        _r("b", "Withdrawal to bank settlement pending for many days now"),
        _r("c", "Trading order cancelled without explaining the reason clearly"),
    ]
    result = cluster_reviews(reviews, max_themes=5)
    draft = write_pulse(
        themes_payload={"themes": [t.to_dict() for t in result.themes], "meta": result.stats},
        reviews=reviews,
        reviews_meta=_meta(kept=len(reviews)),
    )
    # Inject invented quote
    bad = list(draft.quotes)
    bad[0] = PulseQuote(
        text="Completely invented quote about Groww failing everywhere",
        theme_id=bad[0].theme_id,
        theme_label=bad[0].theme_label,
        rating=1,
        review_id="x",
    )
    draft.quotes = bad
    draft.markdown = draft.markdown.replace(
        '"', '"', 1
    )  # keep structure; validate uses quote objects
    with pytest.raises(PulseGateError, match="Invented|paraphrased"):
        validate_pulse(
            draft,
            review_texts=[r.text for r in reviews],
            reviews_meta=_meta(kept=len(reviews)),
        )


def test_privacy_gate_blocks_phone_in_body():
    themes = [
        PulseTheme("kyc", "KYC / verification", 2, 1.5, 1.0, "selfie fails"),
        PulseTheme("withdrawals", "Withdrawals", 2, 1.5, 0.9, "bank delay"),
        PulseTheme("trading", "Trading", 2, 2.0, 0.8, "order cancel"),
    ]
    quotes = [
        PulseQuote("KYC verification failed after uploading my aadhaar card documents", "kyc", "KYC / verification", 1, "a"),
        PulseQuote("Withdrawal to bank settlement pending for many days now", "withdrawals", "Withdrawals", 1, "b"),
        PulseQuote("Trading order cancelled without explaining the reason clearly", "trading", "Trading", 1, "c"),
    ]
    actions = [
        PulseAction("fix selfie recovery", "kyc", "KYC / verification"),
        PulseAction("Show IFSC reject reason", "withdrawals", "Withdrawals"),
        PulseAction("Explain order cancels", "trading", "Trading"),
    ]
    md = (
        "# Groww Weekly Pulse — week ending 2026-10-09\n\n"
        "Window: last 10 weeks (2026-07-31 → 2026-10-09) · Play reviews analyzed: 3\n"
        "Filters: >8 words · English only · emoji reviews excluded\n\n"
        "## Top themes\n"
        "1. KYC / verification — n=2, avg ★=1.5. selfie fails\n"
        "2. Withdrawals — n=2, avg ★=1.5. bank delay\n"
        "3. Trading — n=2, avg ★=2.0. order cancel\n\n"
        "## What users said\n"
        '- "KYC verification failed after uploading my aadhaar card documents" (KYC / verification)\n'
        '- "Withdrawal to bank settlement pending for many days now" (Withdrawals)\n'
        '- "Trading order cancelled without explaining the reason clearly" (Trading)\n\n'
        "## Action ideas\n"
        "1. Fix selfie recovery — grounded in KYC / verification\n"
        "2. Show IFSC reject reason — grounded in Withdrawals\n"
        "3. Explain order cancels — grounded in Trading\n"
        "Call 9876543210 for more.\n"
    )
    draft = PulseDraft(
        week_ending="2026-10-09",
        window_weeks=10,
        window_start="2026-07-31",
        window_end="2026-10-09",
        review_count=3,
        min_review_words=8,
        drop_emoji_reviews=True,
        require_english=True,
        product_name="Groww",
        themes=themes,
        quotes=quotes,
        actions=actions,
        markdown=md,
        word_count=count_words(md),
    )
    with pytest.raises(PulseGateError, match="PII"):
        validate_pulse(
            draft,
            review_texts=[q.text for q in quotes],
            reviews_meta=_meta(kept=3),
        )


def test_select_quotes_one_per_theme():
    reviews = [
        _r("k1", "KYC keeps failing at the selfie verification step every day", 1),
        _r("k2", "Another KYC digilocker issue that is slightly longer text here", 2),
        _r("w1", "Withdrawal to bank settlement pending for many days now", 1),
        _r("t1", "Trading order cancelled without explaining the reason clearly", 1),
    ]
    themes = [
        {
            "theme_id": "kyc",
            "label": "KYC / verification",
            "review_ids": ["k1", "k2"],
            "representative_quotes": [reviews[0].text],
            "count": 2,
            "avg_rating": 1.5,
            "rank_score": 1.0,
        },
        {
            "theme_id": "withdrawals",
            "label": "Withdrawals",
            "review_ids": ["w1"],
            "representative_quotes": [reviews[2].text],
            "count": 1,
            "avg_rating": 1.0,
            "rank_score": 0.8,
        },
        {
            "theme_id": "trading",
            "label": "Trading",
            "review_ids": ["t1"],
            "representative_quotes": [reviews[3].text],
            "count": 1,
            "avg_rating": 1.0,
            "rank_score": 0.7,
        },
    ]
    picked = select_quotes(themes, {r.id: r for r in reviews}, quote_count=3)
    assert len(picked) == 3
    assert {q.theme_id for q in picked} == {"kyc", "withdrawals", "trading"}


def test_sample_golden_path(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.raw_dir.mkdir(parents=True)
    settings.processed_dir.mkdir(parents=True)
    settings.output_dir.mkdir(parents=True)

    ingest = run_ingest(settings, raw_path=SAMPLE, now=NOW)
    assert ingest.stats["kept"] >= 30  # ~36 after filters
    assert ingest.stats["kept"] <= 40

    theme = run_theme(settings)
    assert 1 <= theme.stats["theme_count"] <= 5
    top_ids = {t.theme_id for t in theme.themes[:3]}
    growwish = {"trading", "withdrawals", "kyc", "payments", "onboarding", "stability", "support"}
    assert top_ids & growwish, f"top themes unexpected: {top_ids}"

    result = run_pulse(settings)
    assert result.stats["theme_count"] == 3
    assert result.stats["quote_count"] == 3
    assert result.stats["action_count"] == 3
    assert result.stats["word_count"] <= 250
    assert result.stats["source_fixture"] == "groww_play_reviews_sample.csv"

    md = result.md_path.read_text(encoding="utf-8")
    assert "## Top themes" in md
    assert "## What users said" in md
    assert "## Action ideas" in md
    assert "Play reviews analyzed:" in md

    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert payload["doc_url"] is None
    assert len(payload["themes"]) == 3
    assert len(payload["quotes"]) == 3
    assert len(payload["actions"]) == 3
    assert payload["word_count"] <= 250

    corpus = " || ".join(r.text for r in ingest.reviews)
    for quote in payload["quotes"]:
        assert quote["text"] in corpus

    # Actions map to top theme labels
    top_labels = {t["label"] for t in payload["themes"]}
    for action in payload["actions"]:
        assert action["theme_label"] in top_labels
        assert "improve UX" not in action["text"].lower()


def test_gate_fails_closed_does_not_leave_success_pulse(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.processed_dir.mkdir(parents=True)
    settings.output_dir.mkdir(parents=True)

    # Minimal corpus with only 1 theme → should block (no soft-fail)
    reviews = [
        _r("1", "KYC verification failed at selfie step for my demat account", 1),
        _r("2", "KYC aadhaar eSign stuck and support asks to retry tomorrow", 1),
        _r("3", "KYC digilocker fetch fails with no offline upload option shown", 1),
    ]
    result = cluster_reviews(reviews, max_themes=5)
    write_themes_json(result, settings.processed_dir / "themes.json")
    (settings.processed_dir / "reviews.json").write_text(
        json.dumps(
            {
                "meta": _meta(kept=3),
                "reviews": [r.to_dict() for r in reviews],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Pre-seed a stale pulse that must be removed on failure
    (settings.output_dir / "pulse.md").write_text("stale\n", encoding="utf-8")
    (settings.output_dir / "pulse.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(PulseGateError):
        run_pulse(settings)

    assert not (settings.output_dir / "pulse.md").exists()
    assert not (settings.output_dir / "pulse.json").exists()
