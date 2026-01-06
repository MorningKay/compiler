from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .grammar import GRAMMAR
from .lalr import PROD_BY_ID, generate_tables
from .lexer import Token, TokenType
from .utils import UserError


@dataclass
class ParseStep:
    step: int
    state_stack: List[int]
    symbol_stack: List[str]
    remaining: List[str]
    action: str

    def format(self) -> str:
        states_repr = "[" + " ".join(str(s) for s in self.state_stack) + "]"
        symbols_repr = "[" + " ".join(self.symbol_stack) + "]"
        input_repr = "[" + " ".join(self.remaining) + "]"
        return f"{self.step}\t{states_repr}\t{symbols_repr}\t{input_repr}\t{self.action}"


def _append_eof(tokens: List[Token]) -> List[Token]:
    """Return a new token list with an EOF token appended."""
    if tokens:
        last = tokens[-1]
        line, col = last.line, last.col + len(last.lexeme)
    else:
        line, col = 1, 1
    eof_token = Token(index=len(tokens), type=TokenType.EOF, lexeme="", line=line, col=col)
    return tokens + [eof_token]


def parse_tokens(tokens: List[Token]) -> str:
    """Run shift/reduce parsing and return the parse trace as text."""
    states, terminals, nonterminals, action, goto_table = generate_tables(verbose=False)
    tokens = _append_eof(tokens)

    state_stack: List[int] = [0]
    symbol_stack: List[str] = []
    steps: List[ParseStep] = []
    pos = 0
    step_idx = 0

    while True:
        state = state_stack[-1]
        lookahead = tokens[pos]
        la_type = lookahead.type.value
        act = action.get(state, {}).get(la_type, "")

        remaining_display = []
        for t in tokens[pos:]:
            if t.type == TokenType.EOF:
                remaining_display.append("EOF")
            elif t.lexeme:
                remaining_display.append(f"{t.type.value}({t.lexeme})")
            else:
                remaining_display.append(t.type.value)

        recorded_action = act if act else "error"
        steps.append(
            ParseStep(
                step=step_idx,
                state_stack=list(state_stack),
                symbol_stack=list(symbol_stack),
                remaining=remaining_display,
                action=recorded_action,
            )
        )
        step_idx += 1

        if not act:
            expected = sorted(action.get(state, {}).keys())
            expected_str = ", ".join(expected) if expected else "<none>"
            raise UserError(
                f"Error {lookahead.line}:{lookahead.col}: Expected {expected_str}, "
                f"but got {la_type}({lookahead.lexeme})"
            )

        if act == "acc":
            break

        if act.startswith("s"):
            new_state = int(act[1:])
            symbol_stack.append(la_type)
            state_stack.append(new_state)
            if lookahead.type != TokenType.EOF:
                pos += 1
            continue

        if act.startswith("r"):
            prod_id = int(act[1:])
            prod = PROD_BY_ID[prod_id]
            rhs_len = len(prod.rhs)
            for _ in range(rhs_len):
                if state_stack:
                    state_stack.pop()
                if symbol_stack:
                    symbol_stack.pop()
            goto_state = goto_table.get(state_stack[-1], {}).get(prod.lhs)
            if goto_state is None:
                raise UserError(
                    f"Internal error: goto missing for state {state_stack[-1]} on {prod.lhs}"
                )
            symbol_stack.append(prod.lhs)
            state_stack.append(goto_state)
            continue

        raise UserError(f"Error: unknown parser action '{act}'")

    lines = ["step\tstates\tsymbols\tinput\taction"]
    lines.extend(step.format() for step in steps)
    return "\n".join(lines) + "\n"
