"""Build simulator artefacts: snapshots.parquet + outcomes.parquet. Run: `make sim`."""

from __future__ import annotations

from scripts._log import get_logger

log = get_logger("build_sim")


def main() -> None:
    from sim import outcomes, simulator
    simulator.main()
    outcomes.main()


if __name__ == "__main__":
    main()
