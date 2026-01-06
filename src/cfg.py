from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from .ir import IRBuilder, Quad
from .utils import UserError


@dataclass
class BasicBlock:
    id: int
    start: int
    end: int
    succs: List[int]
    quads: List[Quad]


def build_cfg(builder: IRBuilder) -> List[BasicBlock]:
    quads = builder.quads
    if not quads:
        return []

    label_to_idx: Dict[str, int] = {}
    for idx, q in enumerate(quads):
        if q.op == "LABEL":
            label_to_idx[q.res] = idx

    leaders: Set[int] = set()
    leaders.add(0)
    for idx, q in enumerate(quads):
        if q.op == "LABEL":
            leaders.add(idx)
        if q.op in {"GOTO", "IF_LT", "IF_GT", "IF_EQ", "IF_NE"}:
            if idx + 1 < len(quads):
                leaders.add(idx + 1)
            if q.res != "-" and q.res in label_to_idx:
                leaders.add(label_to_idx[q.res])
            elif q.op in {"GOTO", "IF_LT", "IF_GT", "IF_EQ", "IF_NE"} and q.res != "-":
                raise UserError(f"Internal error: label {q.res} not found")

    leader_list = sorted(leaders)
    block_ranges: List[range] = []
    for i, start in enumerate(leader_list):
        end = leader_list[i + 1] - 1 if i + 1 < len(leader_list) else len(quads) - 1
        block_ranges.append(range(start, end + 1))

    quad_to_block: Dict[int, int] = {}
    blocks: List[BasicBlock] = []
    for bid, rng in enumerate(block_ranges):
        for idx in rng:
            quad_to_block[idx] = bid
        blocks.append(
            BasicBlock(
                id=bid, start=rng.start, end=rng.stop - 1, succs=[], quads=[quads[i] for i in rng]
            )
        )

    for blk in blocks:
        last = blk.quads[-1]
        if last.op in {"IF_LT", "IF_GT", "IF_EQ", "IF_NE"}:
            succs = []
            if last.res not in label_to_idx:
                raise UserError(f"Internal error: label {last.res} not found")
            target_block = quad_to_block[label_to_idx[last.res]]
            succs.append(target_block)
            fall = blk.id + 1
            if fall < len(blocks):
                succs.append(fall)
            blk.succs = sorted(set(succs))
        elif last.op == "GOTO":
            if last.res not in label_to_idx:
                raise UserError(f"Internal error: label {last.res} not found")
            blk.succs = [quad_to_block[label_to_idx[last.res]]]
        else:
            fall = blk.id + 1
            blk.succs = [fall] if fall < len(blocks) else []

    return blocks


def render_cfg(blocks: List[BasicBlock]) -> str:
    lines: List[str] = []
    for blk in blocks:
        succs = ",".join(f"B{s}" for s in blk.succs)
        lines.append(f"B{blk.id}: {blk.start}..{blk.end} succs=[{succs}]")
        for idx, q in enumerate(blk.quads, start=blk.start):
            lines.append(f"  {idx}: ({q.op}, {q.arg1}, {q.arg2}, {q.res})")
    return "\n".join(lines) + "\n"
