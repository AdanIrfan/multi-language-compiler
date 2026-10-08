"""
Python Compiler Module
Handles: indentation-based blocks, if/elif/else, while, for-in, def, print, return
"""

import re
from shared import Token, TT, ASTNode, TACGenerator, print_tokens, print_tree, print_parse_table

# ─────────────────────────────────────────────
# Python Keywords
# ─────────────────────────────────────────────
PY_KEYWORDS = {
    'if','elif','else','while','for','in','not','and','or','is',
    'def','return','class','import','from','as','pass','break',
    'continue','True','False','None','print','range','len','input',
    'int','float','str','bool','list','dict','set','type','lambda',
    'try','except','finally','raise','with','yield','del','global',
    'nonlocal','assert','self','super'
}

# ─────────────────────────────────────────────
# Python Lexer (with INDENT / DEDENT)
# ─────────────────────────────────────────────
class PythonLexer:
    def __init__(self, source):
        self.source = source
        self.tokens = []
        self.line   = 1

    def tokenize(self):
        lines = self.source.split('\n')
        indent_stack = [0]
        self.line = 0

        for raw_line in lines:
            self.line += 1

            # blank / comment only line
            stripped = raw_line.lstrip()
            if not stripped or stripped.startswith('#'):
                continue

            # measure indent
            indent = len(raw_line) - len(raw_line.lstrip())

            if indent > indent_stack[-1]:
                indent_stack.append(indent)
                self.tokens.append(Token(TT.INDENT, indent, self.line))
            else:
                while indent < indent_stack[-1]:
                    indent_stack.pop()
                    self.tokens.append(Token(TT.DEDENT, indent, self.line))

            # lex the stripped line
            self._lex_line(stripped, self.line)
            self.tokens.append(Token(TT.NEWLINE, '\\n', self.line))

        # close remaining indents
        while len(indent_stack) > 1:
            indent_stack.pop()
            self.tokens.append(Token(TT.DEDENT, 0, self.line))

        self.tokens.append(Token(TT.EOF, 'EOF', self.line))
        return self.tokens

    def _lex_line(self, line, lineno):
        pos = 0
        while pos < len(line):
            ch = line[pos]

            if ch in ' \t':
                pos += 1; continue

            if ch == '#':
                break  # rest of line is comment

            # String literal (single or double, single-char quote)
            if ch in ('"', "'"):
                quote = ch
                pos += 1
                s = ''
                while pos < len(line) and line[pos] != quote:
                    if line[pos] == '\\': pos += 1
                    if pos < len(line): s += line[pos]
                    pos += 1
                pos += 1  # closing quote
                self.tokens.append(Token(TT.STR_LIT, s, lineno))
                continue

            # Number
            if ch.isdigit() or (ch == '.' and pos+1 < len(line) and line[pos+1].isdigit()):
                start = pos
                is_float = False
                while pos < len(line) and (line[pos].isdigit() or line[pos] == '.'):
                    if line[pos] == '.': is_float = True
                    pos += 1
                val = line[start:pos]
                self.tokens.append(Token(TT.FLOAT_LIT if is_float else TT.INT_LIT, val, lineno))
                continue

            # Identifier / keyword
            if ch.isalpha() or ch == '_':
                start = pos
                while pos < len(line) and (line[pos].isalnum() or line[pos] == '_'):
                    pos += 1
                word = line[start:pos]
                ttype = TT.KEYWORD if word in PY_KEYWORDS else TT.IDENT
                self.tokens.append(Token(ttype, word, lineno))
                continue

            # Two-char operators
            two = line[pos:pos+2]
            two_map = {
                '==': TT.EQ, '!=': TT.NEQ, '<=': TT.LTE, '>=': TT.GTE,
                '**': TT.STAR,  # power operator (reusing STAR for display)
                '//': TT.SLASH, # floor div
                '+=': TT.PLUS_EQ, '-=': TT.MINUS_EQ,
                '->': TT.ARROW,
            }
            if two in two_map:
                self.tokens.append(Token(two_map[two], two, lineno))
                pos += 2; continue

            # Single-char
            one_map = {
                '+': TT.PLUS, '-': TT.MINUS, '*': TT.STAR, '/': TT.SLASH,
                '%': TT.PERCENT, '=': TT.ASSIGN, '<': TT.LT, '>': TT.GT,
                '!': TT.NOT, '(': TT.LPAREN, ')': TT.RPAREN,
                '[': TT.LBRACKET, ']': TT.RBRACKET,
                '{': TT.LBRACE,   '}': TT.RBRACE,
                ':': TT.COLON, ',': TT.COMMA, '.': TT.DOT,
            }
            if ch in one_map:
                self.tokens.append(Token(one_map[ch], ch, lineno))
                pos += 1; continue

            pos += 1  # skip unknown


# ─────────────────────────────────────────────
# Python Parser (Recursive Descent)
# ─────────────────────────────────────────────
class PythonParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos    = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else Token(TT.EOF,'EOF')

    def peek(self, offset=1):
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else Token(TT.EOF,'EOF')

    def consume(self, type_=None, value=None):
        tok = self.current()
        self.pos += 1
        return tok

    def match(self, type_=None, value=None):
        tok = self.current()
        if type_ and tok.type != type_: return False
        if value and tok.value != value: return False
        return True

    def skip_newlines(self):
        while self.match(TT.NEWLINE): self.consume()

    def parse(self):
        node = ASTNode("Program")
        self.skip_newlines()
        while not self.match(TT.EOF):
            stmt = self.parse_statement()
            if stmt: node.children.append(stmt)
            self.skip_newlines()
        return node

    def parse_block(self):
        node = ASTNode("Block")
        self.consume(TT.INDENT)
        self.skip_newlines()
        while not self.match(TT.DEDENT) and not self.match(TT.EOF):
            stmt = self.parse_statement()
            if stmt: node.children.append(stmt)
            self.skip_newlines()
        if self.match(TT.DEDENT): self.consume()
        return node

    def parse_statement(self):
        tok = self.current()

        if tok.type == TT.KEYWORD and tok.value == 'if':
            return self.parse_if()
        if tok.type == TT.KEYWORD and tok.value == 'while':
            return self.parse_while()
        if tok.type == TT.KEYWORD and tok.value == 'for':
            return self.parse_for()
        if tok.type == TT.KEYWORD and tok.value == 'def':
            return self.parse_def()
        if tok.type == TT.KEYWORD and tok.value == 'return':
            return self.parse_return()
        if tok.type == TT.KEYWORD and tok.value == 'print':
            return self.parse_print()
        if tok.type == TT.KEYWORD and tok.value in ('break','continue','pass'):
            self.consume()
            self.consume(TT.NEWLINE)
            return ASTNode(tok.value.capitalize()+"Stmt")
        if tok.type in (TT.IDENT, TT.KEYWORD):
            return self.parse_assign_or_expr()
        if tok.type in (TT.NEWLINE, TT.INDENT, TT.DEDENT):
            self.consume(); return None
        self.consume(); return None

    def parse_if(self):
        self.consume()   # 'if'
        node = ASTNode("IfStmt")
        node.children.append(ASTNode("Condition", children=[self.parse_expr()]))
        self.consume(TT.COLON)
        self.consume(TT.NEWLINE)
        node.children.append(self.parse_block())
        self.skip_newlines()
        # elif chain
        while self.match(TT.KEYWORD) and self.current().value == 'elif':
            self.consume()
            elif_node = ASTNode("ElifClause")
            elif_node.children.append(ASTNode("Condition", children=[self.parse_expr()]))
            self.consume(TT.COLON)
            self.consume(TT.NEWLINE)
            elif_node.children.append(self.parse_block())
            node.children.append(elif_node)
            self.skip_newlines()
        if self.match(TT.KEYWORD) and self.current().value == 'else':
            self.consume()
            self.consume(TT.COLON)
            self.consume(TT.NEWLINE)
            else_node = ASTNode("ElseClause")
            else_node.children.append(self.parse_block())
            node.children.append(else_node)
        return node

    def parse_while(self):
        self.consume()   # 'while'
        node = ASTNode("WhileStmt")
        node.children.append(ASTNode("Condition", children=[self.parse_expr()]))
        self.consume(TT.COLON)
        self.consume(TT.NEWLINE)
        node.children.append(self.parse_block())
        return node

    def parse_for(self):
        self.consume()   # 'for'
        node = ASTNode("ForStmt")
        var = self.consume()   # loop variable
        node.children.append(ASTNode("LoopVar", value=var.value))
        self.consume()         # 'in'
        node.children.append(ASTNode("Iterable", children=[self.parse_expr()]))
        self.consume(TT.COLON)
        self.consume(TT.NEWLINE)
        node.children.append(self.parse_block())
        return node

    def parse_def(self):
        self.consume()   # 'def'
        name = self.consume()
        node = ASTNode("FuncDef", value=name.value)
        self.consume(TT.LPAREN)
        params = ASTNode("Params")
        while not self.match(TT.RPAREN) and not self.match(TT.EOF):
            params.children.append(ASTNode("Param", value=self.consume().value))
            if self.match(TT.COMMA): self.consume()
        self.consume(TT.RPAREN)
        self.consume(TT.COLON)
        self.consume(TT.NEWLINE)
        node.children.append(params)
        node.children.append(self.parse_block())
        return node

    def parse_return(self):
        self.consume()   # 'return'
        node = ASTNode("ReturnStmt")
        if not self.match(TT.NEWLINE) and not self.match(TT.EOF):
            node.children.append(self.parse_expr())
        if self.match(TT.NEWLINE): self.consume()
        return node

    def parse_print(self):
        self.consume()   # 'print'
        node = ASTNode("PrintStmt")
        self.consume(TT.LPAREN)
        while not self.match(TT.RPAREN) and not self.match(TT.EOF) and not self.match(TT.NEWLINE):
            node.children.append(self.parse_expr())
            if self.match(TT.COMMA): self.consume()
        if self.match(TT.RPAREN): self.consume()
        if self.match(TT.NEWLINE): self.consume()
        return node

    def parse_assign_or_expr(self):
        left = self.parse_expr()
        if self.match(TT.ASSIGN):
            self.consume()
            right = self.parse_expr()
            node = ASTNode("Assignment")
            node.children = [left, right]
            if self.match(TT.NEWLINE): self.consume()
            return node
        if self.match(TT.PLUS_EQ) or self.match(TT.MINUS_EQ):
            op = self.consume()
            right = self.parse_expr()
            node = ASTNode("AugAssign", value=op.value)
            node.children = [left, right]
            if self.match(TT.NEWLINE): self.consume()
            return node
        if self.match(TT.NEWLINE): self.consume()
        return ASTNode("ExprStmt", children=[left])

    # ── Expression parsing ──────────────────────────────────
    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.match(TT.KEYWORD, 'or'):
            self.consume()
            right = self.parse_and()
            left = ASTNode("BinOp", value="or", children=[left, right])
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.match(TT.KEYWORD, 'and'):
            self.consume()
            right = self.parse_not()
            left = ASTNode("BinOp", value="and", children=[left, right])
        return left

    def parse_not(self):
        if self.match(TT.KEYWORD, 'not'):
            self.consume()
            return ASTNode("UnaryOp", value="not", children=[self.parse_not()])
        return self.parse_comparison()

    def parse_comparison(self):
        left = self.parse_additive()
        while self.current().type in (TT.LT, TT.GT, TT.LTE, TT.GTE, TT.EQ, TT.NEQ):
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
        if self.current().type in (TT.MINUS, TT.NOT):
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
        if tok.type == TT.KEYWORD and tok.value in ('True','False','None'):
            self.consume()
            return ASTNode("BoolLiteral", value=tok.value)
        if tok.type in (TT.IDENT, TT.KEYWORD):
            name = self.consume()
            if self.match(TT.LPAREN):
                self.consume()
                node = ASTNode("FuncCall", value=name.value)
                while not self.match(TT.RPAREN) and not self.match(TT.EOF) and not self.match(TT.NEWLINE):
                    node.children.append(self.parse_expr())
                    if self.match(TT.COMMA): self.consume()
                if self.match(TT.RPAREN): self.consume()
                return node
            return ASTNode("Identifier", value=name.value)
        if tok.type == TT.LPAREN:
            self.consume()
            node = self.parse_expr()
            if self.match(TT.RPAREN): self.consume()
            return ASTNode("Grouped", children=[node])
        if tok.type == TT.LBRACKET:
            self.consume()
            node = ASTNode("ListLiteral")
            while not self.match(TT.RBRACKET) and not self.match(TT.EOF):
                node.children.append(self.parse_expr())
                if self.match(TT.COMMA): self.consume()
            if self.match(TT.RBRACKET): self.consume()
            return node
        self.consume()
        return ASTNode("Unknown", value=tok.value)


# ─────────────────────────────────────────────
# Python TAC Generator
# ─────────────────────────────────────────────
class PythonTACGen(TACGenerator):
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

        elif t == "Assignment":
            lhs = self.gen_expr(node.children[0])
            rhs = self.gen_expr(node.children[1])
            self.emit(f"{lhs} = {rhs}")

        elif t == "AugAssign":
            lhs = self.gen_expr(node.children[0])
            rhs = self.gen_expr(node.children[1])
            op  = node.value[0]  # + or -
            self.emit(f"{lhs} = {lhs} {op} {rhs}")

        elif t == "PrintStmt":
            args = [self.gen_expr(c) for c in node.children]
            self.emit(f"PRINT {', '.join(args)}")

        elif t == "IfStmt":
            cond = self.gen_expr(node.children[0].children[0])
            lelse = self.new_label()
            lend  = self.new_label()
            self.emit(f"IF NOT {cond} GOTO {lelse}")
            self.gen(node.children[1])
            self.emit(f"GOTO {lend}")
            self.emit(f"{lelse}:")
            for child in node.children[2:]:
                if child.type in ("ElifClause","ElseClause"):
                    self.gen(child)
            self.emit(f"{lend}:")

        elif t in ("ElifClause","ElseClause"):
            for c in node.children: self.gen(c)

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
            var = node.children[0].value
            iterable = self.gen_expr(node.children[1].children[0])
            tmp_i    = self.new_temp()
            tmp_len  = self.new_temp()
            lstart   = self.new_label()
            lend     = self.new_label()
            self.emit(f"{tmp_i} = 0")
            self.emit(f"{tmp_len} = LEN({iterable})")
            self.emit(f"{lstart}:")
            cond = self.new_temp()
            self.emit(f"{cond} = {tmp_i} < {tmp_len}")
            self.emit(f"IF NOT {cond} GOTO {lend}")
            self.emit(f"{var} = {iterable}[{tmp_i}]")
            self.gen(node.children[2])
            self.emit(f"{tmp_i} = {tmp_i} + 1")
            self.emit(f"GOTO {lstart}")
            self.emit(f"{lend}:")

        elif t == "ReturnStmt":
            if node.children:
                val = self.gen_expr(node.children[0])
                self.emit(f"RETURN {val}")
            else:
                self.emit("RETURN")

        elif t == "ExprStmt":
            for c in node.children: self.gen_expr(c)

        elif t in ("Params","Param","Condition","Iterable","LoopVar"):
            pass

    def gen_expr(self, node):
        t = node.type
        if t == "Literal":     return str(node.value)
        if t == "StrLiteral":  return f'"{node.value}"'
        if t == "BoolLiteral": return str(node.value)
        if t == "Identifier":  return str(node.value)
        if t == "Grouped":     return self.gen_expr(node.children[0])
        if t == "ListLiteral":
            items = [self.gen_expr(c) for c in node.children]
            return f"[{', '.join(items)}]"
        if t == "UnaryOp":
            v = self.gen_expr(node.children[0])
            tmp = self.new_temp()
            self.emit(f"{tmp} = {node.value} {v}")
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
# Python Parse Table
# ─────────────────────────────────────────────
def get_python_parse_table():
    return {
        "Program":    {"id":"Stmt Program", "def":"FuncDef Program", "if":"IfStmt Program", "while":"WhileStmt Program", "for":"ForStmt Program", "$":"ε"},
        "Stmt":       {"id":"id AssignTail NEWLINE", "print":"print ( ExprList ) NEWLINE", "return":"return Expr NEWLINE", "pass":"pass NEWLINE", "break":"break NEWLINE"},
        "AssignTail": {"=":"= Expr", "+=":"+= Expr", "-=":"-= Expr", "NEWLINE":"ε"},
        "FuncDef":    {"def":"def id ( Params ) : NEWLINE INDENT Block DEDENT"},
        "Params":     {"id":"id ParamTail", ")":"ε"},
        "ParamTail":  {",":","+" id ParamTail", ")":"ε"},
        "IfStmt":     {"if":"if Expr : NEWLINE INDENT Block DEDENT ElifChain ElseClause"},
        "ElifChain":  {"elif":"elif Expr : NEWLINE INDENT Block DEDENT ElifChain", "else":"ε", "id":"ε", "$":"ε"},
        "ElseClause": {"else":"else : NEWLINE INDENT Block DEDENT", "id":"ε", "$":"ε"},
        "WhileStmt":  {"while":"while Expr : NEWLINE INDENT Block DEDENT"},
        "ForStmt":    {"for":"for id in Expr : NEWLINE INDENT Block DEDENT"},
        "Block":      {"id":"Stmt Block", "if":"IfStmt Block", "while":"WhileStmt Block", "for":"ForStmt Block", "return":"ReturnStmt Block", "DEDENT":"ε"},
        "Expr":       {"id":"Identifier | FuncCall | Expr BinOp Expr", "num":"Literal", "str":"StrLiteral", "True":"BoolLit", "False":"BoolLit"},
        "ExprList":   {"id":"Expr ExprTail", "str":"Expr ExprTail", "num":"Expr ExprTail"},
        "ExprTail":   {",":","+" Expr ExprTail", ")":"ε"},
    }


# ─────────────────────────────────────────────
# Python output simulation (safe exec)
# ─────────────────────────────────────────────
def simulate_python(code):
    import io, contextlib
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            exec(compile(code, '<string>', 'exec'), {})
        result = output.getvalue()
        if not result.strip():
            result = "[Python simulation] Code ran with no output."
    except Exception as e:
        result = f"[Python Runtime Error] {e}"
    return result


# ─────────────────────────────────────────────
# Main Python Compiler class
# ─────────────────────────────────────────────
class PythonCompiler:
    def __init__(self, code):
        self.code = code

    def compile(self):
        print("\n" + "="*60)
        print("  PYTHON COMPILER — COMPILATION STARTED")
        print("="*60)

        print("\n[1/5] LEXICAL ANALYSIS (Scanner)")
        lexer  = PythonLexer(self.code)
        tokens = lexer.tokenize()
        print_tokens(tokens)

        print("\n[2/5] SYNTAX ANALYSIS (Parser)")
        parser = PythonParser(tokens)
        tree   = parser.parse()

        print("\n[3/5] PARSE TREE")
        print("\n" + "─"*45)
        print_tree(tree)
        print("─"*45)

        print("\n[4/5] THREE-ADDRESS CODE (TAC)")
        tac = PythonTACGen()
        tac.gen(tree)
        tac.print_tac()

        print("\n[5/5] PARSE TABLE (LL(1))")
        print_parse_table(get_python_parse_table(), title="Python Grammar Parse Table")

        print("\n[OUTPUT / RESULT]")
        print("─"*45)
        print(simulate_python(self.code))
        print("─"*45)
        print("\n✅ Python compilation complete.")
