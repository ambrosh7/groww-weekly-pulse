"""Phase 4: local orchestrator — happy path, short-circuit, overwrite, weeks CLI."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.config.settings import Settings, SettingsError, validate_window_weeks
from src.orchestrator import OrchestratorError, cmd_run, run_weekly_pulse
from src.theme.run import ThemeError

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
        email_recipient="ops@example.com",
    )


def test_validate_window_weeks_bounds():
    assert validate_window_weeks(8) == 8
    assert validate_window_weeks(12) == 12
    with pytest.raises(SettingsError, match="between 8 and 12"):
        validate_window_weeks(3)
    with pytest.raises(SettingsError, match="between 8 and 12"):
        validate_window_weeks(13)


def test_orchestrator_happy_path_sample(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.processed_dir.mkdir(parents=True)
    settings.output_dir.mkdir(parents=True)

    result = run_weekly_pulse(settings, raw_path=SAMPLE, now=NOW)
    assert result.stages_completed == ("ingest", "theme", "pulse")
    assert result.pulse_path.exists()
    assert result.pulse_json_path.exists()
    assert result.reviews_path.exists()
    assert result.themes_path.exists()
    assert result.theme_count == 3
    assert result.review_count >= 30
    assert result.word_count <= 250
    assert result.doc_url is None
    assert result.draft_id is None
    assert result.source_fixture == "groww_play_reviews_sample.csv"
    assert result.email_recipient == "ops@example.com"

    md = result.pulse_path.read_text(encoding="utf-8")
    assert "## Top themes" in md
    assert "## What users said" in md
    assert "## Action ideas" in md


def test_orchestrator_idempotent_overwrite(tmp_path: Path):
    settings = _settings(tmp_path)
    settings.processed_dir.mkdir(parents=True)
    settings.output_dir.mkdir(parents=True)

    first = run_weekly_pulse(settings, raw_path=SAMPLE, now=NOW)
    first_md = first.pulse_path.read_text(encoding="utf-8")
    first_reviews = first.reviews_path.read_text(encoding="utf-8")

    # Stale append marker must disappear on re-run (overwrite, not append)
    first.pulse_path.write_text(first_md + "\nAPPEND_MARKER\n", encoding="utf-8")
    first.reviews_path.write_text(first_reviews + "\n", encoding="utf-8")

    second = run_weekly_pulse(settings, raw_path=SAMPLE, now=NOW)
    assert second.pulse_path == first.pulse_path
    body = second.pulse_path.read_text(encoding="utf-8")
    assert "APPEND_MARKER" not in body
    assert body.count("# Groww Weekly Pulse") == 1
    payload = json.loads(second.pulse_json_path.read_text(encoding="utf-8"))
    assert payload["week_ending"] == second.week_ending


def test_theme_failure_short_circuits_no_new_pulse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    settings = _settings(tmp_path)
    settings.processed_dir.mkdir(parents=True)
    settings.output_dir.mkdir(parents=True)

    stale = settings.output_dir / "pulse.md"
    stale.write_text("PRIOR_SUCCESS_PULSE\n", encoding="utf-8")
    (settings.output_dir / "pulse.json").write_text('{"stale": true}\n', encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise ThemeError("simulated theme crash")

    monkeypatch.setattr("src.orchestrator.run.run_theme", boom)

    with pytest.raises(OrchestratorError, match="Theme failed"):
        run_weekly_pulse(settings, raw_path=SAMPLE, now=NOW)

    # Prior pulse left untouched (E4.1); no new success claimed
    assert stale.read_text(encoding="utf-8") == "PRIOR_SUCCESS_PULSE\n"
    # Ingest did regenerate reviews.json; theme never wrote themes.json
    assert (settings.processed_dir / "reviews.json").exists()
    assert not (settings.processed_dir / "themes.json").exists()


def test_pulse_gate_failure_removes_incomplete_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    settings = _settings(tmp_path)
    settings.processed_dir.mkdir(parents=True)
    settings.output_dir.mkdir(parents=True)

    from src.pulse.gates import PulseGateError

    def boom_pulse(*_args, **_kwargs):
        # Simulate gate fail after a partial draft hit disk
        (settings.output_dir / "pulse.md").write_text("partial\n", encoding="utf-8")
        raise PulseGateError("simulated gate fail")

    monkeypatch.setattr("src.orchestrator.run.run_pulse", boom_pulse)

    with pytest.raises(OrchestratorError, match="Pulse failed"):
        run_weekly_pulse(settings, raw_path=SAMPLE, now=NOW)

    assert not (settings.output_dir / "pulse.md").exists()
    assert not (settings.output_dir / "pulse.json").exists()


def test_cli_rejects_invalid_weeks(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    # Minimal args namespace
    class Args:
        input = str(SAMPLE)
        weeks = 3
        recipient = None
        config = None

    # Point load_settings at example config via monkeypatched paths — use real load
    # by writing a temp config that points at tmp dirs
    cfg = tmp_path / "settings.yaml"
    cfg.write_text(
        f"""
product_name: Groww
play_package_id: com.nextbillion.groww
window_weeks: 10
max_themes: 5
paths:
  raw_dir: {tmp_path / "raw"}
  processed_dir: {tmp_path / "processed"}
  output_dir: {tmp_path / "output"}
  default_raw_file: {SAMPLE}
""",
        encoding="utf-8",
    )
    Args.config = str(cfg)

    code = cmd_run(Args())
    assert code == 1
    err = capsys.readouterr().err
    assert "between 8 and 12" in err
    # Must not have started ingest
    assert not (tmp_path / "processed" / "reviews.json").exists()


def test_cli_happy_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    cfg = tmp_path / "settings.yaml"
    cfg.write_text(
        f"""
product_name: Groww
play_package_id: com.nextbillion.groww
window_weeks: 10
max_themes: 5
min_review_words: 8
drop_emoji_reviews: true
require_english: true
paths:
  raw_dir: {tmp_path / "raw"}
  processed_dir: {tmp_path / "processed"}
  output_dir: {tmp_path / "output"}
  default_raw_file: {SAMPLE}
""",
        encoding="utf-8",
    )

    class Args:
        input = str(SAMPLE)
        weeks = 10
        recipient = "me@example.com"
        config = str(cfg)

    code = cmd_run(Args())
    assert code == 0
    out = capsys.readouterr().out
    assert "Weekly pulse OK" in out
    assert (tmp_path / "output" / "pulse.md").exists()
    assert (tmp_path / "output" / "pulse.json").exists()
