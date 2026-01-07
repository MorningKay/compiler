English | [中文](README_zh.md)

# MiniLang Compiler

## Overview
This project implements a MiniLang compiler as a staged course project (M0~M9). Each milestone builds a piece of the toolchain, from lexical analysis through LALR(1) parsing, IR generation with backpatching, CFG construction, local optimizations, and stack-machine codegen. All stages can be run individually or via a single `--stage all` pipeline that writes every artifact into `out/<input_name>/`.

## Features
- Lexer → `tokens.csv`
- LALR(1) table generation → `action_goto.csv`
- Shift/reduce parser → `parse_trace.txt` with English syntax errors (Expected tokens)
- IR (quads) with backpatch → `ir.quad`
- Basic blocks + CFG → `cfg.txt`
- Block-local optimizations → `ir_opt.quad`, `opt_report.txt` (English; passes/changes/stats)
- Stack VM codegen → `target.asm`
- One-command pipeline: `--stage all` generates everything above

## Requirements
- Python 3.10+
- No mandatory third-party dependencies

## Quick Start
```bash
python -m src.main --mode cli --input examples/demo.min --stage all
```

## CLI Usage
All stages share the same entrypoint:
```bash
python -m src.main --mode cli --input <file> --stage <stage>
```
Available stages: `lexer`, `table`, `parse`, `ir`, `cfg`, `opt`, `codegen`, `all`.

## Outputs
- Outputs are written to `out/<input_basename>/`.
- Running `--stage all` produces at least:
```
out/<name>/
├─ tokens.csv
├─ action_goto.csv
├─ parse_trace.txt
├─ ir.quad
├─ cfg.txt
├─ ir_opt.quad
├─ opt_report.txt
└─ target.asm
```

## Examples
- `examples/demo.min`: canonical end-to-end sample.
- `examples/expr.min`: arithmetic expressions.
- `examples/control.min`: control flow with if/else/while.
- `examples/bad.min`: triggers parse error with English “Expected ...” message (line:col).
- `examples/opt_showcase.min`: highlights visible optimization effects.

## Troubleshooting
- `bad.min` fails at parse with: `Error line:col: Expected ..., but got ...` and stops the pipeline.
- Codegen will fail if a jump target label is missing: `Error: undefined label Lk`.
