# MiniLang 语言规范（SPEC）

本规范定义 MiniLang 的语法特性、词法单元、运算符优先级、输入输出与错误报告要求。
该规范服务于编译流水线：Lexer → LALR(1) Parser → IR(四元式) → OPT → CodeGen。

---

## 1. 目标与范围

MiniLang 是一个教学用“小型语言”，用于覆盖课程选题 1~9 的典型特性，包含：

- 算术表达式：`+ - * /` 与括号 `(` `)`
- 关系表达式：`== != < >`（至少必须支持 `>` 与 `!=`）
- 逻辑表达式：`and` `or`（可选 `not`）
- 语句：赋值 `id = E ;`
- 控制流：`if (B) S else S`、`while (B) S`
- 语句块：`{ S* }`
- 注释（建议实现）：行注释 `// ...`（可选）

---

## 2. 词法规范（Lexer）

### 2.1 Token 类型（建议最小集合）

- 关键字：`if`, `else`, `while`, `and`, `or`, `not`(可选)
- 标识符：`ID`
  - 规则：`[A-Za-z_][A-Za-z0-9_]*`
- 整数：`NUM`
  - 规则：`[0-9]+`（十进制整数即可）
- 运算符/界符：
  - 算术：`+ - * /`
  - 赋值：`=`
  - 关系：`== != < >`
  - 分隔：`;`
  - 括号：`(` `)`
  - 花括号：`{` `}`

### 2.2 空白与换行
- 空格、Tab、换行用于分隔 token
- Lexer 必须维护 `line:col` 位置信息

### 2.3 输出（tokens）
- `tokens.csv` 至少包含列：
  - `index,type,lexeme,line,col`
- `type` 使用稳定枚举名（例如 `ID/NUM/IF/PLUS/NE/...`）

### 2.4 TokenType 命名约定（必须）

tokens.csv 的 `type` 必须使用稳定枚举名（TokenType），不得使用以下形式：
- 不得使用通用 `KEYWORD` 作为 type
- 不得直接用符号本身（如 `=`, `+`, `(`, `!=`）作为 type

必须使用如下枚举名（最小集合）：

- 标识符/数字：
  - `ID`, `NUM`

- 关键字：
  - `IF`, `ELSE`, `WHILE`, `AND`, `OR`（可选 `NOT`）

- 运算符：
  - `PLUS`(+), `MINUS`(-), `MUL`(*), `DIV`(/)
  - `ASSIGN`(=)
  - `EQ`(==), `NE`(!=), `LT`(<), `GT`(>)

- 界符：
  - `SEMI`(;)
  - `LPAREN`(() , `RPAREN`())
  - `LBRACE`({) , `RBRACE`(})

`lexeme` 字段保留原始字符串（如 `if`, `!=`, `{`），用于展示与报错。

---

## 3. 语法规范（Grammar）

本节描述“语言结构”，最终实现允许采用等价改写，只要语义一致且可生成 LALR(1) 表。

### 3.1 程序结构
- 程序由若干语句构成：
  - `Program → StmtList`

### 3.2 语句（Stmt）
- 赋值：
  - `Stmt → ID '=' Expr ';'`
- 条件：
  - `Stmt → 'if' '(' Bool ')' Stmt 'else' Stmt`
- 循环：
  - `Stmt → 'while' '(' Bool ')' Stmt`
- 块：
  - `Stmt → '{' StmtList '}'`
- 语句序列：
  - `StmtList → StmtList Stmt | Stmt | ε`
  - 说明：允许空块 `{}`

> 注意：若出现 LALR(1) 冲突，允许将 StmtList 改成更适配的右递归形式，或对 if-else 采用经典“匹配/未匹配”改写方案。

### 3.3 表达式（Expr）
应支持括号与优先级，推荐分层：
- `Expr → Expr ('+'|'-') Term | Term`
- `Term → Term ('*'|'/') Factor | Factor`
- `Factor → ID | NUM | '(' Expr ')'`

### 3.4 布尔表达式（Bool）
推荐：
- 关系：
  - `Rel → Expr ('=='|'!='|'<'|'>') Expr`
- 逻辑组合（含优先级）：
  - `Bool → Bool 'or' And | And`
  - `And  → And 'and' Not | Not`
  - `Not  → 'not' Not | Rel`   （not 可选，不实现则 Not → Rel）

---

## 4. 运算符优先级与结合性（必须）

从高到低：

1. 括号 `()`
2. 一元 `not`（若实现）
3. 乘除 `* /`（左结合）
4. 加减 `+ -`（左结合）
5. 关系 `== != < >`（非结合/或按左结合处理，但建议不允许链式比较）
6. 逻辑 `and`（左结合）
7. 逻辑 `or`（左结合）

约束：
- 不支持 `a < b < c` 这种链式比较（若输入出现，按语法错误处理）

---

## 5. 语义与 IR（只规定“应达到的行为”）

### 5.1 赋值
- `a = Expr;` 计算 Expr 并写回 a

### 5.2 条件 if-else
- 条件为真执行 then 分支，否则执行 else 分支

### 5.3 循环 while
- 每轮先判断条件，真则执行循环体并回到判断；假则退出

### 5.4 中间代码（四元式）要求（概念层）
IR 以“四元式”为主，形式可选其一（但需全项目统一）：

- 三地址：`(op, arg1, arg2, res)`
- 跳转建议至少包含：
  - 条件跳转：`(ifFalse, cond, -, Lx)` 或 `(j<op>, x, y, Lx)`
  - 无条件跳转：`(goto, -, -, Ly)`
  - 标签：`(label, -, -, Lx)` 或用行号代替 label

要求：
- 表达式必须生成临时变量 `t1, t2, ...`
- if/while 必须体现控制流（跳转/标签）
- 建议使用 backpatch（trueList/falseList/nextList）完成跳转目标回填

---

## 6. 输出与目录规范（必须）

对输入 `examples/demo.min`：
- 输出目录：`out/demo/`

至少输出：
- `tokens.csv`
- `action_goto.csv`（或拆成 `action.csv` 与 `goto.csv`）
- `parse_trace.txt`
- `ir.quad`
- `ir_opt.quad`
- `opt_report.txt`
- `target.asm`

补充：EOF 终结符在代码内部统一命名为 `EOF`；在导出的 ACTION/GOTO 表列名或 parse trace 的剩余输入展示中，可将 `EOF` 显示为 `$`。

---

## 7. CLI 与 GUI 规范（必须）

### 7.1 CLI
示例：
```bash
python -m src.main --input examples/demo.min --stage all
```

stage：

* `lexer` / `table` / `parse` / `ir` / `opt` / `codegen` / `all`
* `gui`：启动 GUI 菜单（建议 tkinter，标准库）

### 7.2 GUI（建议 tkinter）

GUI 至少包含：

- 选择输入文件（Open）
- 菜单运行：lexer/table/parse/ir/opt/codegen/all
- 显示运行状态（Success/Failure）与输出目录提示（英文）
  - 示例：`Success: output written to out/demo/`
  - 失败示例：`Failure: see error details below`
- 若发生错误，在界面中显示英文错误信息（与 CLI 错误格式一致）

---

## 8. 错误处理（必须）

错误信息必须包含：

* `line:col`
* 出错 token 的 `type/lexeme`
* 简短原因（**英文输出**）
* 尽可能给出“期望 token 集合”（例如：期待 `';'` 或 `')'`）

示例（格式仅示意，**输出为英文**）：

* `Error 3:15: Expected ';', but got ID('x')`

---

## 9. 示例程序（建议）

建议在 `examples/` 至少提供：

1. 表达式与赋值：

```c
a = 1 + 2 * 3;
b = (a + 4) / 2;
```

2. if-else：

```c
if (a > 0) {
  b = b + 1;
} else {
  b = b - 1;
}
```

3. while：

```c
while (a != 0) {
  a = a - 1;
}
```
