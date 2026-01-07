from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import pipeline
from .gui import launch
from .utils import UserError


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MiniLang compiler driver (M0 stub)")
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Run in tkinter GUI mode (default) or CLI mode.",
    )
    parser.add_argument(
        "--input", dest="input_file", help="Path to the MiniLang source file."
    )
    parser.add_argument(
        "--stage",
        choices=pipeline.SUPPORTED_STAGES,
        help="Which stage to run in CLI mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.mode == "gui":
        initial = Path(args.input_file) if args.input_file else None
        launch(initial_file=initial)
        return

    # CLI mode
    if not args.input_file:
        print("Error: --input is required in cli mode", file=sys.stderr)
        sys.exit(2)

    stage = args.stage or "all"

    try:
        result = pipeline.run_stage(stage, args.input_file)
    except UserError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Stage '{result.stage}' finished. Output folder: {result.output_dir}")
    if result.generated:
        print("Generated files:")
        for path in result.generated:
            print(f"  {path}")
    else:
        print("No files were generated.")
    if result.stage == "all":
        print(f"Success: output written to {result.output_dir}")


if __name__ == "__main__":
    main()
