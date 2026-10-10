"""Allow `python -m src.orchestrator`."""

from src.orchestrator.run import main

if __name__ == "__main__":
    raise SystemExit(main())
