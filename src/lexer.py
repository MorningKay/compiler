from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List

from .utils import UserError, ensure_input_file


class TokenType(str, Enum):
    ID = "ID"
    NUM = "NUM"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    ASSIGN = "ASSIGN"
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    GT = "GT"
    PLUS = "PLUS"
    MINUS = "MINUS"
    MUL = "MUL"
    DIV = "DIV"
    SEMI = "SEMI"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    EOF = "EOF"


KEYWORDS = {
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}


@dataclass
class Token:
    index: int
    type: TokenType
    lexeme: str
    line: int
    col: int


def tokenize(path: str | Path) -> List[Token]:
    source_path = ensure_input_file(path)
    text = source_path.read_text(encoding="utf-8")
    tokens: List[Token] = []
    i = 0
    line = 1
    col = 1

    while i < len(text):
        ch = text[i]

        # Whitespace and newlines
        if ch in " \t\r":
            i += 1
            col += 1
            continue
        if ch == "\n":
            i += 1
            line += 1
            col = 1
            continue

        # Line comment
        if ch == "/" and _peek(text, i) == "/":
            while i < len(text) and text[i] != "\n":
                i += 1
                col += 1
            continue

        start_line, start_col = line, col

        # Identifiers / keywords
        if ch.isalpha() or ch == "_":
            start = i
            while i < len(text) and (text[i].isalnum() or text[i] == "_"):
                i += 1
                col += 1
            lexeme = text[start:i]
            ttype = KEYWORDS.get(lexeme, TokenType.ID)
            tokens.append(Token(len(tokens), ttype, lexeme, start_line, start_col))
            continue

        # Numbers
        if ch.isdigit():
            start = i
            while i < len(text) and text[i].isdigit():
                i += 1
                col += 1
            lexeme = text[start:i]
            tokens.append(Token(len(tokens), TokenType.NUM, lexeme, start_line, start_col))
            continue

        # Two-char operators
        two_char = text[i : i + 2]
        if two_char in ("==", "!="):
            # Reject triple operators like "===" or "!=="
            if i + 2 < len(text) and text[i + 2] == "=":
                raise UserError(
                    f"Error {start_line}:{start_col + 2}: Expected valid token, but got CHAR('=')"
                )
            tt = TokenType.EQ if two_char == "==" else TokenType.NE
            tokens.append(Token(len(tokens), tt, two_char, start_line, start_col))
            i += 2
            col += 2
            continue

        # Single-char tokens
        single_map = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.MUL,
            "/": TokenType.DIV,
            "=": TokenType.ASSIGN,
            "<": TokenType.LT,
            ">": TokenType.GT,
            ";": TokenType.SEMI,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
        }
        if ch in single_map:
            tokens.append(Token(len(tokens), single_map[ch], ch, start_line, start_col))
            i += 1
            col += 1
            continue

        # Unknown character
        raise UserError(
            f"Error {start_line}:{start_col}: Expected valid token, but got CHAR('{ch}')"
        )

    return tokens


def _peek(text: str, idx: int) -> str:
    return text[idx + 1] if idx + 1 < len(text) else ""
