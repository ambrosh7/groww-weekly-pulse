"""Load and validate project settings (Phase 0)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXAMPLE = REPO_ROOT / "config" / "settings.example.yaml"
DEFAULT_LOCAL = REPO_ROOT / "config" / "settings.yaml"

WINDOW_WEEKS_MIN = 8
WINDOW_WEEKS_MAX = 12


class SettingsError(ValueError):
    """Invalid or missing configuration."""


def validate_window_weeks(weeks: int) -> int:
    """Reject invalid lookback before any pipeline stage (E4.6)."""
    weeks = int(weeks)
    if not WINDOW_WEEKS_MIN <= weeks <= WINDOW_WEEKS_MAX:
        raise SettingsError(
            f"window_weeks must be between {WINDOW_WEEKS_MIN} and {WINDOW_WEEKS_MAX}, "
            f"got {weeks}"
        )
    return weeks


@dataclass
class Settings:
    product_name: str
    play_package_id: str
    window_weeks: int
    max_themes: int
    theme_hints: list[str] = field(default_factory=list)
    pulse_top_themes: int = 3
    quote_count: int = 3
    action_count: int = 3
    max_pulse_words: int = 250
    email_recipient: str = "you@example.com"
    doc_title_template: str = "Groww Weekly Pulse — {week_ending}"
    # Phase 5–6 MCP delivery (bearer token via env MCP_HTTP_BEARER_TOKEN only)
    mcp_base_url: str = "https://gmail-docs-mcp-server-production.up.railway.app"
    google_doc_id: str = ""
    google_doc_url: str = ""
    publish_to_docs: bool = False
    send_email: bool = False
    include_full_pulse_in_email: bool = True
    raw_dir: Path = field(default_factory=lambda: REPO_ROOT / "data" / "raw")
    processed_dir: Path = field(default_factory=lambda: REPO_ROOT / "data" / "processed")
    output_dir: Path = field(default_factory=lambda: REPO_ROOT / "data" / "output")
    default_raw_file: Path = field(
        default_factory=lambda: REPO_ROOT / "data" / "raw" / "groww_play_reviews.csv"
    )
    allow_soft_fail: bool = False
    clustering_approach: str = "keyword_seed"
    # Keep reviews with word_count > min_review_words (default: more than 8 words)
    min_review_words: int = 8
    drop_emoji_reviews: bool = True
    require_english: bool = True
    quotes_per_theme: int = 3

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> Settings:
        paths = data.get("paths") or {}
        window_weeks = validate_window_weeks(int(data["window_weeks"]))

        max_themes = int(data.get("max_themes", 5))
        if max_themes < 1 or max_themes > 5:
            raise SettingsError(f"max_themes must be between 1 and 5, got {max_themes}")

        def resolve(key: str, default: str) -> Path:
            value = paths.get(key, default)
            path = Path(value)
            return path if path.is_absolute() else repo_root / path

        return cls(
            product_name=str(data.get("product_name", "Groww")),
            play_package_id=str(data.get("play_package_id", "com.nextbillion.groww")),
            window_weeks=window_weeks,
            max_themes=max_themes,
            theme_hints=list(data.get("theme_hints") or []),
            pulse_top_themes=int(data.get("pulse_top_themes", 3)),
            quote_count=int(data.get("quote_count", 3)),
            action_count=int(data.get("action_count", 3)),
            max_pulse_words=int(data.get("max_pulse_words", 250)),
            email_recipient=str(data.get("email_recipient", "you@example.com")),
            doc_title_template=str(
                data.get("doc_title_template", "Groww Weekly Pulse — {week_ending}")
            ),
            mcp_base_url=str(
                data.get(
                    "mcp_base_url",
                    "https://gmail-docs-mcp-server-production.up.railway.app",
                )
            ).rstrip("/"),
            google_doc_id=str(data.get("google_doc_id") or ""),
            google_doc_url=str(data.get("google_doc_url") or ""),
            publish_to_docs=bool(data.get("publish_to_docs", False)),
            send_email=bool(data.get("send_email", False)),
            include_full_pulse_in_email=bool(
                data.get("include_full_pulse_in_email", True)
            ),
            raw_dir=resolve("raw_dir", "data/raw"),
            processed_dir=resolve("processed_dir", "data/processed"),
            output_dir=resolve("output_dir", "data/output"),
            default_raw_file=resolve(
                "default_raw_file", "data/raw/groww_play_reviews.csv"
            ),
            allow_soft_fail=bool(data.get("allow_soft_fail", False)),
            clustering_approach=str(data.get("clustering_approach", "keyword_seed")),
            min_review_words=int(data.get("min_review_words", 8)),
            drop_emoji_reviews=bool(data.get("drop_emoji_reviews", True)),
            require_english=bool(data.get("require_english", True)),
            quotes_per_theme=int(data.get("quotes_per_theme", 3)),
        )


def load_settings(path: Path | None = None) -> Settings:
    """Load settings from YAML. Prefers local settings.yaml, else example."""
    candidate = path
    if candidate is None:
        if DEFAULT_LOCAL.exists():
            candidate = DEFAULT_LOCAL
        elif DEFAULT_EXAMPLE.exists():
            candidate = DEFAULT_EXAMPLE
        else:
            raise SettingsError(
                f"No config found. Copy {DEFAULT_EXAMPLE.name} to settings.yaml "
                f"under {DEFAULT_EXAMPLE.parent}"
            )

    candidate = Path(candidate)
    if not candidate.exists():
        raise SettingsError(f"Config file not found: {candidate}")

    with candidate.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise SettingsError("Config root must be a mapping")

    return Settings.from_dict(data)
