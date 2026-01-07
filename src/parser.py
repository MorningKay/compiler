from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .grammar import GRAMMAR
from .lalr import PROD_BY_ID, generate_tables
from .lexer import Token, TokenType
from .utils import UserError
from . import ast as ast_nodes


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


@dataclass
class ParseResult:
    trace: str
    program: Optional[ast_nodes.Program]


def parse_tokens(tokens: List[Token]) -> ParseResult:
    """Run shift/reduce parsing and return trace plus Program AST (if accept)."""
    states, terminals, nonterminals, action, goto_table = generate_tables(verbose=False)
    tokens = _append_eof(tokens)

    state_stack: List[int] = [0]
    symbol_stack: List[str] = []
    value_stack: List[object] = []
    steps: List[ParseStep] = []
    pos = 0
    step_idx = 0
    program: Optional[ast_nodes.Program] = None

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
            value_stack.append(lookahead)
            state_stack.append(new_state)
            if lookahead.type != TokenType.EOF:
                pos += 1
            continue

        if act.startswith("r"):
            prod_id = int(act[1:])
            prod = PROD_BY_ID[prod_id]
            rhs_len = len(prod.rhs)
            rhs_vals: List[object] = []
            if rhs_len:
                rhs_vals = value_stack[-rhs_len:]
                value_stack = value_stack[:-rhs_len]
                state_stack = state_stack[:-rhs_len]
                symbol_stack = symbol_stack[:-rhs_len]
            goto_state = goto_table.get(state_stack[-1], {}).get(prod.lhs)
            if goto_state is None:
                raise UserError(
                    f"Internal error: goto missing for state {state_stack[-1]} on {prod.lhs}"
                )
            symbol_stack.append(prod.lhs)
            state_stack.append(goto_state)
            node = _build_node(prod_id, rhs_vals)
            if node is not None:
                value_stack.append(node)
            continue

        raise UserError(f"Error: unknown parser action '{act}'")

    lines = ["step\tstates\tsymbols\tinput\taction"]
    lines.extend(step.format() for step in steps)
    if value_stack:
        for v in reversed(value_stack):
            if isinstance(v, ast_nodes.Program):
                program = v
                break
    return ParseResult(trace="\n".join(lines) + "\n", program=program)


def _build_node(prod_id: int, vals: List[object]) -> object | None:
    """Map production id to AST node construction."""
    if prod_id == 1:
        # S' -> Program EOF
        return vals[0]
    if prod_id == 2:
        # Program -> StmtList
        return ast_nodes.Program(stmts=vals[0])
    if prod_id == 3:
        # StmtList -> Stmt StmtList
        stmt: ast_nodes.Stmt = vals[0]  # type: ignore[assignment]
        rest: List[ast_nodes.Stmt] = vals[1]  # type: ignore[assignment]
        return [stmt] + rest
    if prod_id == 4:
        # StmtList -> ε
        return []
    if prod_id == 5 or prod_id == 6:
        # Stmt -> Matched / Stmt -> Unmatched
        return vals[0]
    if prod_id == 7:
        # Matched -> AssignStmt
        return vals[0]
    if prod_id == 8:
        # Matched -> WHILE LPAREN Bool RPAREN Matched
        cond = vals[2]  # type: ignore[assignment]
        body = vals[4]  # type: ignore[assignment]
        return ast_nodes.While(cond=cond, body=body)
    if prod_id == 9:
        # Matched -> Block
        return vals[0]
    if prod_id == 10:
        # Matched -> IF LPAREN Bool RPAREN Matched ELSE Matched
        cond = vals[2]  # type: ignore[assignment]
        then_stmt = vals[4]  # type: ignore[assignment]
        else_stmt = vals[6]  # type: ignore[assignment]
        return ast_nodes.If(cond=cond, then_branch=then_stmt, else_branch=else_stmt)
    if prod_id == 11:
        # Unmatched -> IF LPAREN Bool RPAREN Stmt
        cond = vals[2]  # type: ignore[assignment]
        then_stmt = vals[4]  # type: ignore[assignment]
        return ast_nodes.If(cond=cond, then_branch=then_stmt, else_branch=None)
    if prod_id == 12:
        # Unmatched -> IF LPAREN Bool RPAREN Matched ELSE Unmatched
        cond = vals[2]  # type: ignore[assignment]
        then_stmt = vals[4]  # type: ignore[assignment]
        else_stmt = vals[6]  # type: ignore[assignment]
        return ast_nodes.If(cond=cond, then_branch=then_stmt, else_branch=else_stmt)
    if prod_id == 13:
        # Unmatched -> WHILE LPAREN Bool RPAREN Unmatched
        cond = vals[2]  # type: ignore[assignment]
        body = vals[4]  # type: ignore[assignment]
        return ast_nodes.While(cond=cond, body=body)
    if prod_id == 14:
        # AssignStmt -> ID ASSIGN Expr SEMI
        ident_tok: Token = vals[0]  # type: ignore[assignment]
        expr = vals[2]  # type: ignore[assignment]
        return ast_nodes.Assign(name=ident_tok.lexeme, expr=expr)
    if prod_id == 15:
        # Block -> LBRACE StmtList RBRACE
        stmts: List[ast_nodes.Stmt] = vals[1]  # type: ignore[assignment]
        return ast_nodes.Block(stmts=stmts)
    if prod_id == 16 or prod_id == 17:
        # Expr -> Expr PLUS/MINUS Term
        left = vals[0]  # type: ignore[assignment]
        right = vals[2]  # type: ignore[assignment]
        op = "ADD" if prod_id == 16 else "SUB"
        return ast_nodes.BinOp(op=op, left=left, right=right)
    if prod_id == 18:
        # Expr -> Term
        return vals[0]
    if prod_id == 19 or prod_id == 20:
        # Term -> Term MUL/DIV Factor
        left = vals[0]  # type: ignore[assignment]
        right = vals[2]  # type: ignore[assignment]
        op = "MUL" if prod_id == 19 else "DIV"
        return ast_nodes.BinOp(op=op, left=left, right=right)
    if prod_id == 21:
        # Term -> Factor
        return vals[0]
    if prod_id == 22:
        # Factor -> ID
        tok: Token = vals[0]  # type: ignore[assignment]
        return ast_nodes.Id(name=tok.lexeme)
    if prod_id == 23:
        # Factor -> NUM
        tok: Token = vals[0]  # type: ignore[assignment]
        return ast_nodes.Num(value=tok.lexeme)
    if prod_id == 24:
        # Factor -> LPAREN Expr RPAREN
        return vals[1]
    if prod_id == 25:
        # Bool -> OrExpr
        return vals[0]
    if prod_id == 26:
        # OrExpr -> OrExpr OR AndExpr
        left = vals[0]  # type: ignore[assignment]
        right = vals[2]  # type: ignore[assignment]
        return ast_nodes.LogicOp(op="OR", left=left, right=right)
    if prod_id == 27:
        # OrExpr -> AndExpr
        return vals[0]
    if prod_id == 28:
        # AndExpr -> AndExpr AND NotExpr
        left = vals[0]  # type: ignore[assignment]
        right = vals[2]  # type: ignore[assignment]
        return ast_nodes.LogicOp(op="AND", left=left, right=right)
    if prod_id == 29:
        # AndExpr -> NotExpr
        return vals[0]
    if prod_id == 30:
        # NotExpr -> NOT NotExpr
        expr = vals[1]  # type: ignore[assignment]
        return ast_nodes.Not(expr=expr)
    if prod_id == 31:
        # NotExpr -> LPAREN Bool RPAREN
        return vals[1]
    if prod_id == 32:
        # NotExpr -> RelExpr
        return vals[0]
    if prod_id == 33:
        op = "IF_EQ"
    elif prod_id == 34:
        op = "IF_NE"
    elif prod_id == 35:
        op = "IF_LT"
    elif prod_id == 36:
        op = "IF_GT"
    elif prod_id == 37:
        op = "IF_LE"
    elif prod_id == 38:
        op = "IF_GE"
    else:
        return None
    if prod_id in (33, 34, 35, 36, 37, 38):
        left = vals[0]  # type: ignore[assignment]
        right = vals[2]  # type: ignore[assignment]
        return ast_nodes.RelOp(op=op, left=left, right=right)
    return None
