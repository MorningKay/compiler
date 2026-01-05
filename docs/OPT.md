# MiniLang 优化规范（OPT）

本文档规定 IR（四元式）层的优化流程与必须实现的优化项。
目标是：在不改变语义的前提下，进行基本块内（局部）优化，并可选实现循环优化作为加分项。

---

## 1. 优化总体原则

- 语义不变：优化前后程序行为一致（同输入得到同输出/同变量结果）
- 控制流一致：LABEL / GOTO / IF_* 的跳转目标必须保持正确
- 可复现：同一输入的优化输出应稳定
- 可展示：必须能输出“优化前后对比”与“每个 pass 修改了什么”

---

## 2. 基本块划分（必须）

### 2.1 术语
- Leader（基本块入口）：
  1) 第一条四元式
  2) 任意 LABEL 指令
  3) 任意跳转指令（GOTO / IF_*）的下一条指令（fall-through）
  4) 任意跳转目标（被跳转到的 LABEL）

- 基本块（Basic Block）：
  - 从一个 leader 开始，直到下一个 leader 前结束（不含下一个 leader）

### 2.2 输出要求
必须输出基本块信息（写入 `out/<name>/cfg.txt` 或合并进 `opt_report.txt`）：
- 每个块：
  - block id（B0, B1, ...）
  - 指令范围（start_idx..end_idx）
  - 后继块列表（succs）
- 说明：后继边规则
  - IF_*：两个后继（跳转目标 + fall-through）
  - GOTO：一个后继（跳转目标）
  - 其它：一个后继（fall-through），若无下一块则为空

---

## 3. 必做优化（基本块内 Local Optimizations）

必须实现以下至少 4 类优化（推荐顺序见第 5 节）：

1) 常量折叠（Constant Folding）
2) 常量传播（Constant Propagation）
3) 拷贝传播（Copy Propagation）
4) 死代码删除（Dead Code Elimination, DCE）

可选但强烈推荐：
5) 公共子表达式消除（Common Subexpression Elimination, CSE）

---

## 4. 各优化项定义与实现要点

> 注意：所有优化默认仅在“基本块内”进行（local），无需跨块数据流分析。
> 若实现跨块优化，需在报告中明确说明，但不是必需。

### 4.1 常量折叠（Constant Folding）
**适用：**
- `ADD/SUB/MUL/DIV` 且 `arg1` 与 `arg2` 都是数字常量

**变换：**
- `t = 3 + 4` → `t = 7`（用 ASSIGN 或直接将 op 变为常量赋值）

**IR 形式建议：**
- 将该四元式替换为：`(ASSIGN, <const>, -, res)`

**注意：**
- DIV 的常量折叠需处理除零：若除零出现，保留原指令并在运行/解释阶段报错（或在优化阶段报告无法折叠）。

---

### 4.2 常量传播（Constant Propagation）
**适用：**
- 基本块内出现 `ASSIGN const -> x`，且在 x 被重新赋值前可视为常量

**变换：**
- 将后续使用 x 的地方替换成 const
  - `x = 5; y = x + 1` → `y = 5 + 1`

**实现要点（local map）：**
- 在基本块内维护 `const_env: var -> const`
- 遇到：
  - `ASSIGN const -> x`：记录 `const_env[x] = const`
  - `ASSIGN something -> x`：清除 `const_env[x]`
  - 其它指令：若 `arg1/arg2` 是变量且存在于 const_env，则替换为常量

---

### 4.3 拷贝传播（Copy Propagation）
**适用：**
- 基本块内出现 `ASSIGN y -> x`（x 是 y 的拷贝），且 y/x 未被重定义导致失效

**变换：**
- 将后续使用 x 的地方替换为 y
  - `x = y; z = x + 1` → `z = y + 1`

**实现要点（copy map）：**
- 维护 `copy_env: var -> var`
- 遇到：
  - `ASSIGN y -> x`（y 是变量）且 y 不是 x：记录 `copy_env[x] = y`
  - x 被重新赋值：清除 `copy_env[x]`
  - y 被重新赋值：需要清除所有 `copy_env[*] == y` 的映射（仅在基本块内扫描即可）
- 替换时可做“链式追踪”：
  - 若 `copy_env[x] = y` 且 `copy_env[y] = z`，则 x 替换为 z（直到不再可替换）

---

### 4.4 死代码删除（DCE）
**目标：**
- 删除“结果不再被使用”的指令（通常是产生临时变量的算术运算或冗余赋值）

**最稳的局部 DCE（基本块内活跃变量分析的简化版）：**
- 从块尾到块头逆序扫描，维护 `live` 集合（当前仍可能被后续使用的变量名）
- 对每条指令：
  - 若该指令定义了 `res`（如 ADD/SUB/MUL/DIV/ASSIGN）：
    - 如果 `res` 不在 `live`，且该指令无副作用，则可删除
    - 否则：从 `live` 中移除 `res`，并将该指令使用到的变量（arg1/arg2 若为变量）加入 `live`
  - 对 IF_* / GOTO / LABEL：不可删除；并将其使用到的变量加入 `live`（IF_* 的 arg1/arg2）
- 副作用规则：
  - 本项目 IR 中除了跳转/标签外，一般算术/赋值都可视为无副作用
  - 但对用户变量的 ASSIGN 是否可删：若该变量之后不再被使用且不影响输出，可删；为保守起见，允许只删临时变量 `t*` 的定义（更稳）

**建议（稳妥策略）：**
- 第一版只删除 `res` 为临时变量 `t*` 的无用定义
- 进阶再考虑删除对用户变量的无用赋值

---

### 4.5 公共子表达式消除（CSE，可选但推荐）
**适用：**
- 基本块内重复出现同样的纯表达式，如：
  - `t1 = a + b`
  - 中间 a/b 未被重定义
  - 又出现 `t2 = a + b`

**变换：**
- 第二次计算替换为拷贝：
  - `t2 = t1`

**实现要点：**
- 在基本块内维护 `expr_table: (op, arg1, arg2) -> res`
  - 注意：对交换律运算（ADD/MUL）可规范化 key：将 `(arg1,arg2)` 排序
- 遇到任何对变量的写入（res 是变量）时，需要使相关表达式失效：
  - 简化做法：若写入变量为 v，则删除 expr_table 中包含 v 的所有 key（线性扫描即可）

---

## 5. 推荐优化顺序（必须给出并在报告里能解释）

推荐 pass pipeline（可迭代多轮）：

1) Constant Folding
2) Constant Propagation
3) Copy Propagation
4) CSE（可选）
5) DCE

建议循环执行直到“不再变化”或最多迭代 N 轮（如 N=3）：
- 这样 `传播 → 折叠 → DCE` 会更充分

---

## 6. 可选循环优化（加分项）

> 选做 1 个即可，推荐：循环不变式外提（LICM）。

### 6.1 循环识别（最小实现）
- 若实现 while 的 IR 结构满足：
  - `LABEL L_begin`
  - 条件跳转/假跳转到 `L_end`
  - 循环体末尾 `GOTO L_begin`
- 则可将 `L_begin..(GOTO L_begin)` 视为循环范围（简化识别）

更严谨实现可用 CFG + 回边识别，但不强制。

### 6.2 循环不变式外提（LICM）
**目标：**
- 将循环体内每次都重复计算、且其操作数在循环内不变的表达式提到循环前

**局部判断（简化版即可）：**
- 指令形如：`t = a op b`（op 为 ADD/SUB/MUL/DIV）
- 若 `a` 与 `b` 在循环体内从未被赋值（未出现在任何指令的 res 中，且不是 `t`）
- 则该表达式可视为循环不变式，可外提到 `L_begin` 前

**注意：**
- 外提需要保证不改变异常行为（如除零）；本项目可先忽略这一点或保守处理 DIV

---

## 7. 优化报告（opt_report.txt）格式要求（必须）

优化阶段必须输出一份英文报告 `opt_report.txt`，包含：

1) 启用的 pass 列表（按执行顺序）
2) 基本块划分摘要（每块范围与后继）
3) 每个 pass 的修改摘要（至少包含）
   - 删除了哪些 quad index（原索引）
   - 替换了哪些指令（old -> new）
   - 新增了哪些指令（如有）
4) 统计信息（建议）
   - 优化前指令数 / 优化后指令数
   - 删除条数、替换条数

示例（仅示意）：
```
Pass pipeline: Folding -> ConstProp -> CopyProp -> DCE

BasicBlocks:
B0: 0..7  succs=[B1]
B1: 8..12 succs=[B2,B3]

Changes:
[Folding] replaced 2 quads
3: (ADD, 3, 4, t1)  -> 3: (ASSIGN, 7, -, t1)
[DCE] removed 1 quads
removed: 6

Stats:
quads_before=40
quads_after=33
````

---

## 8. 验收用最小案例（建议）

应准备一个样例，使优化效果明显，例如：

```c
a = 3 + 4;
b = a + 1;
c = a + 1;
d = c;
```

优化预期（示意）：

* 折叠：`a = 7`
* 传播：`b = 8`, `c = 8`
* CSE：`c` 可复用 b 的计算（或直接传播折叠）
* DCE：删除无用临时变量计算
