from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set, Tuple


@dataclass(frozen=True)
class Production:
    id: int
    lhs: str
    rhs: Tuple[str, ...]


@dataclass(frozen=True)
class Grammar:
    terminals: Set[str]
    nonterminals: Set[str]
    productions: List[Production]
    start_symbol: str
    augmented_start: str


TERMINALS: Set[str] = {
    "IF",
    "ELSE",
    "WHILE",
    "AND",
    "OR",
    "NOT",
    "ID",
    "NUM",
    "ASSIGN",
    "PLUS",
    "MINUS",
    "MUL",
    "DIV",
    "EQ",
    "NE",
    "LT",
    "GT",
    "LPAREN",
    "RPAREN",
    "LBRACE",
    "RBRACE",
    "SEMI",
    "EOF",
}

NONTERMINALS: Set[str] = {
    "S'",
    "Program",
    "StmtList",
    "Stmt",
    "Matched",
    "Unmatched",
    "AssignStmt",
    "Block",
    "Expr",
    "Term",
    "Factor",
    "Bool",
    "OrExpr",
    "AndExpr",
    "NotExpr",
    "RelExpr",
}


PRODUCTIONS: List[Production] = [
    Production(1, "S'", ("Program", "EOF")),
    Production(2, "Program", ("StmtList",)),
    Production(3, "StmtList", ("Stmt", "StmtList")),
    Production(4, "StmtList", ()),
    Production(5, "Stmt", ("Matched",)),
    Production(6, "Stmt", ("Unmatched",)),
    Production(7, "Matched", ("AssignStmt",)),
    Production(8, "Matched", ("WHILE", "LPAREN", "Bool", "RPAREN", "Matched")),
    Production(9, "Matched", ("Block",)),
    Production(10, "Matched", ("IF", "LPAREN", "Bool", "RPAREN", "Matched", "ELSE", "Matched")),
    Production(11, "Unmatched", ("IF", "LPAREN", "Bool", "RPAREN", "Stmt")),
    Production(12, "Unmatched", ("IF", "LPAREN", "Bool", "RPAREN", "Matched", "ELSE", "Unmatched")),
    Production(13, "Unmatched", ("WHILE", "LPAREN", "Bool", "RPAREN", "Unmatched")),
    Production(14, "AssignStmt", ("ID", "ASSIGN", "Expr", "SEMI")),
    Production(15, "Block", ("LBRACE", "StmtList", "RBRACE")),
    Production(16, "Expr", ("Expr", "PLUS", "Term")),
    Production(17, "Expr", ("Expr", "MINUS", "Term")),
    Production(18, "Expr", ("Term",)),
    Production(19, "Term", ("Term", "MUL", "Factor")),
    Production(20, "Term", ("Term", "DIV", "Factor")),
    Production(21, "Term", ("Factor",)),
    Production(22, "Factor", ("ID",)),
    Production(23, "Factor", ("NUM",)),
    Production(24, "Factor", ("LPAREN", "Expr", "RPAREN")),
    Production(25, "Bool", ("OrExpr",)),
    Production(26, "OrExpr", ("OrExpr", "OR", "AndExpr")),
    Production(27, "OrExpr", ("AndExpr",)),
    Production(28, "AndExpr", ("AndExpr", "AND", "NotExpr")),
    Production(29, "AndExpr", ("NotExpr",)),
    Production(30, "NotExpr", ("NOT", "NotExpr")),
    Production(31, "NotExpr", ("LPAREN", "Bool", "RPAREN")),
    Production(32, "NotExpr", ("RelExpr",)),
    Production(33, "RelExpr", ("Expr", "EQ", "Expr")),
    Production(34, "RelExpr", ("Expr", "NE", "Expr")),
    Production(35, "RelExpr", ("Expr", "LT", "Expr")),
    Production(36, "RelExpr", ("Expr", "GT", "Expr")),
]

GRAMMAR = Grammar(
    terminals=TERMINALS,
    nonterminals=NONTERMINALS,
    productions=PRODUCTIONS,
    start_symbol="Program",
    augmented_start="S'",
)


def dump_productions(lines: Iterable[Production] | None = None) -> str:
    items = list(lines) if lines is not None else GRAMMAR.productions
    return "\n".join(f"{p.id}: {p.lhs} -> {' '.join(p.rhs) if p.rhs else 'ε'}" for p in items)


def dump_symbols() -> str:
    terms = ", ".join(sorted(GRAMMAR.terminals))
    nonterms = ", ".join(sorted(GRAMMAR.nonterminals))
    return f"Terminals: {terms}\nNonterminals: {nonterms}"
