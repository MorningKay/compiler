# MiniLang 编译器

[English](README.md) | 中文

## 简介
这是一个 MiniLang 编译器课程项目，按里程碑从词法到栈机代码逐步实现。各阶段可独立运行，也可用 `--stage all` 一次生成所有产物，输出统一写入 `out/<输入文件名>/`。

## 功能
- 词法分析 → `tokens.csv`
- 词法阶段输出符号表 → `symtab.txt`（标识符、首出现位置、次数）
- LALR(1) 表生成 → `action_goto.csv`
- 移入-归约语法分析 → `parse_trace.txt`，英文错误含 Expected 列表
- 四元式 IR + 回填 → `ir.quad`
- 基本块与 CFG → `cfg.txt`
- 块内优化 → `ir_opt.quad`、`opt_report.txt`（英文，含 pass/变更/统计）
- 栈机伪汇编生成 → `target.asm`
- 一键流水线：`--stage all` 生成上述全部文件

## 环境
- Python 3.10+
- 无必需第三方依赖

## 快速开始
```bash
python -m src.main --mode cli --input examples/demo.min --stage all
```

## 命令行用法
统一入口：
```bash
python -m src.main --mode cli --input <file> --stage <stage>
```
可用阶段：`lexer`、`table`、`parse`、`ir`、`cfg`、`opt`、`codegen`、`all`。

## 输出说明
- 所有产物写入 `out/<输入文件名>/`。
- 执行 `--stage all` 后的目录示例：
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

## 样例说明
- `examples/demo.min`：规范示例，贯穿全流程。
- `examples/expr.min`：算术表达式。
- `examples/control.min`：if/else/while 控制流。
- `examples/bad.min`：用于回归，parse 阶段触发英文错误（含 Expected 列表）。
- `examples/opt_showcase.min`：便于观察优化效果。

## 常见问题
- `bad.min` 在 parse 阶段会报 `Error line:col: Expected ..., but got ...`，流水线随即停止。
- 如遇跳转目标不存在，codegen 报：`Error: undefined label Lk`。
