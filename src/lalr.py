from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, Set, Tuple

from .grammar import GRAMMAR, Production
from .utils import UserError


@dataclass(frozen=True)
class LR1Item:
    prod_id: int
    dot: int
    lookahead: frozenset[str]

    def core(self) -> Tuple[int, int]:
        return (self.prod_id, self.dot)


@dataclass
class LRState:
    id: int
    items: frozenset[LR1Item]
    transitions: Dict[str, int]
    sources: List[int] | None = None


def _production_by_id() -> Dict[int, Production]:
    return {p.id: p for p in GRAMMAR.productions}


PROD_BY_ID = _production_by_id()
PRODS_BY_LHS: Mapping[str, List[Production]] = {}
for p in GRAMMAR.productions:
    PRODS_BY_LHS.setdefault(p.lhs, []).append(p)


def _compute_first_sets() -> Dict[str, Set[str]]:
    first: Dict[str, Set[str]] = {}
    for t in GRAMMAR.terminals:
        first[t] = {t}
    for nt in GRAMMAR.nonterminals:
        first[nt] = set()

    changed = True
    while changed:
        changed = False
        for prod in GRAMMAR.productions:
            lhs_first = first[prod.lhs]
            before = len(lhs_first)
            if not prod.rhs:
                lhs_first.add("")
            else:
                all_nullable = True
                for sym in prod.rhs:
                    sym_first = first[sym]
                    lhs_first.update(sym_first - {""})
                    if "" not in sym_first:
                        all_nullable = False
                        break
                if all_nullable:
                    lhs_first.add("")
            if len(lhs_first) != before:
                changed = True
    return first


FIRST: Dict[str, Set[str]] = _compute_first_sets()


def _compute_follow_sets() -> Dict[str, Set[str]]:
    follow: Dict[str, Set[str]] = {nt: set() for nt in GRAMMAR.nonterminals}
    follow[GRAMMAR.start_symbol].add("EOF")

    changed = True
    while changed:
        changed = False
        for prod in GRAMMAR.productions:
            trailer = set(follow[prod.lhs])
            for symbol in reversed(prod.rhs):
                if symbol in GRAMMAR.nonterminals:
                    before = len(follow[symbol])
                    follow[symbol].update(trailer)
                    if "" in FIRST[symbol]:
                        trailer = trailer.union(FIRST[symbol] - {""})
                    else:
                        trailer = FIRST[symbol] - {""}
                    if len(follow[symbol]) != before:
                        changed = True
                else:
                    trailer = FIRST[symbol]
            if not prod.rhs:
                continue
    return follow


FOLLOW: Dict[str, Set[str]] = _compute_follow_sets()


def first_of_sequence(symbols: Iterable[str]) -> Tuple[Set[str], bool]:
    """Return (first set, derives_epsilon) for a sequence of symbols."""
    first: Set[str] = set()
    derives_epsilon = True
    for sym in symbols:
        sym_first = FIRST[sym]
        first.update(sym_first - {""})
        if "" not in sym_first:
            derives_epsilon = False
            break
    if derives_epsilon:
        first.add("")
    return first, derives_epsilon


def closure(items: Set[LR1Item]) -> Set[LR1Item]:
    """Compute LR(1) closure while merging lookahead sets per core."""
    item_map: Dict[Tuple[int, int], Set[str]] = {}
    for it in items:
        item_map.setdefault(it.core(), set()).update(it.lookahead)

    queue: List[Tuple[int, int]] = sorted(item_map.keys())
    while queue:
        core = queue.pop(0)
        lookaheads = item_map[core]
        prod = PROD_BY_ID[core[0]]
        dot = core[1]
        if dot >= len(prod.rhs):
            continue
        symbol = prod.rhs[dot]
        if symbol in GRAMMAR.terminals:
            continue
        beta = prod.rhs[dot + 1 :]
        needed: Set[str] = set()
        for la in sorted(lookaheads):
            first_set, _ = first_of_sequence(list(beta) + [la])
            needed.update(first_set - {""})
        for p in sorted(PRODS_BY_LHS.get(symbol, []), key=lambda pr: pr.id):
            key = (p.id, 0)
            prev = item_map.get(key)
            if prev is None:
                item_map[key] = set(needed)
                queue.append(key)
            else:
                new_las = needed - prev
                if new_las:
                    prev.update(new_las)
                    queue.append(key)

    return {
        LR1Item(prod_id=pid, dot=dot, lookahead=frozenset(las))
        for (pid, dot), las in item_map.items()
    }


def goto(items: Set[LR1Item], symbol: str) -> Set[LR1Item]:
    moved: Dict[Tuple[int, int], Set[str]] = {}
    for item in sorted(items, key=lambda it: (it.prod_id, it.dot, sorted(it.lookahead))):
        prod = PROD_BY_ID[item.prod_id]
        if item.dot < len(prod.rhs) and prod.rhs[item.dot] == symbol:
            key = (item.prod_id, item.dot + 1)
            moved.setdefault(key, set()).update(item.lookahead)
    if not moved:
        return set()
    shifted = {LR1Item(prod_id=pid, dot=dot, lookahead=frozenset(las)) for (pid, dot), las in moved.items()}
    return closure(shifted)


def canonical_collection() -> List[LRState]:
    start_prod = PROD_BY_ID[1]  # S' -> Program EOF
    start_item = LR1Item(prod_id=start_prod.id, dot=0, lookahead=frozenset({"EOF"}))
    start_state_items = frozenset(closure({start_item}))

    states: List[LRState] = [LRState(id=0, items=start_state_items, transitions={}, sources=[0])]
    state_index: Dict[frozenset[LR1Item], int] = {start_state_items: 0}
    i = 0
    terminal_list = sorted(t for t in GRAMMAR.terminals if t != "EOF") + ["EOF"]
    nonterminal_list = sorted(GRAMMAR.nonterminals)
    symbols = terminal_list + nonterminal_list
    while i < len(states):
        state = states[i]
        i += 1
        for sym in symbols:
            next_items = goto(set(state.items), sym)
            if not next_items:
                continue
            frozen_items = frozenset(next_items)
            if frozen_items not in state_index:
                idx = len(states)
                states.append(LRState(id=idx, items=frozen_items, transitions={}, sources=[idx]))
                state_index[frozen_items] = idx
            else:
                idx = state_index[frozen_items]
            state.transitions[sym] = idx
    return states


@dataclass
class LALRState:
    id: int
    items: frozenset[LR1Item]
    transitions: Dict[str, int]
    sources: List[int]


def merge_to_lalr(lr_states: List[LRState]) -> List[LALRState]:
    def core_of(state: LRState) -> frozenset[Tuple[int, int]]:
        return frozenset((item.prod_id, item.dot) for item in state.items)

    # Pass A: assign core ids deterministically
    core_to_id: Dict[frozenset[Tuple[int, int]], int] = {}
    state_core: List[int] = []
    for st in lr_states:
        core = core_of(st)
        cid = core_to_id.setdefault(core, len(core_to_id))
        state_core.append(cid)

    merged_items: List[MutableMapping[Tuple[int, int], Set[str]]] = [
        {} for _ in range(len(core_to_id))
    ]
    merged_trans: List[Dict[str, int]] = [{} for _ in range(len(core_to_id))]
    core_sources: List[List[int]] = [[] for _ in range(len(core_to_id))]

    # Pass B: union lookaheads and merge transitions with checks
    for idx, st in enumerate(lr_states):
        cid = state_core[idx]
        core_sources[cid].append(idx)
        store = merged_items[cid]
        for item in st.items:
            key = (item.prod_id, item.dot)
            store.setdefault(key, set()).update(item.lookahead)
        for sym, tgt in st.transitions.items():
            tid = state_core[tgt]
            prev = merged_trans[cid].get(sym)
            if prev is not None and prev != tid:
                raise UserError(
                    f"Transition merge conflict: core {cid} on symbol {sym} maps to {prev} vs {tid}; "
                    f"LR states {core_sources[cid]}"
                )
            merged_trans[cid][sym] = tid

    lalr_states: List[LALRState] = []
    for cid in range(len(core_to_id)):
        items_set: Set[LR1Item] = set()
        for (prod_id, dot), las in merged_items[cid].items():
            items_set.add(LR1Item(prod_id=prod_id, dot=dot, lookahead=frozenset(las)))
        lalr_states.append(
            LALRState(
                id=cid,
                items=frozenset(items_set),
                transitions=merged_trans[cid],
                sources=sorted(core_sources[cid]),
            )
        )
    return lalr_states


def generate_tables(
    verbose: bool = True,
) -> Tuple[List[LALRState], List[str], List[str], Dict[int, Dict[str, str]], Dict[int, Dict[str, int]]]:
    lr_states = canonical_collection()
    terminals = sorted(t for t in GRAMMAR.terminals if t != "EOF")
    terminals.append("EOF")
    nonterminals = sorted(nt for nt in GRAMMAR.nonterminals if nt != "S'")

    # Diagnose canonical LR(1) conflicts without applying policies
    lr_conflicts = detect_conflicts(lr_states, terminals, nonterminals, label="LR(1)")
    if verbose:
        if lr_conflicts:
            print(f"LR(1) conflicts: {len(lr_conflicts)}", file=sys.stderr)
            for msg in lr_conflicts:
                print(msg, file=sys.stderr)
        else:
            print("LR(1) conflicts: 0", file=sys.stderr)

    lalr_states = merge_to_lalr(lr_states)
    lalr_conflicts = detect_conflicts(lalr_states, terminals, nonterminals, label="LALR(1)")
    if verbose:
        if lalr_conflicts:
            print(f"LALR(1) conflicts: {len(lalr_conflicts)}", file=sys.stderr)
            for msg in lalr_conflicts:
                print(msg, file=sys.stderr)
        else:
            print("LALR(1) conflicts: 0", file=sys.stderr)

    # Build final tables (may apply dangling-else policy)
    try:
        action, goto_table = build_action_goto(lalr_states, terminals, nonterminals, is_lalr=True)
    except UserError as err:
        raise UserError(
            f"{err}\nCanonical LR(1) table had no conflicts; conflict introduced during LALR merge."
        ) from err

    return lalr_states, terminals, nonterminals, action, goto_table


def detect_conflicts(
    states: List[LRState] | List[LALRState],
    terminals: List[str],
    nonterminals: List[str],
    label: str,
) -> List[str]:
    """Build ACTION/GOTO without policy resolution; return conflict messages."""
    action: Dict[int, Dict[str, str]] = {}
    goto_table: Dict[int, Dict[str, int]] = {}
    conflicts: List[str] = []

    def sid(idx: int, st: object) -> int:
        return st.id if hasattr(st, "id") else idx

    for idx, st in enumerate(states):
        action[sid(idx, st)] = {}
        goto_table[sid(idx, st)] = {}

    for idx, st in enumerate(states):
        cur_id = sid(idx, st)
        for sym, tgt in st.transitions.items():
            if sym in GRAMMAR.terminals:
                _record_action(action, cur_id, sym, f"s{tgt}", st, None, conflicts, label)
            elif sym in GRAMMAR.nonterminals:
                goto_table[cur_id][sym] = tgt
        for item in st.items:
            prod = PROD_BY_ID[item.prod_id]
            if item.dot == len(prod.rhs):
                for la in sorted(item.lookahead):
                    if prod.lhs == GRAMMAR.augmented_start:
                        if la == "EOF":
                            _record_action(action, cur_id, "EOF", "acc", st, item, conflicts, label)
                        continue
                    _record_action(action, cur_id, la, f"r{prod.id}", st, item, conflicts, label)
    return conflicts


def build_action_goto(
    states: List[LRState] | List[LALRState],
    terminals: List[str],
    nonterminals: List[str],
    is_lalr: bool,
) -> Tuple[Dict[int, Dict[str, str]], Dict[int, Dict[str, int]]]:
    action: Dict[int, Dict[str, str]] = {}
    goto_table: Dict[int, Dict[str, int]] = {}

    def sid(idx: int, st: object) -> int:
        return st.id if hasattr(st, "id") else idx

    for idx, st in enumerate(states):
        action[sid(idx, st)] = {}
        goto_table[sid(idx, st)] = {}

    for idx, st in enumerate(states):
        cur_id = sid(idx, st)
        # shifts
        for sym, tgt in st.transitions.items():
            if sym in GRAMMAR.terminals:
                _set_action(action, cur_id, sym, f"s{tgt}", st, None)
            elif sym in GRAMMAR.nonterminals:
                goto_table[cur_id][sym] = tgt
        # reductions
        for item in st.items:
            prod = PROD_BY_ID[item.prod_id]
            if item.dot == len(prod.rhs):
                for la in sorted(item.lookahead):
                    if prod.lhs == GRAMMAR.augmented_start:
                        if la == "EOF":
                            _set_action(action, cur_id, "EOF", "acc", st, item)
                        continue
                    _set_action(action, cur_id, la, f"r{prod.id}", st, item)

    return action, goto_table


def _set_action(
    table: Dict[int, Dict[str, str]],
    state_id: int,
    terminal: str,
    value: str,
    state: object,
    item: LR1Item | None = None,
) -> None:
    existing = table[state_id].get(terminal)
    if existing and existing != value:
        details = _describe_conflict(state, terminal, existing, value, item)
        raise UserError(details)
    table[state_id][terminal] = value


def _record_action(
    table: Dict[int, Dict[str, str]],
    state_id: int,
    terminal: str,
    value: str,
    state: object,
    item: LR1Item | None,
    conflicts: List[str],
    label: str,
) -> None:
    existing = table[state_id].get(terminal)
    if existing and existing != value:
        conflicts.append(f"[{label}] {_describe_conflict(state, terminal, existing, value, item)}")
        return
    table[state_id][terminal] = value


def _describe_conflict(
    state: object, terminal: str, existing: str, new: str, item: LR1Item | None
) -> str:
    sid = state.id if hasattr(state, "id") else "?"
    sources = getattr(state, "sources", [])
    parts = [
        f"Conflict at state {sid} on terminal {terminal}: {existing} vs {new}",
        f"  sources (LR states): {sources}",
    ]
    if item:
        prod = PROD_BY_ID[item.prod_id]
        rhs = list(prod.rhs)
        rhs.insert(item.dot, "·")
        parts.append(f"  item: [{prod.lhs} -> {' '.join(rhs)}, {sorted(item.lookahead)}]")
    parts.append("  all items:")
    def _la_sort(it: LR1Item) -> Tuple[int, int, Tuple[str, ...]]:
        return (it.prod_id, it.dot, tuple(sorted(it.lookahead)))
    for it in sorted(state.items, key=_la_sort):
        prod = PROD_BY_ID[it.prod_id]
        rhs = list(prod.rhs)
        rhs.insert(it.dot, "·")
        parts.append(f"    [{prod.id}] {prod.lhs} -> {' '.join(rhs)}, {sorted(it.lookahead)}]")
    return "\n".join(parts)
