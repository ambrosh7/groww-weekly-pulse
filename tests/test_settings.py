"""Phase 0: config load and window_weeks validation."""

from pathlib import Path

import pytest
import yaml

from src.config.settings import Settings, SettingsError, load_settings

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "config" / "settings.example.yaml"
SAMPLE = REPO_ROOT / "data" / "raw" / "groww_play_reviews_sample.csv"
DEFAULT_RAW = "groww_play_reviews.csv"


def test_load_example_settings():
    settings = load_settings(EXAMPLE)
    assert settings.product_name == "Groww"
    assert settings.play_package_id == "com.nextbillion.groww"
    assert settings.window_weeks == 10
    assert 8 <= settings.window_weeks <= 12
    assert settings.max_themes == 5
    assert settings.clustering_approach == "keyword_seed"
    assert settings.min_review_words == 8
    assert settings.default_raw_file.name == DEFAULT_RAW


def test_window_weeks_out_of_range_rejected(tmp_path: Path):
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["window_weeks"] = 3
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(SettingsError, match="window_weeks"):
        load_settings(bad)


def test_window_weeks_upper_bound_rejected(tmp_path: Path):
    data = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))
    data["window_weeks"] = 13
    bad = tmp_path / "bad.yaml"
    bad.write_text(yaml.dump(data), encoding="utf-8")

    with pytest.raises(SettingsError, match="window_weeks"):
        load_settings(bad)


def test_sample_play_export_exists_and_spans_window():
    assert SAMPLE.exists(), "Phase 0 requires sample under data/raw/"
    lines = SAMPLE.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 1  # header + rows
    header = lines[0].split(",")
    assert "store" in header
    assert "date" in header
    assert "text" in header
    body = "\n".join(lines[1:])
    assert "play" in body
    assert "app_store" not in body


def test_settings_from_dict_paths_resolve():
    settings = Settings.from_dict(
        {
            "window_weeks": 10,
            "paths": {"raw_dir": "data/raw"},
        }
    )
    assert settings.raw_dir == REPO_ROOT / "data" / "raw"
