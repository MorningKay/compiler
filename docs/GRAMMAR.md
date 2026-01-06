# MiniLang 文法定稿（GRAMMAR）

本文档给出 MiniLang 的推荐 BNF 文法（可用于自动生成 LALR(1) ACTION/GOTO 表）。
实现允许做等价改写，但必须满足 `docs/SPEC.md` 中的语言特性与优先级要求。

---

## 1. 终结符（Terminals）与 Token 映射

> 以 Lexer 输出的 token 类型为准；下述为推荐命名（允许你在代码里用不同枚举名，但需一致）。

关键字：
- `IF`（"if"）
- `ELSE`（"else"）
- `WHILE`（"while"）
- `AND`（"and"）
- `OR`（"or"）
- `NOT`（"not" 可选，建议实现）

标识符/字面量：
- `ID`
- `NUM`

运算符与界符：
- `ASSIGN`（"="）
- `PLUS`（"+"）
- `MINUS`（"-"）
- `MUL`（"*"）
- `DIV`（"/"）
- `EQ`（"=="）
- `NE`（"!="）
- `LT`（"<"）
- `GT`（">"）
- `LPAREN`（"("）
- `RPAREN`（")"）
- `LBRACE`（"{"）
- `RBRACE`（"}"）
- `SEMI`（";"）
- `EOF`（输入结束标记；实现内部统一使用终结符名 `EOF`，在导出的表格/日志中可显示为 `$` 以贴合教材）

---

## 2. 非终结符（Nonterminals）

- `Program`
- `StmtList`
- `Stmt`
- `Matched`
- `Unmatched`
- `AssignStmt`
- `WhileStmt`
- `Block`
- `Expr`
- `Term`
- `Factor`
- `Bool`
- `OrExpr`
- `AndExpr`
- `NotExpr`
- `RelExpr`

---

## 3. 推荐文法（BNF）

### 3.1 增广文法（用于 LR）
```bnf
S'       → Program EOF
Program  → StmtList
```

### 3.2 语句序列与语句

> 说明：这里使用右递归的 `StmtList`，便于实现与减少部分状态复杂度。
> 空块 `{}` 由 `StmtList → ε` 支持。

```bnf
StmtList → Stmt StmtList
StmtList → ε

Stmt     → Matched
Stmt     → Unmatched
```

### 3.3 解决 dangling-else（关键）

> 这是规避冲突的核心：将语句分为 **Matched / Unmatched** 两类，
> 经典写法能避免 `if (...) if (...) ... else ...` 的 shift/reduce 冲突。

```bnf
Matched   → AssignStmt
Matched   → WhileStmt
Matched   → Block
Matched   → IF LPAREN Bool RPAREN Matched ELSE Matched

Unmatched → IF LPAREN Bool RPAREN Stmt
Unmatched → IF LPAREN Bool RPAREN Matched ELSE Unmatched
```

### 3.4 基本语句

```bnf
AssignStmt → ID ASSIGN Expr SEMI

WhileStmt  → WHILE LPAREN Bool RPAREN Stmt

Block      → LBRACE StmtList RBRACE
```

---

## 4. 表达式文法（算术）

优先级与结合性：

* `* /` 高于 `+ -`
* 都是左结合
* 支持括号

```bnf
Expr   → Expr PLUS Term
Expr   → Expr MINUS Term
Expr   → Term

Term   → Term MUL Factor
Term   → Term DIV Factor
Term   → Factor

Factor → ID
Factor → NUM
Factor → LPAREN Expr RPAREN
```

> 注：本版本不包含一元负号（`-x`）。如需扩展，请在 `Factor` 层加入一元产生式并同步更新优先级说明。

---

## 5. 布尔表达式文法（关系 + 逻辑）

优先级与结合性（从高到低）：

* 括号
* `not`（若实现）
* 关系 `== != < >`
* `and`
* `or`

同时允许布尔括号：`( Bool )`，便于书写复杂条件。

```bnf
Bool    → OrExpr

OrExpr  → OrExpr OR AndExpr
OrExpr  → AndExpr

AndExpr → AndExpr AND NotExpr
AndExpr → NotExpr

NotExpr → NOT NotExpr
NotExpr → LPAREN Bool RPAREN
NotExpr → RelExpr

RelExpr → Expr EQ Expr
RelExpr → Expr NE Expr
RelExpr → Expr LT Expr
RelExpr → Expr GT Expr
```

约束（由文法天然保证）：

* 不支持链式比较（如 `a < b < c`），因为 `RelExpr` 只允许 `Expr relop Expr`

---

## 6. 冲突与规避策略说明

### 6.1 dangling-else 冲突

* 问题：`if (c1) if (c2) S1 else S2`
* 解决：使用 `Matched/Unmatched` 文法（见 3.3）
* 效果：`else` 总是绑定最近的未匹配 `if`，且 LR 表更稳定

### 6.2 StmtList 的递归形式

* 右递归：`StmtList → Stmt StmtList | ε`
* 优点：实现简单；对 LR 无硬性差别，但一般更利于工程输出一致性

### 6.3 逻辑与关系优先级

* 通过分层（OrExpr/AndExpr/NotExpr/RelExpr）编码优先级
* 不依赖“优先级声明”机制（因为我们不是用 yacc/bison），更利于自研 LALR(1)

---

## 7. 产生式编号（建议）

> 语法分析表 reduce 动作需要引用产生式编号。
> 实现中建议在 `grammar.py` 中按如下顺序编号（示例编号，你可以调整，但需固定且可导出）。

建议编号（示例）：

1. S' → Program EOF
2. Program → StmtList
3. StmtList → Stmt StmtList
4. StmtList → ε
5. Stmt → Matched
6. Stmt → Unmatched
7. Matched → AssignStmt
8. Matched → WhileStmt
9. Matched → Block
10. Matched → IF ( Bool ) Matched ELSE Matched
11. Unmatched → IF ( Bool ) Stmt
12. Unmatched → IF ( Bool ) Matched ELSE Unmatched
13. AssignStmt → ID = Expr ;
14. WhileStmt → WHILE ( Bool ) Stmt
15. Block → { StmtList }

算术与布尔部分继续顺序编号即可。

---

## 8. 语义动作挂接点（只给接口，不在本文展开）

本项目会生成四元式与控制流（回填），语义动作通常挂在以下产生式：

* 算术：`Expr/Term` 的二元运算产生式（生成临时变量）
* 关系：`RelExpr`（生成条件跳转所需结构：true/false list 或条件表达式临时结果）
* 逻辑：`OrExpr/AndExpr/NotExpr`（实现短路时需要 backpatch；不短路则可转化为显式计算）
* if/while：`Matched/Unmatched` 对应产生式（生成 label/goto/ifFalse 并回填 nextList）

具体 IR 形式与 backpatch 规则请见 `docs/IR.md`（后续生成）。

---

## 9. 最小可通过样例（建议用于验收）

1. 赋值与优先级：

```c
a = 1 + 2 * 3;
b = (a + 4) / 2;
```

2. if-else（含嵌套）：

```c
if (a > 0) {
  if (b != 0) c = c + 1;
  else c = c - 1;
} else {
  c = 0;
}
```

3. while：

```c
while (a != 0) {
  a = a - 1;
}
```
