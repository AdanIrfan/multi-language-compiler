"""
C Compiler Module
Lexer → Parser (recursive descent) → Parse Tree → TAC → Parse Table
Supports: variables, assignments, if/else, while, for, functions, printf
"""

import re
from shared import Token, TT, ASTNode, TACGenerator, print_tokens, print_tree, print_parse_table

# ─────────────────────────────────────────────
# C Keywords
# ─────────────────────────────────────────────
C_KEYWORDS = {
    'int','float','char','double','void','long','short','unsigned','signed',
    'if','else','while','for','do','return','break','continue',
    'struct','union','typedef','enum','sizeof','static','extern','const',
    'printf','scanf','include','define','main'
}

# ─────────────────────────────────────────────
# C Lexer
# ─────────────────────────────────────────────
class CLexer:
    def __init__(self, source):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.tokens = []

    def error(self, ch):
        print(f"[Lexer Error] Unexpected character '{ch}' at line {self.line}")

    def peek(self, offset=1):
        i = self.pos + offset
        return self.source[i] if i < len(self.source) else ''

    def current(self):
        return self.source[self.pos] if self.pos < len(self.source) else ''

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n': self.line += 1
        return ch

    def add(self, type_, value):
        self.tokens.append(Token(type_, value, self.line))

    def tokenize(self):
        src = self.source
        self.pos = 0

        while self.pos < len(src):
            ch = src[self.pos]

            # Whitespace / newlines
            if ch in ' \t\r\n':
                if ch == '\n': self.line += 1
                self.pos += 1
                continue

            # Single-line comment
            if ch == '/' and self.peek() == '/':
                while self.pos < len(src) and src[self.pos] != '\n':
                    self.pos += 1
                continue

            # Multi-line comment
            if ch == '/' and self.peek() == '*':
                self.pos += 2
                while self.pos < len(src) - 1:
                    if src[self.pos] == '*' and src[self.pos+1] == '/':
                        self.pos += 2
                        break
                    if src[self.pos] == '\n': self.line += 1
                    self.pos += 1
                continue

            # Preprocessor directive
            if ch == '#':
                start = self.pos
                while self.pos < len(src) and src[self.pos] != '\n':
                    self.pos += 1
                self.add(TT.HASH, src[start:self.pos])
                continue

            # String literal
            if ch == '"':
                self.pos += 1
                s = ''
                while self.pos < len(src) and src[self.pos] != '"':
                    if src[self.pos] == '\\':
                        self.pos += 1
                        esc = src[self.pos] if self.pos < len(src) else ''
                        escape_map = {'n':'\n','t':'\t','r':'\r','\\':'\\','"':'"',"'"  :"'"}
                        s += escape_map.get(esc, '\\' + esc)
                    else:
                        s += src[self.pos]
                    self.pos += 1
                self.pos += 1
                self.add(TT.STR_LIT, s)
                continue

            # Char literal
            if ch == "'":
                self.pos += 1
                s = ''
                while self.pos < len(src) and src[self.pos] != "'":
                    s += src[self.pos]; self.pos += 1
                self.pos += 1
                self.add(TT.CHAR_LIT, s)
                continue

            # Number
            if ch.isdigit() or (ch == '.' and self.peek().isdigit()):
                start = self.pos
                is_float = False
                while self.pos < len(src) and (src[self.pos].isdigit() or src[self.pos] == '.'):
                    if src[self.pos] == '.': is_float = True
                    self.pos += 1
                val = src[start:self.pos]
                self.add(TT.FLOAT_LIT if is_float else TT.INT_LIT, val)
                continue

            # Identifier / keyword
            if ch.isalpha() or ch == '_':
                start = self.pos
                while self.pos < len(src) and (src[self.pos].isalnum() or src[self.pos] == '_'):
                    self.pos += 1
                word = src[start:self.pos]
                if word in C_KEYWORDS:
                    self.add(TT.KEYWORD, word)
                else:
                    self.add(TT.IDENT, word)
                continue

            # Two-char operators
            two = src[self.pos:self.pos+2]
            two_map = {
                '==': TT.EQ, '!=': TT.NEQ, '<=': TT.LTE, '>=': TT.GTE,
                '&&': TT.AND, '||': TT.OR, '++': TT.INC, '--': TT.DEC,
                '+=': TT.PLUS_EQ, '-=': TT.MINUS_EQ, '->': TT.ARROW,
            }
            if two in two_map:
                self.add(two_map[two], two)
                self.pos += 2
                continue

            # Single-char operators / delimiters
            one_map = {
                '+': TT.PLUS, '-': TT.MINUS, '*': TT.STAR, '/': TT.SLASH,
                '%': TT.PERCENT, '=': TT.ASSIGN, '<': TT.LT, '>': TT.GT,
                '!': TT.NOT, '(': TT.LPAREN, ')': TT.RPAREN,
                '{': TT.LBRACE, '}': TT.RBRACE, '[': TT.LBRACKET, ']': TT.RBRACKET,
                ';': TT.SEMI, ':': TT.COLON, ',': TT.COMMA, '.': TT.DOT,
            }
            if ch in one_map:
                self.add(one_map[ch], ch)
                self.pos += 1
                continue

            self.error(ch)
            self.pos += 1

        self.add(TT.EOF, 'EOF')
        return self.tokens


# ─────────────────────────────────────────────
# C Parser (Recursive Descent)
# ─────────────────────────────────────────────
class CParser:
    def __init__(self, tokens):
        self.tokens = [t for t in tokens if t.type not in (TT.HASH, TT.COMMENT)]
        self.pos    = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TT.EOF,'EOF')

    def peek(self, offset=1):
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else Token(TT.EOF,'EOF')

    def consume(self, type_=None, value=None):
        tok = self.current()
        if type_ and tok.type != type_:
            if not (type_ == TT.KEYWORD and tok.value == value):
                print(f"[Parser Error] Expected {type_}({value}) got {tok.type}({tok.value}) at line {tok.line}")
        if value and tok.value != value and tok.type != TT.EOF:
            if tok.value != value:
                pass  # lenient
        self.pos += 1
        return tok

    def match(self, type_=None, value=None):
        tok = self.current()
        if type_ and tok.type != type_: return False
        if value and tok.value != value: return False
        return True

    def parse(self):
        node = ASTNode("Program")
        while not self.match(TT.EOF):
            stmt = self.parse_top_level()
            if stmt: node.children.append(stmt)
        return node

    def parse_top_level(self):
        tok = self.current()
        # preprocessor already filtered; skip EOF/stray
        if tok.type == TT.EOF: return None
        # function or variable declaration
        if tok.type == TT.KEYWORD and tok.value in ('int','float','char','void','double','long','short'):
            return self.parse_decl_or_func()
        return self.parse_statement()

    def parse_decl_or_func(self):
        type_tok = self.consume()          # int / float / void …
        # 'main' is stored as KEYWORD — accept both IDENT and KEYWORD as function/var name
        tok = self.current()
        if tok.type in (TT.IDENT, TT.KEYWORD) and tok.value not in (
                'if','else','while','for','do','return','break','continue',
                'struct','union','typedef','enum','sizeof','static','extern','const'):
            name_tok = self.consume()
        else:
            name_tok = self.consume(TT.IDENT)
        if self.match(TT.LPAREN):          # function definition
            return self.parse_function(type_tok, name_tok)
        else:                              # variable declaration
            return self.parse_var_decl(type_tok, name_tok)

    def parse_function(self, type_tok, name_tok):
        node = ASTNode("FuncDef", value=name_tok.value)
        node.children.append(ASTNode("ReturnType", value=type_tok.value))
        self.consume(TT.LPAREN)
        params = ASTNode("Params")
        while not self.match(TT.RPAREN) and not self.match(TT.EOF):
            if self.current().type == TT.KEYWORD:
                pt = self.consume()
                pn = self.consume(TT.IDENT)
                params.children.append(ASTNode("Param", value=f"{pt.value} {pn.value}"))
            if self.match(TT.COMMA): self.consume()
        self.consume(TT.RPAREN)
        node.children.append(params)
        if self.match(TT.LBRACE):
            node.children.append(self.parse_block())
        return node

    def parse_block(self):
        node = ASTNode("Block")
        self.consume(TT.LBRACE)
        while not self.match(TT.RBRACE) and not self.match(TT.EOF):
            stmt = self.parse_statement()
            if stmt: node.children.append(stmt)
        self.consume(TT.RBRACE)
        return node

    def parse_var_decl(self, type_tok=None, name_tok=None):
        if type_tok is None: type_tok = self.consume()
        if name_tok is None: name_tok = self.consume(TT.IDENT)
        node = ASTNode("VarDecl", value=f"{type_tok.value} {name_tok.value}")
        if self.match(TT.ASSIGN):
            self.consume()
            node.children.append(self.parse_expr())
        self.consume(TT.SEMI)
        return node

    def parse_statement(self):
        tok = self.current()

        if tok.type == TT.KEYWORD and tok.value == 'if':
            return self.parse_if()
        if tok.type == TT.KEYWORD and tok.value == 'while':
            return self.parse_while()
        if tok.type == TT.KEYWORD and tok.value == 'for':
            return self.parse_for()
        if tok.type == TT.KEYWORD and tok.value == 'return':
            return self.parse_return()
        if tok.type == TT.KEYWORD and tok.value in ('int','float','char','double','long','short','unsigned'):
            return self.parse_var_decl()
        if tok.type == TT.KEYWORD and tok.value in ('printf','scanf'):
            return self.parse_func_call_stmt()
        if tok.type == TT.IDENT:
            return self.parse_assign_or_call()
        if tok.type == TT.LBRACE:
            return self.parse_block()
        if tok.type == TT.SEMI:
            self.consume(); return ASTNode("EmptyStmt")
        if tok.type == TT.KEYWORD and tok.value in ('break','continue'):
            self.consume(); self.consume(TT.SEMI)
            return ASTNode(tok.value.capitalize()+"Stmt")
        # skip unknown
        self.consume()
        return None

    def parse_if(self):
        self.consume()  # 'if'
        node = ASTNode("IfStmt")
        self.consume(TT.LPAREN)
        node.children.append(ASTNode("Condition", children=[self.parse_expr()]))
        self.consume(TT.RPAREN)
        node.children.append(self.parse_block() if self.match(TT.LBRACE) else self.parse_statement())
        if self.match(TT.KEYWORD) and self.current().value == 'else':
            self.consume()
            else_node = ASTNode("ElseClause")
            else_node.children.append(self.parse_block() if self.match(TT.LBRACE) else self.parse_statement())
            node.children.append(else_node)
        return node

    def parse_while(self):
        self.consume()  # 'while'
        node = ASTNode("WhileStmt")
        self.consume(TT.LPAREN)
        node.children.append(ASTNode("Condition", children=[self.parse_expr()]))
        self.consume(TT.RPAREN)
        node.children.append(self.parse_block() if self.match(TT.LBRACE) else self.parse_statement())
        return node

    def parse_for(self):
        self.consume()  # 'for'
        node = ASTNode("ForStmt")
        self.consume(TT.LPAREN)
        # init
        init = ASTNode("ForInit")
        if not self.match(TT.SEMI):
            if self.current().type == TT.KEYWORD:
                init.children.append(self.parse_var_decl())
            else:
                init.children.append(self.parse_expr())
                self.consume(TT.SEMI)
        else:
            self.consume(TT.SEMI)
        node.children.append(init)
        # condition
        cond = ASTNode("Condition")
        if not self.match(TT.SEMI):
            cond.children.append(self.parse_expr())
        self.consume(TT.SEMI)
        node.children.append(cond)
        # update — handle i++, i--, i+=x, i-=x, i=i+1
        upd = ASTNode("ForUpdate")
        if not self.match(TT.RPAREN):
            name = self.consume()   # variable name (IDENT or KEYWORD)
            if self.current().type == TT.INC:
                self.consume()
                upd.children.append(ASTNode("UnaryOp", value=f"{name.value}++"))
            elif self.current().type == TT.DEC:
                self.consume()
                upd.children.append(ASTNode("UnaryOp", value=f"{name.value}--"))
            elif self.current().type == TT.PLUS_EQ:
                self.consume()
                val = self.parse_expr()
                upd.children.append(ASTNode("Assignment", value=f"{name.value} +=", children=[val]))
            elif self.current().type == TT.MINUS_EQ:
                self.consume()
                val = self.parse_expr()
                upd.children.append(ASTNode("Assignment", value=f"{name.value} -=", children=[val]))
            elif self.current().type == TT.ASSIGN:
                self.consume()
                val = self.parse_expr()
                upd.children.append(ASTNode("Assignment", value=f"{name.value} =", children=[val]))
            else:
                upd.children.append(ASTNode("Identifier", value=name.value))
        self.consume(TT.RPAREN)
        node.children.append(upd)
        node.children.append(self.parse_block() if self.match(TT.LBRACE) else self.parse_statement())
        return node

    def parse_return(self):
        self.consume()  # 'return'
        node = ASTNode("ReturnStmt")
        if not self.match(TT.SEMI):
            node.children.append(self.parse_expr())
        self.consume(TT.SEMI)
        return node

    def parse_func_call_stmt(self):
        name = self.consume()
        node = ASTNode("FuncCall", value=name.value)
        self.consume(TT.LPAREN)
        while not self.match(TT.RPAREN) and not self.match(TT.EOF):
            node.children.append(self.parse_expr())
            if self.match(TT.COMMA): self.consume()
        self.consume(TT.RPAREN)
        self.consume(TT.SEMI)
        return node

    def parse_assign_or_call(self):
        name = self.consume(TT.IDENT)
        if self.match(TT.LPAREN):       # function call
            node = ASTNode("FuncCall", value=name.value)
            self.consume(TT.LPAREN)
            while not self.match(TT.RPAREN) and not self.match(TT.EOF):
                node.children.append(self.parse_expr())
                if self.match(TT.COMMA): self.consume()
            self.consume(TT.RPAREN)
            self.consume(TT.SEMI)
            return node
        if self.current().type in (TT.ASSIGN, TT.PLUS_EQ, TT.MINUS_EQ):
            op = self.consume()
            node = ASTNode("Assignment", value=f"{name.value} {op.value}")
            node.children.append(self.parse_expr())
            self.consume(TT.SEMI)
            return node
        if self.current().type in (TT.INC, TT.DEC):
            op = self.consume()
            self.consume(TT.SEMI)
            return ASTNode("UnaryOp", value=f"{name.value}{op.value}")
        self.consume(TT.SEMI)
        return ASTNode("ExprStmt", value=name.value)

    # ── Expression parsing (precedence climbing) ──────────
    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.match(TT.OR):
            op = self.consume()
            right = self.parse_and()
            left = ASTNode("BinOp", value=op.value, children=[left, right])
        return left

    def parse_and(self):
        left = self.parse_equality()
        while self.match(TT.AND):
            op = self.consume()
            right = self.parse_equality()
            left = ASTNode("BinOp", value=op.value, children=[left, right])
        return left

    def parse_equality(self):
        left = self.parse_relational()
        while self.current().type in (TT.EQ, TT.NEQ):
            op = self.consume()
            right = self.parse_relational()
            left = ASTNode("BinOp", value=op.value, children=[left, right])
        return left

    def parse_relational(self):
        left = self.parse_additive()
        while self.current().type in (TT.LT, TT.GT, TT.LTE, TT.GTE):
            op = self.consume()
            right = self.parse_additive()
            left = ASTNode("BinOp", value=op.value, children=[left, right])
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current().type in (TT.PLUS, TT.MINUS):
            op = self.consume()
            right = self.parse_multiplicative()
            left = ASTNode("BinOp", value=op.value, children=[left, right])
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.current().type in (TT.STAR, TT.SLASH, TT.PERCENT):
            op = self.consume()
            right = self.parse_unary()
            left = ASTNode("BinOp", value=op.value, children=[left, right])
        return left

    def parse_unary(self):
        if self.current().type in (TT.NOT, TT.MINUS):
            op = self.consume()
            return ASTNode("UnaryOp", value=op.value, children=[self.parse_unary()])
        return self.parse_primary()

    def parse_primary(self):
        tok = self.current()
        if tok.type in (TT.INT_LIT, TT.FLOAT_LIT):
            self.consume()
            return ASTNode("Literal", value=tok.value)
        if tok.type == TT.STR_LIT:
            self.consume()
            return ASTNode("StrLiteral", value=tok.value)
        if tok.type == TT.CHAR_LIT:
            self.consume()
            return ASTNode("CharLiteral", value=tok.value)
        if tok.type == TT.IDENT:
            name = self.consume()
            if self.match(TT.LPAREN):
                node = ASTNode("FuncCall", value=name.value)
                self.consume(TT.LPAREN)
                while not self.match(TT.RPAREN) and not self.match(TT.EOF):
                    node.children.append(self.parse_expr())
                    if self.match(TT.COMMA): self.consume()
                self.consume(TT.RPAREN)
                return node
            return ASTNode("Identifier", value=name.value)
        if tok.type == TT.LPAREN:
            self.consume()
            node = self.parse_expr()
            self.consume(TT.RPAREN)
            return ASTNode("Grouped", children=[node])
        if tok.type == TT.KEYWORD and tok.value in ('true','false'):
            self.consume()
            return ASTNode("BoolLiteral", value=tok.value)
        # skip unknown token gracefully
        self.consume()
        return ASTNode("Unknown", value=tok.value)


# ─────────────────────────────────────────────
# C TAC Generator
# ─────────────────────────────────────────────
class CTACGen(TACGenerator):
    def gen(self, node):
        t = node.type

        if t == "Program":
            for c in node.children: self.gen(c)

        elif t == "FuncDef":
            self.emit(f"FUNC_BEGIN {node.value}")
            for c in node.children: self.gen(c)
            self.emit(f"FUNC_END {node.value}")

        elif t == "Block":
            for c in node.children: self.gen(c)

        elif t == "VarDecl":
            if node.children:
                val = self.gen_expr(node.children[0])
                name = node.value.split()[-1]
                self.emit(f"{name} = {val}")

        elif t == "Assignment":
            parts = node.value.split()
            name, op = parts[0], parts[1]
            val = self.gen_expr(node.children[0])
            if op == '=':
                self.emit(f"{name} = {val}")
            elif op == '+=':
                self.emit(f"{name} = {name} + {val}")
            elif op == '-=':
                self.emit(f"{name} = {name} - {val}")

        elif t == "IfStmt":
            cond = self.gen_expr(node.children[0].children[0])
            lelse = self.new_label()
            lend  = self.new_label()
            self.emit(f"IF NOT {cond} GOTO {lelse}")
            self.gen(node.children[1])
            self.emit(f"GOTO {lend}")
            self.emit(f"{lelse}:")
            if len(node.children) > 2:
                self.gen(node.children[2])
            self.emit(f"{lend}:")

        elif t == "WhileStmt":
            lstart = self.new_label()
            lend   = self.new_label()
            self.emit(f"{lstart}:")
            cond = self.gen_expr(node.children[0].children[0])
            self.emit(f"IF NOT {cond} GOTO {lend}")
            self.gen(node.children[1])
            self.emit(f"GOTO {lstart}")
            self.emit(f"{lend}:")

        elif t == "ForStmt":
            self.gen(node.children[0])   # init
            lstart = self.new_label()
            lend   = self.new_label()
            self.emit(f"{lstart}:")
            if node.children[1].children:
                cond = self.gen_expr(node.children[1].children[0])
                self.emit(f"IF NOT {cond} GOTO {lend}")
            self.gen(node.children[3])   # body
            # update step — emit via gen() so UnaryOp i++ works
            for upd_child in node.children[2].children:
                self.gen(upd_child)
            self.emit(f"GOTO {lstart}")
            self.emit(f"{lend}:")

        elif t == "ReturnStmt":
            if node.children:
                val = self.gen_expr(node.children[0])
                self.emit(f"RETURN {val}")
            else:
                self.emit("RETURN")

        elif t == "FuncCall":
            args = [self.gen_expr(c) for c in node.children]
            self.emit(f"CALL {node.value}({', '.join(args)})")

        elif t in ("Params","ReturnType","ElseClause","ForInit","ForUpdate","Condition","EmptyStmt"):
            for c in node.children: self.gen(c)

        elif t == "UnaryOp":
            parts = node.value.split()
            if '++' in node.value:
                name = node.value.replace('++','').strip()
                self.emit(f"{name} = {name} + 1")
            elif '--' in node.value:
                name = node.value.replace('--','').strip()
                self.emit(f"{name} = {name} - 1")

    def gen_expr(self, node):
        t = node.type
        if t == "Literal":      return str(node.value)
        if t == "StrLiteral":   return f'"{node.value}"'
        if t == "CharLiteral":  return f"'{node.value}'"
        if t == "BoolLiteral":  return str(node.value)
        if t == "Identifier":   return str(node.value)
        if t == "Grouped":      return self.gen_expr(node.children[0])
        if t == "UnaryOp":
            v = self.gen_expr(node.children[0])
            tmp = self.new_temp()
            self.emit(f"{tmp} = {node.value}{v}")
            return tmp
        if t == "BinOp":
            l = self.gen_expr(node.children[0])
            r = self.gen_expr(node.children[1])
            tmp = self.new_temp()
            self.emit(f"{tmp} = {l} {node.value} {r}")
            return tmp
        if t == "FuncCall":
            args = [self.gen_expr(c) for c in node.children]
            tmp = self.new_temp()
            self.emit(f"{tmp} = CALL {node.value}({', '.join(args)})")
            return tmp
        return "?"


# ─────────────────────────────────────────────
# C Parse Table (LL(1) representative)
# ─────────────────────────────────────────────
def get_c_parse_table():
    return {
        "Program":     {"int":"TopDecl", "void":"TopDecl", "float":"TopDecl", "$":"ε"},
        "TopDecl":     {"int":"Type id (Params) Block | Type id = Expr ;", "void":"Type id (Params) Block", "float":"Type id = Expr ;"},
        "Type":        {"int":"int", "float":"float", "void":"void", "char":"char"},
        "Stmt":        {"if":"IfStmt", "while":"WhileStmt", "for":"ForStmt", "return":"return Expr ;", "id":"id = Expr ; | FuncCall ;", "{":"Block", ";":"ε"},
        "IfStmt":      {"if":"if ( Expr ) Stmt ElseClause"},
        "ElseClause":  {"else":"else Stmt", "id":"ε", ";":"ε", "}":"ε"},
        "WhileStmt":   {"while":"while ( Expr ) Stmt"},
        "ForStmt":     {"for":"for ( ForInit Expr ; Expr ) Stmt"},
        "Expr":        {"id":"Expr → AddExpr RelOp AddExpr | AddExpr", "num":"AddExpr", "(":"( Expr )"},
        "AddExpr":     {"id":"MulExpr AddExpr'", "num":"MulExpr AddExpr'"},
        "AddExpr'":    {"+":"+ MulExpr AddExpr'", "-":"- MulExpr AddExpr'", ")":"ε", ";":"ε"},
        "MulExpr":     {"id":"Primary MulExpr'", "num":"Primary MulExpr'"},
        "MulExpr'":    {"*":"* Primary MulExpr'", "/":"/ Primary MulExpr'", "+":"ε", ")":"ε", ";":"ε"},
        "Primary":     {"id":"id", "num":"num", "(":"( Expr )"},
    }


# ─────────────────────────────────────────────
# C AST Interpreter — walks the AST and runs it
# ─────────────────────────────────────────────

class ReturnException(Exception):
    def __init__(self, value): self.value = value

class BreakException(Exception): pass
class ContinueException(Exception): pass

class CASTInterpreter:
    def __init__(self, tree):
        self.tree    = tree
        self.output  = []
        self.globals = {}          # global scope
        self.functions = {}        # name -> FuncDef node
        self.call_stack = []       # list of dicts (local scopes)
        self._collect_functions(tree)

    def _collect_functions(self, node):
        for child in node.children:
            if child and child.type == "FuncDef":
                self.functions[child.value] = child

    # ── scope helpers ────────────────────────
    def _env(self):
        return self.call_stack[-1] if self.call_stack else self.globals

    def _get(self, name):
        if self.call_stack:
            if name in self.call_stack[-1]: return self.call_stack[-1][name]
        return self.globals.get(name, 0)

    def _set(self, name, value):
        if self.call_stack:
            self.call_stack[-1][name] = value
        else:
            self.globals[name] = value

    # ── entry point ──────────────────────────
    def run(self):
        try:
            self._call_func("main", [])
        except ReturnException:
            pass
        except Exception as e:
            self.output.append(f"[Runtime error: {e}]")
        return "".join(self.output)

    # ── function call ─────────────────────────
    def _call_func(self, name, arg_values):
        # built-ins
        if name == "printf":
            self._builtin_printf(arg_values)
            return 0
        if name == "scanf":
            return 0
        if name not in self.functions:
            return 0
        node = self.functions[name]
        # bind params
        local = {}
        params_node = next((c for c in node.children if c and c.type == "Params"), None)
        if params_node:
            for i, param in enumerate(params_node.children):
                pname = param.value.split()[-1]
                local[pname] = arg_values[i] if i < len(arg_values) else 0
        self.call_stack.append(local)
        ret = 0
        try:
            block = next((c for c in node.children if c and c.type == "Block"), None)
            if block:
                self._exec_block(block)
        except ReturnException as r:
            ret = r.value
        finally:
            self.call_stack.pop()
        return ret

    def _builtin_printf(self, args):
        if not args: return
        fmt = str(args[0])
        rest = args[1:]
        result = []
        i = 0; ai = 0
        while i < len(fmt):
            if fmt[i] == '%' and i+1 < len(fmt):
                spec = fmt[i+1]
                val = rest[ai] if ai < len(rest) else 0
                ai += 1
                if spec == 'd' or spec == 'i':
                    result.append(str(int(val)))
                elif spec == 'f':
                    result.append(f"{float(val):.6f}")
                elif spec == 's':
                    result.append(str(val))
                elif spec == 'c':
                    result.append(chr(int(val)))
                else:
                    result.append('%' + spec)
                i += 2
            else:
                result.append(fmt[i])
                i += 1
        self.output.append("".join(result))

    # ── statement executor ────────────────────
    def _exec_block(self, node):
        for child in node.children:
            if child: self._exec_stmt(child)

    def _exec_stmt(self, node):
        t = node.type

        if t == "Block":
            self._exec_block(node)

        elif t == "VarDecl":
            name = node.value.split()[-1]
            val = self._eval(node.children[0]) if node.children else 0
            self._set(name, val)

        elif t == "Assignment":
            parts = node.value.split()
            name, op = parts[0], parts[1]
            val = self._eval(node.children[0])
            if op == '=':   self._set(name, val)
            elif op == '+=': self._set(name, self._get(name) + val)
            elif op == '-=': self._set(name, self._get(name) - val)

        elif t == "IfStmt":
            cond = self._eval(node.children[0].children[0])
            if cond:
                self._exec_stmt(node.children[1])
            else:
                for child in node.children[2:]:
                    if child and child.type == "ElseClause":
                        self._exec_stmt(child.children[0])

        elif t == "WhileStmt":
            limit = 0
            while self._eval(node.children[0].children[0]) and limit < 10000:
                limit += 1
                try:
                    self._exec_stmt(node.children[1])
                except BreakException: break
                except ContinueException: continue

        elif t == "ForStmt":
            # init
            if node.children[0].children:
                self._exec_stmt(node.children[0].children[0])
            limit = 0
            while limit < 10000:
                limit += 1
                # condition
                if node.children[1].children:
                    if not self._eval(node.children[1].children[0]):
                        break
                # body
                try:
                    self._exec_stmt(node.children[3])
                except BreakException: break
                except ContinueException: pass
                # update
                for upd in node.children[2].children:
                    if upd: self._exec_stmt(upd)

        elif t == "ReturnStmt":
            val = self._eval(node.children[0]) if node.children else 0
            raise ReturnException(val)

        elif t == "FuncCall":
            args = [self._eval(c) for c in node.children]
            self._call_func(node.value, args)

        elif t == "UnaryOp":
            v = node.value
            if '++' in v:
                name = v.replace('++', '').strip()
                self._set(name, self._get(name) + 1)
            elif '--' in v:
                name = v.replace('--', '').strip()
                self._set(name, self._get(name) - 1)

        elif t == "BreakStmt":    raise BreakException()
        elif t == "ContinueStmt": raise ContinueException()

        elif t in ("EmptyStmt", "ReturnType", "Params", "Param"): pass

    # ── expression evaluator ──────────────────
    def _eval(self, node):
        if node is None: return 0
        t = node.type

        if t == "Literal":
            try: return int(node.value)
            except: return float(node.value)

        if t == "StrLiteral":  return node.value
        if t == "CharLiteral": return ord(node.value[0]) if node.value else 0
        if t == "BoolLiteral": return 1 if node.value == 'true' else 0
        if t == "Identifier":  return self._get(node.value)
        if t == "Grouped":     return self._eval(node.children[0])

        if t == "UnaryOp":
            if node.children:
                v = self._eval(node.children[0])
                if node.value == '-': return -v
                if node.value == '!': return int(not v)
            return 0

        if t == "BinOp":
            L = self._eval(node.children[0])
            R = self._eval(node.children[1])
            op = node.value
            try:
                if op == '+':  return L + R
                if op == '-':  return L - R
                if op == '*':  return L * R
                if op == '/':  return int(L / R) if isinstance(L,int) and isinstance(R,int) else L/R
                if op == '%':  return int(L) % int(R)
                if op == '<':  return int(L < R)
                if op == '>':  return int(L > R)
                if op == '<=': return int(L <= R)
                if op == '>=': return int(L >= R)
                if op == '==': return int(L == R)
                if op == '!=': return int(L != R)
                if op == '&&': return int(bool(L) and bool(R))
                if op == '||': return int(bool(L) or  bool(R))
            except: return 0

        if t == "FuncCall":
            args = [self._eval(c) for c in node.children]
            return self._call_func(node.value, args)

        return 0


def simulate_c(tree):
    interp = CASTInterpreter(tree)
    result = interp.run()
    if not result.strip():
        return "[C simulation] No output produced."
    return result


# ─────────────────────────────────────────────
# Main C Compiler class
# ─────────────────────────────────────────────
class CCompiler:
    def __init__(self, code):
        self.code = code

    def compile(self):
        print("\n" + "="*60)
        print("  C COMPILER — COMPILATION STARTED")
        print("="*60)

        # 1. Lexing
        print("\n[1/5] LEXICAL ANALYSIS (Scanner)")
        lexer  = CLexer(self.code)
        tokens = lexer.tokenize()
        print_tokens(tokens)

        # 2. Parsing
        print("\n[2/5] SYNTAX ANALYSIS (Parser)")
        parser = CParser(tokens)
        tree   = parser.parse()

        # 3. Parse Tree
        print("\n[3/5] PARSE TREE")
        print("\n" + "-"*45)
        print_tree(tree)
        print("-"*45)

        # 4. TAC
        print("\n[4/5] THREE-ADDRESS CODE (TAC)")
        tac = CTACGen()
        tac.gen(tree)
        tac.print_tac()

        # 5. Parse Table
        print("\n[5/5] PARSE TABLE (LL(1))")
        print_parse_table(get_c_parse_table(), title="C Grammar Parse Table")

        # 6. Output / Result
        print("\n[OUTPUT / RESULT]")
        print("-"*45)
        result = simulate_c(tree)
        print(result)
        print("-"*45)
        print("\n✅ C compilation complete.")
