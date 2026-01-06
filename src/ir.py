from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from . import ast as ast_nodes
from .lexer import tokenize
from .parser import parse_tokens
from .utils import UserError, write_text_file


@dataclass
class BoolCode:
    true_list: List[int]
    false_list: List[int]


class IRBuilder:
    def __init__(self) -> None:
        self.quads: List[List[str]] = []
        self.temp_counter = 0
        self.label_counter = 0

    def new_temp(self) -> str:
        self.temp_counter += 1
        return f"t{self.temp_counter}"

    def new_label(self) -> str:
        self.label_counter += 1
        return f"L{self.label_counter}"

    def emit(self, op: str, arg1: str = "-", arg2: str = "-", res: str = "-") -> int:
        idx = len(self.quads)
        self.quads.append([op, arg1, arg2, res])
        return idx

    def emit_label(self, label: str) -> int:
        return self.emit("LABEL", "-", "-", label)

    def makelist(self, idx: int) -> List[int]:
        return [idx]

    def merge(self, a: Sequence[int], b: Sequence[int]) -> List[int]:
        return list(a) + list(b)

    def backpatch(self, lst: Sequence[int], label: str) -> None:
        for idx in lst:
            if idx < 0 or idx >= len(self.quads):
                raise UserError(f"Internal error: backpatch index out of range {idx}")
            self.quads[idx][3] = label

    def render(self) -> str:
        lines = []
        for i, (op, a1, a2, res) in enumerate(self.quads):
            lines.append(f"{i}: ({op}, {a1}, {a2}, {res})")
        return "\n".join(lines) + "\n"


def generate_ir(source_path: Path, out_dir: Path) -> Path:
    tokens = tokenize(source_path)
    parse_result = parse_tokens(tokens)
    if parse_result.program is None:
        raise UserError("Internal error: parser did not return Program AST")

    builder = IRBuilder()
    _gen_program(parse_result.program, builder)

    out_path = out_dir / "ir.quad"
    write_text_file(out_path, builder.render())
    return out_path


def _gen_program(node: ast_nodes.Program, b: IRBuilder) -> None:
    for stmt in node.stmts:
        _gen_stmt(stmt, b)


def _gen_stmt(stmt: ast_nodes.Stmt, b: IRBuilder) -> None:
    if isinstance(stmt, ast_nodes.Assign):
        place = _gen_expr(stmt.expr, b)
        b.emit("ASSIGN", place, "-", stmt.name)
    elif isinstance(stmt, ast_nodes.Block):
        for s in stmt.stmts:
            _gen_stmt(s, b)
    elif isinstance(stmt, ast_nodes.If):
        cond = _gen_bool(stmt.cond, b)
        then_label = b.new_label()
        b.backpatch(cond.true_list, then_label)
        b.emit_label(then_label)
        _gen_stmt(stmt.then_branch, b)
        if stmt.else_branch is not None:
            end_label = b.new_label()
            b.emit("GOTO", "-", "-", end_label)
            else_label = b.new_label()
            b.backpatch(cond.false_list, else_label)
            b.emit_label(else_label)
            _gen_stmt(stmt.else_branch, b)
            b.emit_label(end_label)
        else:
            end_label = b.new_label()
            b.backpatch(cond.false_list, end_label)
            b.emit_label(end_label)
    elif isinstance(stmt, ast_nodes.While):
        start_label = b.new_label()
        b.emit_label(start_label)
        cond = _gen_bool(stmt.cond, b)
        body_label = b.new_label()
        b.backpatch(cond.true_list, body_label)
        b.emit_label(body_label)
        _gen_stmt(stmt.body, b)
        b.emit("GOTO", "-", "-", start_label)
        end_label = b.new_label()
        b.backpatch(cond.false_list, end_label)
        b.emit_label(end_label)
    else:
        raise UserError(f"Internal error: unsupported stmt {stmt}")


def _gen_expr(expr: ast_nodes.Expr, b: IRBuilder) -> str:
    if isinstance(expr, ast_nodes.Id):
        return expr.name
    if isinstance(expr, ast_nodes.Num):
        return expr.value
    if isinstance(expr, ast_nodes.BinOp):
        left = _gen_expr(expr.left, b)
        right = _gen_expr(expr.right, b)
        res = b.new_temp()
        b.emit(expr.op, left, right, res)
        return res
    raise UserError(f"Internal error: unsupported expr {expr}")


def _gen_bool(node: ast_nodes.BoolExpr, b: IRBuilder) -> BoolCode:
    if isinstance(node, ast_nodes.RelOp):
        op = node.op
        idx_true = b.emit(op, _gen_expr(node.left, b), _gen_expr(node.right, b), "-")
        idx_false = b.emit("GOTO", "-", "-", "-")
        return BoolCode(true_list=b.makelist(idx_true), false_list=b.makelist(idx_false))
    if isinstance(node, ast_nodes.LogicOp):
        if node.op == "OR":
            left = _gen_bool(node.left, b)
            join_label = b.new_label()
            b.backpatch(left.false_list, join_label)
            b.emit_label(join_label)
            right = _gen_bool(node.right, b)
            return BoolCode(
                true_list=b.merge(left.true_list, right.true_list),
                false_list=right.false_list,
            )
        if node.op == "AND":
            left = _gen_bool(node.left, b)
            join_label = b.new_label()
            b.backpatch(left.true_list, join_label)
            b.emit_label(join_label)
            right = _gen_bool(node.right, b)
            return BoolCode(
                true_list=right.true_list,
                false_list=b.merge(left.false_list, right.false_list),
            )
        raise UserError(f"Internal error: unknown logic op {node.op}")
    if isinstance(node, ast_nodes.Not):
        inner = _gen_bool(node.expr, b)
        return BoolCode(true_list=inner.false_list, false_list=inner.true_list)
    raise UserError(f"Internal error: unsupported bool expr {node}")
