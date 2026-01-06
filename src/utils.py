from __future__ import annotations

import csv
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, TYPE_CHECKING

if TYPE_CHECKING:  # avoid circular import at runtime
    from .lexer import Token


class UserError(Exception):
    """Raised for predictable, user-facing errors that should be shown as-is."""


@dataclass
class StageResult:
    stage: str
    output_dir: Path
    generated: List[Path]
    message: str | None = None


def ensure_input_file(input_path: str | Path) -> Path:
    """Validate that the input file exists and is readable."""
    path = Path(input_path)
    if not path.is_file():
        raise UserError(f"Error: failed to read input file: {path} does not exist")
    return path


def output_dir_for_input(input_path: Path) -> Path:
    """Return the output directory for the given input file (without creating it)."""
    return Path("out") / input_path.stem


def ensure_output_dir(input_path: Path) -> Path:
    """Create and return the output directory for the given input file."""
    out_dir = output_dir_for_input(input_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_csv_with_header(path: Path, header: Iterable[str]) -> None:
    """Write a CSV file containing only the header row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(list(header))


def write_tokens_csv(path: Path, tokens: List["Token"]) -> None:
    """Write tokens to CSV with the required header."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["index", "type", "lexeme", "line", "col"])
        for tok in tokens:
            writer.writerow([tok.index, tok.type, tok.lexeme, tok.line, tok.col])


def write_text_file(path: Path, content: str) -> None:
    """Write plain text content to a file, ensuring the directory exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_action_goto_csv(
    path: Path,
    terminals: List[str],
    nonterminals: List[str],
    action: dict[int, dict[str, str]],
    goto_table: dict[int, dict[str, int]],
) -> None:
    """Write combined ACTION/GOTO CSV with stable ordering."""
    path.parent.mkdir(parents=True, exist_ok=True)
    max_state = max(action.keys()) if action else -1
    headers = ["state"] + terminals + nonterminals
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(headers)
        for state in range(max_state + 1):
            row: List[str | int] = [state]
            for t in terminals:
                row.append(action.get(state, {}).get(t, ""))
            for nt in nonterminals:
                goto_val = goto_table.get(state, {}).get(nt)
                row.append("" if goto_val is None else goto_val)
            writer.writerow(row)


def open_folder(path: Path) -> None:
    """Open a folder in the system file explorer, if possible."""
    if sys.platform.startswith("darwin"):
        subprocess.Popen(["open", str(path)])
    elif os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])
