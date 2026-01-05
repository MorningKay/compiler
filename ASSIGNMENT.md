# ASSIGNMENTS.md — MiniLang 任务流程与里程碑（What to Build）

> 本文件定义 MiniLang 的任务拆解、里程碑（M0~M9）与验收标准。
> Coding Agent 应按顺序完成：M0 → M1 → ... → M9。
>
> 工程约束/命令/输出契约请见 `AGENTS.md`。
> 语言与实现规范请见 `docs/`。

---

## M0 — 工程骨架与跑通

### 产出
- CLI 可读取文件、可按 stage 分发
- `examples/` 至少 3 个样例

### 验收
- `python -m src.main --mode cli --input examples/demo.min --stage lexer`可运行并生成 `out/demo/tokens.csv`

---

## M1 — Lexer（词法分析）

### 产出
- Token 类型：关键字、标识符、数字、运算符、界符
- Token 含 `index, type, lexeme, line, col`（至少 line/col）

### 验收
- 对 `examples/` 全部样例输出 tokens，不崩溃，定位信息正确
- 非法字符能报错（英文 Error 格式）

---

## M2 — Grammar（文法定稿）

### 产出
- 覆盖：表达式/关系/逻辑/赋值/if-else/while/block
- 明确优先级（算术 > 关系 > 逻辑；and 高于 or）
- 使用增广文法（S' → Program EOF）
- if-else 采用 Matched/Unmatched 规避 dangling-else（推荐）

### 验收
- 文法可用于构建 LALR(1)（冲突应可定位并修正）

---

## M3 — LALR(1) 表生成器（重点）

### 产出
- LR(1) closure/goto、项目集族
- 合并同核得到 LALR(1)
- 导出 ACTION/GOTO 表到 CSV（action_goto.csv 或拆分）

### 验收
- 对主文法生成表：无冲突
- 若出现冲突必须输出“state + production + lookahead”定位信息

---

## M4 — Parser 驱动（shift/reduce + 日志）

### 产出
- 根据 ACTION/GOTO 表解析输入
- 输出 parse trace：状态栈、符号栈、剩余输入、动作

### 验收
- 合法样例 accept
- 非法样例：给出英文错误（Error line:col: Expected ...）

---

## M5 — IR（四元式）与 backpatch（控制流加分点）

### 产出
- 表达式生成临时变量：t1,t2,...
- 跳转与标签：IF_* / GOTO / LABEL（或等价形式）
- backpatch：trueList/falseList（and/or/not 的短路推荐）

### 验收
- `if` 与 `while` 样例生成合理跳转结构，标签回填正确
- 输出 `ir.quad`

---

## M6 — 基本块与 CFG

### 产出
- 基本块划分（leaders）
- CFG 后继边（用于优化与循环识别）

### 验收
- 输出每个基本块的指令范围与后继列表（`cfg.txt` 或并入 report）

---

## M7 — 优化（必做：基本块内；选做：循环优化）

### 必做（基本块内）
- 常量折叠（Folding）
- 常量传播（Const Prop）
- 拷贝传播（Copy Prop）
- 死代码删除（DCE）
- CSE（可选但推荐）

### 选做（循环优化，加分）
- LICM（循环不变式外提）或强度削弱（二选一）

### 验收
- `ir_opt.quad` 相比 `ir.quad` 有可见变化且语义不变
- 输出 `opt_report.txt`（英文，含 pass、变更、统计）

---

## M8 — 目标代码生成（伪汇编/栈机）

### 产出
- 将四元式映射到栈机/伪汇编
- 输出到 `target.asm`

### 验收
- 输出格式统一
- LABEL/GOTO/IF_* 跳转目标一致
- 对示例程序生成可读目标代码

---

## M9 — 一键导出报告素材

### 产出
- `--stage all` 自动导出：tokens、表、trace、IR、优化后 IR、目标代码

### 验收
- 跑一次命令即可在 `out/<name>/` 拿齐所有报告材料

---

### 样例策略

* `examples/demo.min`：**canonical**
  * M0–M3：保证可被读取并可生成对应阶段输出（允许 stub）。
  * M4 起：合法样例必须 parse accept；M5 起可生成 IR；M8 起可生成 target.asm；M9 必须 stage all 全流程跑通。
* `examples/expr.min`：表达式优先级/括号回归
* `examples/control.min`：控制流与嵌套结构回归
* `examples/bad.min`：错误提示回归（必须报英文 Error + expected tokens）
* （可选）`examples/opt_showcase.min`：专门用来让优化效果“肉眼可见”

### 每个 stage / milestone 的必跑样例

* **stage=lexer（M1 起）**

  * 必须通过（能 tokenize，不崩溃）：`demo.min`, `expr.min`, `control.min`, `bad.min`
  * 备注：`bad.min` 在 lexer 阶段通常也应该能过（因为它只是语法错，不一定词法错）

* **stage=table（M3）**

  * 不依赖具体样例文件（只依赖 grammar）
  * 验收点：生成 `action_goto.csv`，无冲突（或冲突能定位）

* **stage=parse（M4）**

  * 必须 accept：`demo.min`, `expr.min`, `control.min`
  * 必须报错（英文 Error line:col + Expected tokens）：`bad.min`

* **stage=ir（M5）**

  * 必须生成合理 IR：`demo.min`（至少一个含 if/while 的样例）
  * 推荐额外验证：`control.min`（结构更集中）

* **stage=opt（M6+M7）**

  * 必须不崩溃且控制流仍正确：`demo.min`
  * 必须“优化前后有明显变化”：推荐用 `opt_showcase.min`（可选文件）

* **stage=codegen（M8）**

  * 必须生成 `target.asm` 且 label/jump 一致：`demo.min`（或 `control.min`）

* **stage=all（M9）**

  * 必须全流程跑通：`demo.min`
  * 推荐（非必须但很加分）：`expr.min`、`control.min` 也能 all（至少跑到 parse/ir）

---

## 可选加分项（不影响主验收）
- `--target x86_64`：生成真实 x86-64 汇编（仅生成文本也可加分）
- VM/解释器：解释执行 `target.asm`（若实现 I/O 则更强）
- GUI 增强：Recent Files、打开输出文件、复制路径、运行禁用按钮等
