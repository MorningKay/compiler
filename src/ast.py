from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


# Expressions
@dataclass
class Expr:
    pass


@dataclass
class Id(Expr):
    name: str


@dataclass
class Num(Expr):
    value: str


@dataclass
class BinOp(Expr):
    op: str  # ADD/SUB/MUL/DIV
    left: Expr
    right: Expr


@dataclass
class RelOp:
    op: str  # IF_LT/IF_GT/IF_EQ/IF_NE
    left: Expr
    right: Expr


@dataclass
class LogicOp:
    op: str  # AND/OR
    left: "BoolExpr"
    right: "BoolExpr"


@dataclass
class Not:
    expr: "BoolExpr"


BoolExpr = RelOp | LogicOp | Not


# Statements
@dataclass
class Stmt:
    pass


@dataclass
class Assign(Stmt):
    name: str
    expr: Expr


@dataclass
class Block(Stmt):
    stmts: List[Stmt]


@dataclass
class If(Stmt):
    cond: BoolExpr
    then_branch: Stmt
    else_branch: Optional[Stmt]


@dataclass
class While(Stmt):
    cond: BoolExpr
    body: Stmt


@dataclass
class Program:
    stmts: List[Stmt]
