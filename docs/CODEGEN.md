# MiniLang 目标代码生成规范（CODEGEN）

本文档规定从 IR（四元式）生成目标代码 `target.asm` 的规则。
目标代码不要求真实机器汇编，可采用“栈机指令（stack-based VM）”或“伪汇编”。
本规范默认使用 **栈机指令集**（简单、稳定、适合作业展示）。

---

## 1. 总体原则

- 目标代码必须可读、可复现、跳转目标正确
- 支持：算术、赋值、关系判断、条件跳转、无条件跳转、标签
- 本项目默认不实现 I/O 指令；验收以生成代码文本为主
- 若实现解释器（可选），需保证 `target.asm` 可被解释执行

---

## 2. 目标代码输出文件

- 输出文件：`out/<input_name>/target.asm`
- 每行一条指令
- 标签以 `Lk:` 单独一行表示（如 `L3:`）
- 行末可选注释（用 `;` 开头），便于报告展示

示例：
```
L1:
LOAD a
PUSH 0
GT
JZ L2
...
JMP L3
L2:
...
L3:
HALT
```

---

## 3. 运行模型（Stack VM）

### 3.1 数据栈
- VM 有一个操作数栈
- 表达式计算通过栈完成：先压入操作数，再执行运算指令

### 3.2 变量存储（抽象）
- `ID` 与临时变量 `t*` 均视为“符号表槽位”
- 目标代码使用 `LOAD name` / `STORE name` 访问变量
- 不区分用户变量与临时变量（都可 STORE/LOAD）

> 若你实现解释器：可用 dict<string,int> 作为内存。

---

## 4. 指令集定义（最小集合）

### 4.1 栈与内存
- `PUSH c`：将常量 `c` 压栈
- `LOAD x`：将变量 `x` 的值压栈
- `STORE x`：弹栈顶并写入变量 `x`

### 4.2 算术
- `ADD`：弹出 b、a，压入 a+b
- `SUB`：压入 a-b
- `MUL`：压入 a*b
- `DIV`：压入 a/b（整数除法；除零行为可不定义或由解释器报错）

### 4.3 比较（产生布尔值 0/1）
- `LT`：压入 (a < b)
- `GT`：压入 (a > b)
- `EQ`：压入 (a == b)
- `NE`：压入 (a != b)

### 4.4 跳转
- `JMP L`：无条件跳转
- `JZ  L`：若栈顶为 0，则跳转（并弹栈顶）
- `JNZ L`：若栈顶非 0，则跳转（并弹栈顶）

### 4.5 程序结束
- `HALT`：停止（可选，但推荐输出以便展示完整）

---

## 5. IR 到目标代码的映射规则（必须）

### 5.1 操作数加载规则
定义一个通用函数 `emit_load(x)`：
- 若 x 是 `-`：不发射任何指令
- 若 x 是常量（全数字）：发射 `PUSH x`
- 否则（变量名/临时变量名）：发射 `LOAD x`

### 5.2 LABEL
IR：
- `(LABEL, -, -, Lk)`
目标代码：
- `Lk:`

### 5.3 GOTO
IR：
- `(GOTO, -, -, Lk)`
目标代码：
- `JMP Lk`

### 5.4 ASSIGN
IR：
- `(ASSIGN, arg1, -, res)`  表示 `res = arg1`
目标代码：
1) `emit_load(arg1)`
2) `STORE res`

### 5.5 算术四元式
IR：
- `(ADD, a, b, t)`
目标代码：
1) `emit_load(a)`
2) `emit_load(b)`
3) `ADD`
4) `STORE t`

其它类似：
- `SUB` → `SUB`
- `MUL` → `MUL`
- `DIV` → `DIV`

### 5.6 条件跳转 IF_*
IR：
- `(IF_GT, x, y, Lk)` 表示 `if (x > y) goto Lk`
目标代码（统一实现方式）：

1) `emit_load(x)`
2) `emit_load(y)`
3) `GT`            ; 栈顶为 1/0
4) `JNZ Lk`        ; 若条件真则跳转（弹出比较结果）

其它关系：
- `IF_LT` → `LT` + `JNZ`
- `IF_EQ` → `EQ` + `JNZ`
- `IF_NE` → `NE` + `JNZ`

> 注意：IR 的 `IF_*` 是“真跳转”语义，因此用 `JNZ`。

---

## 6. 代码生成顺序与标签解析（必须）

### 6.1 生成顺序
- 按 IR 列表顺序逐条翻译
- LABEL 必须在跳转指令之前或之后均可，但跳转目标必须能在最终文本中找到对应 `Lk:`

### 6.2 未定义标签处理
- 若发现跳转目标标签不存在，应报错（英文）：
  - `Error: undefined label Lk`

---

## 7. 示例：if-else / while 的代码形态（示意）

### 7.1 if-else（示意）
IR（示意）：
```
(IF_GT, a, 0, L_then)
(GOTO, -, -, L_else)
(LABEL, -, -, L_then)
...
(GOTO, -, -, L_end)
(LABEL, -, -, L_else)
...
(LABEL, -, -, L_end)
```

目标代码（示意）：
```
LOAD a
PUSH 0
GT
JNZ L_then
JMP L_else
L_then:
...
JMP L_end
L_else:
...
L_end:
```

### 7.2 while（示意）
IR（示意）：
```
(LABEL, -, -, L_begin)
(IF_NE, a, 0, L_body)
(GOTO, -, -, L_end)
(LABEL, -, -, L_body)
...
(GOTO, -, -, L_begin)
(LABEL, -, -, L_end)
```

目标代码（示意）：
```
L_begin:
LOAD a
PUSH 0
NE
JNZ L_body
JMP L_end
L_body:
...
JMP L_begin
L_end:
```

---

## 8. 输出格式与注释（建议）

为便于报告展示，可以在每条指令旁加注释（不强制）：

- 翻译自第 n 条 IR：
  - `; IR[12]: (ADD, a, b, t1)`

示例：
```
LOAD a     ; IR[12]
LOAD b     ; IR[12]
ADD        ; IR[12]
STORE t1   ; IR[12]
```

---

## 9. 可选：解释器（非必需）

若实现解释器，可放在 `src/vm.py`，支持：
- 解析 `target.asm`
- 维护 `stack` 与 `mem`（dict）
- 解析标签到行号的映射表
- 执行指令直至 HALT

但作业验收不以解释器为硬性要求。
 