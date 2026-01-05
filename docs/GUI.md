# MiniLang GUI 设计规范（GUI）

本文档规定 MiniLang 的图形界面（GUI）设计与交互行为。
GUI 的目标是：以“菜单驱动”的方式引导用户完成 Lexer / LALR 表生成 / Parse / IR / OPT / CodeGen 等功能，
并在界面中展示运行状态与输出文件位置。GUI 使用 Python 标准库 `tkinter` 实现，不引入额外依赖。

---

## 1. GUI 总体要求

### 1.1 必须满足
- 提供菜单（Menu）驱动各功能（与课程要求“设立菜单，根据提示完成”一致）
- 可选择输入源文件（Open）
- 支持运行各阶段（lexer/table/parse/ir/opt/codegen/all）
- 显示运行状态（成功/失败）与输出目录（路径）
- 若出错：显示英文格式错误信息（与 SPEC 第 8 节一致）

### 1.2 非必需但推荐（加分项）
- 支持“最近输出文件快速打开”
- 支持“复制输出目录路径”
- 支持“自动在日志面板显示 parse_trace / opt_report 摘要”
- 运行时禁用菜单项，结束后恢复（防止重复点击）

---

## 2. 启动方式与入口

- 默认入口：`python -m src.main`（即 `--mode gui`）
- GUI 作为主进程窗口，不依赖 CLI `--stage`

---

## 3. 窗口布局（推荐）

推荐主窗口分为 3 个区域：

1) 顶部：状态栏（Status Bar）
- 显示：
  - 当前输入文件：`Input: <path>`
  - 当前输出目录：`Output: out/<name>/`
  - 最近一次运行结果：`Success` 或 `Failure`

2) 中部：日志/输出面板（Text）
- 用于显示：
  - 运行过程简要日志（英文）
  - 错误详细信息（英文）
  - 可选：展示 `parse_trace.txt` 前 N 行或 `opt_report.txt` 摘要

3) 底部：快捷按钮区（可选）
- `Run All`
- `Open Output Folder`
- `Clear Log`

> 菜单是必须项；按钮区是可选增强。

---

## 4. 菜单设计（必须）

### 4.1 Menu Bar 顶层菜单
必须包含至少以下菜单：

- `File`
- `Run`
- `View`
- `Help`（可选但推荐）

### 4.2 File 菜单（必须）
包含：
- `Open...`：打开文件选择框，选择 `.min` 或任意文本文件
- `Recent`（可选）：最近打开的 3~5 个文件
- `Exit`：退出程序

行为要求：
- 选择文件后：
  - 更新状态栏 `Input: ...`
  - 自动计算输出目录 `out/<input_basename>/`
  - 在日志面板输出：
    - `Loaded: <path>`
    - `Output dir: out/<name>/`

### 4.3 Run 菜单（必须）
包含菜单项（与 CLI stage 一一对应）：
- `Lexer`
- `Build LALR Table`
- `Parse Trace`
- `Generate IR`
- `Optimize IR`
- `Codegen`
- `Run All`

行为要求：
- 每次运行前检查是否已选择输入文件：
  - 若未选择，弹窗提示（英文）：
    - `Error: no input file selected. Please use File -> Open...`
- 运行期间：
  - 在日志面板追加：
    - `Running: <stage> ...`
  - 禁用 Run 菜单或禁用正在执行项（推荐）
- 运行成功：
  - 状态栏显示 `Success`
  - 日志面板追加：
    - `Success: output written to out/<name>/`
- 运行失败：
  - 状态栏显示 `Failure`
  - 日志面板追加英文错误信息（格式见第 6 节）

### 4.4 View 菜单（必须）
包含：
- `Open Output Folder`：打开输出目录
- `Open tokens.csv`
- `Open action_goto.csv`
- `Open parse_trace.txt`
- `Open ir.quad`
- `Open ir_opt.quad`
- `Open opt_report.txt`
- `Open target.asm`

行为要求：
- 若文件不存在（尚未生成），弹窗提示（英文）：
  - `Error: file not found. Please run the corresponding stage first.`
- 打开方式：
  - 优先使用系统默认方式打开（macOS `open` / Windows `start` / Linux `xdg-open`）
  - 若无法调用系统命令，则在 GUI 的日志面板显示文件路径并提示用户手动打开

### 4.5 Help 菜单（可选）
包含：
- `About`：显示简短说明（版本、作者、如何运行）
- `Shortcuts`（可选）：显示快捷键列表

---

## 5. GUI 与核心编译流水线的集成方式（必须）

GUI 不应“复制实现”各阶段逻辑；应复用核心模块函数。

推荐架构：
- `src/pipeline.py`（建议新增）
  - 对外暴露统一接口：
    - `run_stage(input_path: str, stage: str) -> RunResult`
- GUI 只负责：
  - 选择文件
  - 调用 `run_stage(...)`
  - 展示结果/错误
  - 打开输出文件

`RunResult`（建议）：
- `ok: bool`
- `output_dir: str`
- `message: str`（简短日志）
- `error: str | None`（英文错误信息，若失败）

---

## 6. 错误展示规范（必须，英文输出）

GUI 中的错误信息文本必须与 CLI 的格式一致（SPEC 第 8 节）：

- 必须包含 `line:col`（若可定位）
- token 的 `type/lexeme`
- 简短英文原因
- 尽可能包含 expected tokens 提示

示例（仅示意）：
- `Error 3:15: Expected ';', but got ID('x')`
- `Error 10:5: Unexpected token RBRACE('}'). Expected one of: ID, IF, WHILE, LBRACE`

无法定位行列时：
- `Error: undefined label L3`
- `Error: failed to read input file: <reason>`

---

## 7. 输出目录与文件命名（必须）

GUI 必须遵守 `docs/SPEC.md` 的输出约定：
- 输出目录：`out/<input_basename>/`
- 文件名固定：
  - `tokens.csv`
  - `action_goto.csv`
  - `parse_trace.txt`
  - `ir.quad`
  - `ir_opt.quad`
  - `opt_report.txt`
  - `target.asm`

GUI 的 View 菜单必须基于这些固定文件名定位打开。

---

## 8. 推荐快捷键（可选）

- `Ctrl/Cmd + O`：Open...
- `Ctrl/Cmd + R`：Run All
- `Ctrl/Cmd + L`：Clear Log
- `Ctrl/Cmd + E`：Open Output Folder

---

## 9. 最小验收清单（必须通过）

- [ ] 能打开输入文件并显示路径
- [ ] Run 菜单可逐项运行，并生成对应输出文件
- [ ] View 菜单能打开输出目录与已生成文件
- [ ] 未选文件点击 Run：给出英文错误提示
- [ ] 运行失败：日志面板显示英文错误信息（含 line:col 若可定位）
