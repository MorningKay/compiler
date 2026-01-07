from __future__ import annotations

from pathlib import Path
from typing import List

from .ir import Quad
from .opt import optimize_ir
from .utils import UserError, write_text_file


def emit_target(source_path: Path, out_dir: Path) -> Path:
    ir_opt_path = out_dir / "ir_opt.quad"
    if not ir_opt_path.exists():
        ir_opt_path, _ = optimize_ir(source_path, out_dir)
    quads = _parse_ir_file(ir_opt_path)
    _validate_labels(quads)
    asm_lines = _gen_asm(quads)
    target_path = out_dir / "target.asm"
    write_text_file(target_path, "\n".join(asm_lines) + "\n")
    return target_path


def _parse_ir_file(path: Path) -> List[Quad]:
    quads: List[Quad] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        # expected format: idx: (OP, a1, a2, res)
        if ":" not in line:
            continue
        _, rest = line.split(":", 1)
        rest = rest.strip()
        if not (rest.startswith("(") and rest.endswith(")")):
            continue
        inner = rest[1:-1]
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) != 4:
            continue
        op, a1, a2, res = parts
        quads.append(Quad(op=op, arg1=a1, arg2=a2, res=res, orig_index=None))
    return quads


def _validate_labels(quads: List[Quad]) -> None:
    defined = {q.res for q in quads if q.op == "LABEL"}
    used = {q.res for q in quads if q.op == "GOTO" or q.op.startswith("IF_")}
    missing = used - defined
    if missing:
        raise UserError(f"Error: undefined label {sorted(missing)[0]}")


def _emit_load(val: str, out: List[str]) -> None:
    if val == "-" or val == "":
        return
    if val.lstrip("-").isdigit():
        out.append(f"PUSH {val}")
    else:
        out.append(f"LOAD {val}")


def _gen_asm(quads: List[Quad]) -> List[str]:
    lines: List[str] = []
    for q in quads:
        if q.op == "LABEL":
            lines.append(f"{q.res}:")
            continue
        if q.op == "GOTO":
            lines.append(f"JMP {q.res}")
            continue
        if q.op == "ASSIGN":
            _emit_load(q.arg1, lines)
            lines.append(f"STORE {q.res}")
            continue
        if q.op in {"ADD", "SUB", "MUL", "DIV"}:
            _emit_load(q.arg1, lines)
            _emit_load(q.arg2, lines)
            lines.append(q.op)
            lines.append(f"STORE {q.res}")
            continue
        if q.op in {"IF_GT", "IF_LT", "IF_EQ", "IF_NE", "IF_LE", "IF_GE"}:
            _emit_load(q.arg1, lines)
            _emit_load(q.arg2, lines)
            if q.op in {"IF_GT", "IF_LT", "IF_EQ", "IF_NE"}:
                cmp_op = {"IF_GT": "GT", "IF_LT": "LT", "IF_EQ": "EQ", "IF_NE": "NE"}[q.op]
                lines.append(cmp_op)
                lines.append(f"JNZ {q.res}")
            elif q.op == "IF_LE":
                lines.append("GT")
                lines.append(f"JZ {q.res}")
            elif q.op == "IF_GE":
                lines.append("LT")
                lines.append(f"JZ {q.res}")
            continue
        raise UserError(f"Internal error: unsupported op {q.op}")
    lines.append("HALT")
    return lines
