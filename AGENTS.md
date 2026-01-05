# AGENTS.md — MiniLang Coding Agent 执行指南（How to Work）

> 本文件是给 Coding Agent（Codex）用的“执行手册”，专注：强约束、可执行命令、输出契约、代码风格、验收清单。
> 任务流程与里程碑（M0~M9）请见：`ASSIGNMENTS.md`。
>
> 详细规范以 `docs/` 为准（SPEC/GRAMMAR/IR/OPT/CODEGEN/GUI）。

---

## 0. 强约束（MUST）

### 0.1 离线运行
- 运行/验收时不得依赖网络：
  - 不在线下载依赖
  - 不在线生成语法表
  - 不调用外部服务/API

### 0.2 依赖约束
- 默认：Python 3.11+ 标准库即可运行
- 可选增强（仅用于更漂亮输出/测试，不能成为必需）：`tabulate` / `rich` / `pytest`
- GUI 必须使用标准库 `tkinter`，不得引入 PyQt/GTK 等第三方 GUI 框架

### 0.3 输出契约（固定目录 + 固定文件名）
- 所有 stage 输出写入：`out/<input_basename>/`
- 文件名必须稳定（见第 3 节 Output Contract）

### 0.4 错误信息格式（英文）
- 错误信息本体统一英文格式（可在 GUI/CLI 中显示）：
  - `Error line:col: Expected 'X', but got TOKEN('lexeme')`
- GUI/CLI 的错误格式必须一致
- 非定位错误：
  - `Error: undefined label L3`
  - `Error: failed to read input file: <reason>`

---

## 1. 技术栈与代码风格（MUST）

### 1.1 语言与版本
- Python 3.11+
- 全项目统一编码：UTF-8

### 1.2 代码结构原则
- 模块单一职责：
  - `lexer.py`：词法
  - `grammar.py`：产生式/符号集合/编号
  - `lalr.py`：LR(1) → LALR(1) 表构造
  - `parser.py`：shift/reduce 驱动与 trace 输出
  - `ir.py`：四元式与 backpatch
  - `cfg.py`：基本块/CFG
  - `opt.py`：优化 passes
  - `codegen.py`：目标代码生成（栈机/伪汇编）
  - `gui.py`（可选）：GUI 界面（也可放在 main 内部）
  - `main.py`：入口/参数解析/分发 stage

### 1.3 类型与数据结构
- 公共数据结构优先使用：
  - `@dataclass`：Token / Quad / Production / LRItem / RunResult
  - `Enum`：TokenType / OpCode（或字符串常量，但需统一）
  - `typing`：函数签名必须带类型标注（至少对外接口）

### 1.4 可读性与注释
- 关键算法处必须有简短注释：
  - closure/goto
  - 合并同核（LALR）
  - backpatch
  - DCE（死代码删除）
- 不写大段论文式注释，偏“关键点说明即可”

---

## 2. 可执行命令（Commands）

> 下面命令必须可直接运行（在无网络环境下）。

### 2.1 GUI（默认入口）
- `python -m src.main`
- `python -m src.main --mode gui`

### 2.2 CLI（用于验收/导出）
示例（以 `examples/demo.min` 为例）：

- Lexer：
  - `python -m src.main --mode cli --input examples/demo.min --stage lexer`
- LALR 表：
  - `python -m src.main --mode cli --input examples/demo.min --stage table`
- Parse（trace）：
  - `python -m src.main --mode cli --input examples/demo.min --stage parse`
- IR：
  - `python -m src.main --mode cli --input examples/demo.min --stage ir`
- OPT：
  - `python -m src.main --mode cli --input examples/demo.min --stage opt`
- Codegen：
  - `python -m src.main --mode cli --input examples/demo.min --stage codegen`
- 全流程：
  - `python -m src.main --mode cli --input examples/demo.min --stage all`

### 2.3 Tests（可选但推荐）
- 优先使用标准库：
  - `python -m unittest -q`
- 若引入 pytest（可选依赖）：
  - `pytest -q`

---

## 3. 输出契约（Output Contract, MUST）

对输入 `examples/demo.min`：
- 输出目录：`out/demo/`

必须生成：
- `out/demo/tokens.csv`
- `out/demo/action_goto.csv`（或 `action.csv` + `goto.csv`，但二选一固定）
- `out/demo/parse_trace.txt`
- `out/demo/ir.quad`
- `out/demo/ir_opt.quad`
- `out/demo/opt_report.txt`
- `out/demo/target.asm`

输出要求：
- CSV 必须有 header
- trace/report 必须可读、行分隔清晰
- 输出格式允许调整，但必须稳定、易读、可粘贴进报告

---

## 4. Trace / Report 规范（MUST）

### 4.1 parse_trace.txt
每步至少包含：
- state stack
- symbol stack（可选但推荐）
- remaining input（token 序列或其前若干项）
- action（shift/reduce/accept/error）

### 4.2 opt_report.txt（英文）
必须包含：
- Pass pipeline（执行顺序）
- 基本块摘要（范围 + 后继）
- 每个 pass 的变更摘要：
  - removed indices
  - replaced old -> new
- Stats：优化前后指令条数

（详细格式见 `docs/OPT.md`）

---

## 5. Definition of Done（DoD）

一次实现/修改只有满足以下条件才算完成：

- CLI 在 `examples/` 的所有样例上不崩溃
- `--stage all` 能生成完整输出集（tokens/table/trace/ir/opt/codegen）
- 语法错误/词法错误能输出英文 Error 格式（含 line:col 若可定位）
- 输出目录与文件名完全符合 Output Contract
- 无网络环境可直接运行（无 pip 依赖也能跑通基本功能）

---

## 6. 任务流程与里程碑

- 任务流程（M0~M9）与验收标准请见：`ASSIGNMENTS.md`。
