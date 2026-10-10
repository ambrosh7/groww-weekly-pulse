"""CLI entrypoints for Groww Weekly Review Pulse."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config.settings import SettingsError, load_settings
from src.ingest.fetch_play import FetchError, fetch_groww_reviews, save_raw_csv, save_raw_json
from src.ingest.load import IngestError
from src.ingest.run import run_ingest
from src.normalize.pipeline import EmptyCorpusError
from src.deliver import main as deliver_main
from src.orchestrator import cmd_run
from src.pulse.gates import PulseGateError
from src.pulse.run import PulseError, run_pulse
from src.theme.run import ThemeError, run_theme


def cmd_validate_config(_: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    print("Config OK")
    print(f"  product_name: {settings.product_name}")
    print(f"  play_package_id: {settings.play_package_id}")
    print(f"  window_weeks: {settings.window_weeks}")
    print(f"  max_themes: {settings.max_themes}")
    print(f"  clustering_approach: {settings.clustering_approach}")
    print(f"  min_review_words: {settings.min_review_words} (keep word_count > this)")
    print(f"  drop_emoji_reviews: {settings.drop_emoji_reviews}")
    print(f"  require_english: {settings.require_english}")
    print(f"  default_raw_file: {settings.default_raw_file}")
    print(f"  raw exists: {settings.default_raw_file.exists()}")
    print(f"  mcp_base_url: {settings.mcp_base_url}")
    print(f"  google_doc_id: {settings.google_doc_id or '(unset)'}")
    print(f"  publish_to_docs: {settings.publish_to_docs}")
    print(f"  send_email: {settings.send_email}")
    print(f"  email_recipient: {settings.email_recipient}")
    return 0


def cmd_fetch_reviews(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    out_csv = Path(args.output) if args.output else settings.raw_dir / "groww_play_reviews.csv"
    try:
        rows = fetch_groww_reviews(
            settings,
            lang=args.lang,
            country=args.country,
            max_reviews=args.max_reviews,
        )
    except FetchError as exc:
        print(f"Fetch error: {exc}", file=sys.stderr)
        return 1

    save_raw_csv(rows, out_csv)
    save_raw_json(rows, out_csv.with_suffix(".json"))
    dates = sorted(r["date"] for r in rows if r.get("date"))
    print(f"Downloaded {len(rows)} public Play reviews for {settings.play_package_id}")
    print(f"  lang/country: {args.lang}/{args.country}")
    if dates:
        print(f"  date range: {dates[0]} → {dates[-1]}")
    print(f"  wrote: {out_csv}")
    print(f"  wrote: {out_csv.with_suffix('.json')}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    raw_path = Path(args.input) if args.input else None
    try:
        result = run_ingest(settings, raw_path=raw_path)
    except (IngestError, EmptyCorpusError, SettingsError) as exc:
        print(f"Ingest error: {exc}", file=sys.stderr)
        return 1

    out = settings.processed_dir / "reviews.json"
    print(f"Ingest OK — {result.stats['kept']} reviews")
    print(f"  window: {result.stats['window_start']} → {result.stats['window_end']}")
    print(f"  skipped: {result.stats['skipped']}")
    if result.stats.get("data_starved"):
        print("  warning: data-starved (<10 reviews in window)")
    print(f"  wrote: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Groww Weekly Review Pulse")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-config", help="Load and validate settings")
    validate.set_defaults(func=cmd_validate_config)

    fetch = sub.add_parser(
        "fetch-reviews",
        help="Download public Google Play reviews for Groww (no login)",
    )
    fetch.add_argument("--lang", default="en", help="Play language code (default: en)")
    fetch.add_argument("--country", default="in", help="Play country code (default: in)")
    fetch.add_argument(
        "--max-reviews",
        type=int,
        default=15000,
        help="Max reviews to fetch while covering window_weeks (default: 15000)",
    )
    fetch.add_argument(
        "-o",
        "--output",
        help="CSV output path (default: data/raw/groww_play_reviews.csv)",
    )
    fetch.set_defaults(func=cmd_fetch_reviews)

    ingest = sub.add_parser("ingest", help="Normalize raw exports → data/processed/reviews.json")
    ingest.add_argument(
        "-i",
        "--input",
        help="Specific raw CSV/JSON (default: prefer groww_play_reviews.csv in data/raw)",
    )
    ingest.set_defaults(func=cmd_ingest)

    theme = sub.add_parser("theme", help="Cluster reviews.json → data/processed/themes.json")
    theme.add_argument(
        "-i",
        "--input",
        help="Path to reviews.json (default: data/processed/reviews.json)",
    )
    theme.set_defaults(func=cmd_theme)

    pulse = sub.add_parser(
        "pulse",
        help="Write validated pulse.md / pulse.json from processed artifacts",
    )
    pulse.add_argument(
        "--reviews",
        help="Path to reviews.json (default: data/processed/reviews.json)",
    )
    pulse.add_argument(
        "--themes",
        help="Path to themes.json (default: data/processed/themes.json)",
    )
    pulse.add_argument(
        "-o",
        "--output-dir",
        help="Output directory (default: data/output)",
    )
    pulse.set_defaults(func=cmd_pulse)

    # Phases 4–6 — local pipeline + optional Docs/Gmail via MCP
    # (also: python -m src.orchestrator)
    run = sub.add_parser(
        "run",
        help="Orchestrate ingest → theme → pulse → optional Docs/Gmail MCP delivery",
    )
    run.add_argument(
        "-i",
        "--input",
        help="Raw Play CSV/JSON (default: prefer groww_play_reviews.csv in data/raw)",
    )
    run.add_argument(
        "--weeks",
        type=int,
        default=None,
        help="Review lookback weeks (8–12; overrides config)",
    )
    run.add_argument(
        "--recipient",
        default=None,
        help="Email recipient for Gmail notify (overrides config)",
    )
    run.add_argument(
        "--config",
        default=None,
        help="Path to settings YAML",
    )
    run.add_argument(
        "--deliver",
        action="store_true",
        help="Enable Docs append + Gmail send (requires MCP_HTTP_BEARER_TOKEN + doc id)",
    )
    run.add_argument(
        "--publish-docs",
        action="store_true",
        help="Append pulse to configured Google Doc via MCP",
    )
    run.add_argument(
        "--send-email",
        action="store_true",
        help="Send pulse email via MCP (requires Docs publish in same run)",
    )
    run.add_argument(
        "--local-only",
        action="store_true",
        help="Force skip Docs/Gmail even if enabled in settings",
    )
    run.set_defaults(func=cmd_orchestrator_run)

    deliver = sub.add_parser(
        "deliver",
        help="Append existing pulse.md to Google Doc + send Gmail (Phases 5–6 only)",
    )
    deliver.add_argument("--config", default=None, help="Path to settings YAML")
    deliver.add_argument("--pulse-md", default=None, help="Override pulse.md path")
    deliver.add_argument("--pulse-json", default=None, help="Override pulse.json path")
    deliver.add_argument(
        "--docs-only",
        action="store_true",
        help="Append to Google Doc only (skip email)",
    )
    deliver.set_defaults(func=cmd_deliver)

    return parser


def cmd_orchestrator_run(args: argparse.Namespace) -> int:
    return cmd_run(args)


def cmd_deliver(args: argparse.Namespace) -> int:
    argv: list[str] = []
    if args.config:
        argv.extend(["--config", args.config])
    if args.pulse_md:
        argv.extend(["--pulse-md", args.pulse_md])
    if args.pulse_json:
        argv.extend(["--pulse-json", args.pulse_json])
    if args.docs_only:
        argv.append("--docs-only")
    return deliver_main(argv)


def cmd_theme(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    reviews_path = Path(args.input) if args.input else None
    try:
        result = run_theme(settings, reviews_path=reviews_path)
    except (ThemeError, ValueError, RuntimeError) as exc:
        print(f"Theme error: {exc}", file=sys.stderr)
        return 1

    out = settings.processed_dir / "themes.json"
    print(f"Theme OK — {result.stats['theme_count']} themes from {result.stats['review_count']} reviews")
    for theme in result.themes:
        print(
            f"  [{theme.rank_score:.3f}] {theme.label}: "
            f"n={theme.count} avg★={theme.avg_rating} quotes={len(theme.representative_quotes)}"
        )
    print(f"  wrote: {out}")
    return 0


def cmd_pulse(args: argparse.Namespace) -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    reviews_path = Path(args.reviews) if args.reviews else None
    themes_path = Path(args.themes) if args.themes else None
    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        result = run_pulse(
            settings,
            reviews_path=reviews_path,
            themes_path=themes_path,
            output_dir=output_dir,
        )
    except (PulseError, PulseGateError, ThemeError) as exc:
        print(f"Pulse error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Pulse OK — week ending {result.stats['week_ending']} · "
        f"{result.stats['theme_count']}/3 themes · "
        f"{result.stats['quote_count']} quotes · "
        f"{result.stats['action_count']} actions · "
        f"{result.stats['word_count']} words"
    )
    if result.stats.get("source_fixture"):
        print(f"  source_fixture: {result.stats['source_fixture']}")
    for theme in result.draft.themes:
        print(f"  theme: {theme.label} (n={theme.count}, avg★={theme.avg_rating})")
    print(f"  wrote: {result.md_path}")
    print(f"  wrote: {result.json_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
