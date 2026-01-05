# MiniLang 中间代码规范（IR）

本文档规定 MiniLang 的中间表示（IR）格式与生成规则。
本项目采用“四元式（quadruple）”为主，并要求支持控制流（if/while）与回填（backpatch）。

---

## 1. 术语与目标

- IR 的目标：
  1) 表达式计算可三地址化（引入临时变量）
  2) 控制流显式化（条件跳转/无条件跳转/标签）
  3) 便于基本块划分与优化
  4) 便于目标代码生成

- 重要约束：
  - IR 输出必须稳定可读（便于写报告截图）
  - 同一输入的 IR 在同一实现下应可复现（不要包含时间戳等随机信息）

---

## 2. 四元式格式

### 2.1 基本形式
统一使用四元式：
```

(index)  (op, arg1, arg2, res)

```

- `index`：从 0 或 1 开始的整数编号（推荐从 0 开始）
- `op`：操作码（字符串或枚举）
- `arg1/arg2/res`：操作数（变量名/临时变量/常量/标签名/空位）

### 2.2 操作数表示
- 标识符变量：直接用其词素名，如 `a`, `b`, `count`
- 常量：用十进制字符串，如 `0`, `42`
- 临时变量：`t1, t2, ...`（必须全局递增，不回收）
- 标签：`L1, L2, ...`（必须全局递增，不回收）
- 空位：使用 `-` 或空字符串（全项目统一，推荐 `-`）

---

## 3. 操作码集合（最小集合）

### 3.1 算术
- `ADD`：`res = arg1 + arg2`
- `SUB`：`res = arg1 - arg2`
- `MUL`：`res = arg1 * arg2`
- `DIV`：`res = arg1 / arg2`

### 3.2 赋值
- `ASSIGN`：`res = arg1`
  - 约定：`(ASSIGN, x, -, y)` 表示 `y = x`

### 3.3 关系（用于条件跳转）
为简化控制流，推荐使用“条件跳转 + 比较内置”操作码：

- `IF_LT`, `IF_GT`, `IF_EQ`, `IF_NE`
  - 语义：若 `arg1 <arg> arg2` 为真则跳转到 `res`（res 为标签）
  - 形式：`(IF_GT, x, y, Lk)` 表示 `if (x > y) goto Lk`

> 注：如不想引入 IF_xx 系列，也可用 `CMP + Jxx` 两步形式，但会增加 IR 体积。
> 本规范默认 IF_xx 以利于简洁与回填。

### 3.4 无条件跳转与标签
- `GOTO`：
  - 形式：`(GOTO, -, -, Lk)`
- `LABEL`：
  - 形式：`(LABEL, -, -, Lk)`

---

## 4. 表达式 IR 生成规则

### 4.1 二元运算（Expr/Term）
- 对于 `x + y`：
  1) 计算子表达式得到位置 `p(x)`, `p(y)`（变量名/常量/临时变量）
  2) 生成新临时变量 `t = new_temp()`
  3) 发射：`(ADD, p(x), p(y), t)`
  4) 返回该表达式位置为 `t`

其它运算类似：`SUB/MUL/DIV`

### 4.2 赋值语句
对 `a = Expr;`：
1) 生成 Expr，得到位置 `p`
2) 发射：`(ASSIGN, p, -, a)`

---

## 5. 控制流 IR 与 backpatch

### 5.1 backpatch 数据结构（概念）
为实现 if/while 的跳转目标回填，语义动作建议维护以下“链表”（可用 Python list 存 quad index）：

- `trueList`：需要回填为“条件为真跳转目标”的四元式索引集合
- `falseList`：需要回填为“条件为假跳转目标”的四元式索引集合
- `nextList`：语句结束后需要跳到“后继位置”的 GOTO 集合（用于语句串联）

配套工具函数（概念）：
- `makelist(i)`：创建只含 i 的列表
- `merge(a, b)`：合并列表
- `backpatch(lst, label)`：将 lst 中每条四元式的 `res` 字段回填为 label

### 5.2 生成标签与标记点
建议在语义动作中使用“标记点”：
- `M`：记录当前下一条四元式的 index（或将来要插入 LABEL 的位置）
- `new_label()`：生成 `Lk` 并发射 `(LABEL, -, -, Lk)`

实践建议（更易实现）：
- 每当需要一个目标位置时，立即生成一个标签并发射 `LABEL`
- backpatch 时只回填标签名（如 `L3`），不回填裸 index

---

## 6. 关系表达式（RelExpr）的 IR 规范

对 `x > y`：
- 生成两条“跳转框架”（用于 if/while/短路）：

1) 条件为真跳转（目标待回填）：
   - 发射：`(IF_GT, p(x), p(y), ?)`
2) 条件为假跳转（目标待回填）：
   - 发射：`(GOTO, -, -, ?)`

并返回：
- `trueList = [index_of_IF_GT]`
- `falseList = [index_of_GOTO]`

其它关系同理：
- `==` → `IF_EQ`
- `!=` → `IF_NE`
- `<`  → `IF_LT`

> 说明：这里用两条指令保证 Bool 表达式能自然产生 true/false 两个出口。

---

## 7. 逻辑表达式（and/or/not）的短路（推荐实现）

### 7.1 `B1 or B2`
短路规则：
- 若 `B1` 为真，则整个表达式为真，不再计算 `B2`
- 若 `B1` 为假，则去计算 `B2`

语义（概念）：
1) 生成 `B1` 得到 `(B1.trueList, B1.falseList)`
2) 生成一个标签 `L` 作为进入 `B2` 的入口：
   - `backpatch(B1.falseList, L)`
3) 生成 `B2`
4) 结果：
   - `trueList = merge(B1.trueList, B2.trueList)`
   - `falseList = B2.falseList`

### 7.2 `B1 and B2`
短路规则：
- 若 `B1` 为假，则整个为假，不再计算 `B2`
- 若 `B1` 为真，则去计算 `B2`

语义（概念）：
1) 生成 `B1`
2) 生成标签 `L` 作为进入 `B2` 的入口：
   - `backpatch(B1.trueList, L)`
3) 生成 `B2`
4) 结果：
   - `trueList = B2.trueList`
   - `falseList = merge(B1.falseList, B2.falseList)`

### 7.3 `not B`
语义（概念）：
- `trueList = B.falseList`
- `falseList = B.trueList`

> 若不实现短路，也可将 Bool 计算为临时变量再比较，但会弱化“编译器感”。建议实现短路以加分。

---

## 8. if-else 语句 IR 规则（使用 backpatch）

目标结构（概念）：

```
B
if true  → L_then: S_then
if false → L_else: S_else
L_end
```

推荐生成流程（概念）：

1) 生成 Bool：得到 `B.trueList`, `B.falseList`
2) 生成 `L_then` 并回填 `B.trueList → L_then`
3) 生成 then 语句 `S1`
4) 生成一条跳到结束的 GOTO（目标待回填）：
   - `goto_end = emit(GOTO, -, -, ?)`
5) 生成 `L_else` 并回填 `B.falseList → L_else`
6) 生成 else 语句 `S2`
7) 生成 `L_end` 并回填：
   - `backpatch([goto_end], L_end)`

`Stmt.nextList` 的处理：
- 若实现 `nextList`，可将 then/else 的 nextList 与 goto_end 合并，最后回填到 L_end。
- 最简实现可直接用 goto_end 控制结构，StmtList 串联用 LABEL 连接。

---

## 9. while 语句 IR 规则（使用 backpatch）

目标结构（概念）：

```
L_begin:
B
if false → L_end
L_body:
S
goto L_begin
L_end:
```

推荐生成流程（概念）：

1) 生成 `L_begin`（LABEL）
2) 生成 Bool：得到 `B.trueList`, `B.falseList`
3) 生成 `L_body` 并回填 `B.trueList → L_body`
4) 生成循环体 `S`
5) 发射回跳：
   - `(GOTO, -, -, L_begin)`
6) 生成 `L_end` 并回填 `B.falseList → L_end`

---

## 10. IR 输出文件格式（ir.quad / ir_opt.quad）

- 每行一条四元式，推荐格式：
```
12: (ADD, a, 1, t3)
13: (ASSIGN, t3, -, a)
```
- LABEL 也按四元式输出：
```
20: (LABEL, -, -, L5)
```

---

## 11. 最小示例（展示风格，不作为唯一正确答案）

输入：
```c
a = 1 + 2 * 3;
if (a > 0) a = a - 1; else a = 0;
```

可能的 IR（示意）：

```
0: (MUL, 2, 3, t1)
1: (ADD, 1, t1, t2)
2: (ASSIGN, t2, -, a)
3: (IF_GT, a, 0, L1)
4: (GOTO, -, -, L2)
5: (LABEL, -, -, L1)
6: (SUB, a, 1, t3)
7: (ASSIGN, t3, -, a)
8: (GOTO, -, -, L3)
9: (LABEL, -, -, L2)
10:(ASSIGN, 0, -, a)
11:(LABEL, -, -, L3)
```

---

## 12. 与优化/代码生成的接口约定

* 优化器输入：`ir.quad` 中的四元式序列（含 LABEL/GOTO/IF_*）
* 目标代码生成输入：`ir_opt.quad`（默认使用优化后 IR）
* 重要约定：

  * 不允许在优化后破坏控制流结构（LABEL/GOTO/IF_* 的一致性必须保持）
  * 不允许重命名用户变量（ID），临时变量可在保持语义一致前提下消除/合并
