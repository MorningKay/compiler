from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .cfg import build_cfg, render_cfg
from .ir import IRBuilder, Quad, generate_ir_quads
from .utils import UserError, write_text_file


@dataclass
class PassStats:
    removed: List[int]
    replaced: List[Tuple[int, str, str]]
    notes: List[str]


def optimize_ir(source_path: Path, out_dir: Path) -> Tuple[Path, Path]:
    builder = generate_ir_quads(source_path)
    cfg_blocks = build_cfg(builder)

    quads = list(builder.quads)
    pipeline = ["Folding", "ConstProp", "CopyProp", "DCE"]
    stats = {name: PassStats([], [], []) for name in pipeline}

    # Block-local passes, iterate up to 3 rounds
    for _ in range(3):
        changed = False
        new_quads: List[Quad] = []
        offset = 0
        for blk in cfg_blocks:
            blk_quads = quads[blk.start : blk.end + 1]
            optimized, blk_changed = _opt_block(blk_quads, stats)
            changed = changed or blk_changed
            new_quads.extend(optimized)
            blk.end = offset + len(optimized) - 1
            offset += len(optimized)
        quads = new_quads
        # rebuild cfg for next round if changed
        builder = IRBuilder()
        builder.quads = quads
        cfg_blocks = build_cfg(builder)
        if not changed:
            break

    # Write optimized IR
    builder = IRBuilder()
    builder.quads = quads
    ir_opt_path = out_dir / "ir_opt.quad"
    write_text_file(ir_opt_path, builder.render())

    # Build report
    cfg_summary = render_cfg(cfg_blocks).strip().splitlines()
    report = _render_report(pipeline, stats, len(generate_ir_quads(source_path).quads), len(quads), cfg_summary)
    report_path = out_dir / "opt_report.txt"
    write_text_file(report_path, report + "\n")

    return ir_opt_path, report_path


def _opt_block(quads: List[Quad], stats: Dict[str, PassStats]) -> Tuple[List[Quad], bool]:
    changed = False
    qlist = [q for q in quads]

    # Constant folding
    for i, q in enumerate(qlist):
        if q.op in {"ADD", "SUB", "MUL", "DIV"} and _is_const(q.arg1) and _is_const(q.arg2):
            if q.op == "DIV" and q.arg2 == "0":
                stats["Folding"].notes.append(f"Skip div-by-zero folding at {q.orig_index}")
                continue
            val = _calc(q.op, q.arg1, q.arg2)
            new_q = Quad("ASSIGN", val, "-", q.res, q.orig_index)
            if new_q != q:
                stats["Folding"].replaced.append((q.orig_index or i, _fmt_quad(q), _fmt_quad(new_q)))
                qlist[i] = new_q
                changed = True

    # Const propagation
    const_env: Dict[str, str] = {}
    for i, q in enumerate(qlist):
        if q.op in {"LABEL", "GOTO", "IF_LT", "IF_GT", "IF_EQ", "IF_NE"}:
            const_env.clear()
            continue
        a1, a2 = q.arg1, q.arg2
        if a1 in const_env:
            a1 = const_env[a1]
        if a2 in const_env:
            a2 = const_env[a2]
        new_q = Quad(q.op, a1, a2, q.res, q.orig_index)
        if new_q != q:
            stats["ConstProp"].replaced.append((q.orig_index or i, _fmt_quad(q), _fmt_quad(new_q)))
            qlist[i] = new_q
            changed = True
        # Update env on assignments
        if q.res != "-":
            if new_q.op == "ASSIGN" and _is_const(new_q.arg1):
                const_env[new_q.res] = new_q.arg1
            else:
                # kill bindings mentioning res
                const_env.pop(new_q.res, None)
                for k in list(const_env.keys()):
                    if const_env[k] == new_q.res:
                        const_env.pop(k, None)

    # Copy propagation
    copy_env: Dict[str, str] = {}
    for i, q in enumerate(qlist):
        if q.op in {"LABEL", "GOTO", "IF_LT", "IF_GT", "IF_EQ", "IF_NE"}:
            copy_env.clear()
            continue
        a1 = _resolve_copy(q.arg1, copy_env)
        a2 = _resolve_copy(q.arg2, copy_env)
        new_q = Quad(q.op, a1, a2, q.res, q.orig_index)
        if new_q != q:
            stats["CopyProp"].replaced.append((q.orig_index or i, _fmt_quad(q), _fmt_quad(new_q)))
            qlist[i] = new_q
            changed = True
        if new_q.op == "ASSIGN" and _is_var(new_q.arg1) and _is_var(new_q.res):
            copy_env[new_q.res] = _resolve_copy(new_q.arg1, copy_env)
        if new_q.res != "-":
            # kill entries involving res
            copy_env.pop(new_q.res, None)
            for k in list(copy_env.keys()):
                if copy_env[k] == new_q.res:
                    copy_env.pop(k, None)

    # DCE (only temporaries)
    live: set[str] = set()
    keep: List[Quad] = []
    for q in reversed(qlist):
        if q.op in {"LABEL", "GOTO", "IF_LT", "IF_GT", "IF_EQ", "IF_NE"}:
            keep.append(q)
            if _is_var(q.arg1):
                live.add(q.arg1)
            if _is_var(q.arg2):
                live.add(q.arg2)
            continue
        removable = q.res.startswith("t") if q.res else False
        if removable and q.res not in live:
            stats["DCE"].removed.append(q.orig_index or 0)
            changed = True
            continue
        if _is_var(q.res):
            live.discard(q.res)
        if _is_var(q.arg1):
            live.add(q.arg1)
        if _is_var(q.arg2):
            live.add(q.arg2)
        keep.append(q)
    keep.reverse()

    return keep, changed


def _resolve_copy(name: str, env: Dict[str, str]) -> str:
    seen = set()
    cur = name
    while cur in env and cur not in seen:
        seen.add(cur)
        cur = env[cur]
    return cur


def _is_const(val: str) -> bool:
    return val.lstrip("-").isdigit()


def _is_var(val: str) -> bool:
    return val not in ("-", "") and not _is_const(val)


def _calc(op: str, a: str, b: str) -> str:
    x, y = int(a), int(b)
    if op == "ADD":
        return str(x + y)
    if op == "SUB":
        return str(x - y)
    if op == "MUL":
        return str(x * y)
    if op == "DIV":
        return str(x // y)
    return a


def _fmt_quad(q: Quad) -> str:
    return f"({q.op}, {q.arg1}, {q.arg2}, {q.res})"


def _render_report(
    pipeline: List[str],
    stats: Dict[str, PassStats],
    before: int,
    after: int,
    cfg_summary: List[str],
) -> str:
    lines: List[str] = []
    lines.append("Pass pipeline: " + " -> ".join(pipeline))
    lines.append(f"Stats: quads_before={before}, quads_after={after}")
    total_removed = sum(len(s.removed) for s in stats.values())
    total_replaced = sum(len(s.replaced) for s in stats.values())
    lines.append(f"removed_count={total_removed}, replaced_count={total_replaced}")
    lines.append("")
    lines.append("Basic blocks:")
    lines.extend(f"  {line}" for line in cfg_summary)
    lines.append("")
    lines.append("Changes:")
    for name in pipeline:
        ps = stats[name]
        if ps.replaced:
            for orig, old, new in ps.replaced:
                lines.append(f"[{name}] replaced: {orig} {old} -> {new}")
        if ps.removed:
            for orig in ps.removed:
                lines.append(f"[{name}] removed: {orig}")
        if ps.notes:
            for note in ps.notes:
                lines.append(f"[{name}] note: {note}")
    if len(lines) == 0:
        lines.append("No changes.")
    return "\n".join(lines)
