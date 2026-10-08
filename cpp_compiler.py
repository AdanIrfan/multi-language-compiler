"""
C++ Compiler Module
Extends C compiler with: cout/cin, class, namespace, new/delete, templates (basic), STL hints
"""

import re
from shared import Token, TT, ASTNode, TACGenerator, print_tokens, print_tree, print_parse_table
from c_compiler import CLexer, CParser, CTACGen, simulate_c

# ─────────────────────────────────────────────
# Additional C++ keywords
# ─────────────────────────────────────────────
CPP_EXTRA_KEYWORDS = {
    'class','public','private','protected','new','delete','this',
    'namespace','using','template','typename','virtual','override',
    'cout','cin','endl','string','bool','true','false','nullptr',
    'try','catch','throw','const','auto','inline','friend','operator',
    'std','vector','map','set','pair'
}

# ─────────────────────────────────────────────
# C++ Lexer (inherits C Lexer, adds keywords)
# ─────────────────────────────────────────────
class CppLexer(CLexer):
    def tokenize(self):
        tokens = super().tokenize()
        for tok in tokens:
            if tok.type == TT.IDENT and tok.value in CPP_EXTRA_KEYWORDS:
                tok.type = TT.KEYWORD
        return tokens


# ─────────────────────────────────────────────
# C++ Parser (extends CParser with class/namespace)
# ─────────────────────────────────────────────
class CppParser(CParser):
    def parse_top_level(self):
        tok = self.current()
        if tok.type == TT.EOF:
            return None
        if tok.type == TT.KEYWORD and tok.value == 'namespace':
            return self.parse_namespace()
        if tok.type == TT.KEYWORD and tok.value == 'class':
            return self.parse_class()
        if tok.type == TT.KEYWORD and tok.value == 'using':
            return self.parse_using()
        if tok.type == TT.KEYWORD and tok.value == 'template':
            return self.parse_template()
        return super().parse_top_level()

    def parse_namespace(self):
        self.consume()   # 'namespace'
        name = self.consume()
        node = ASTNode("Namespace", value=name.value)
        if self.match(TT.LBRACE):
            node.children.append(self.parse_block())
        return node

    def parse_class(self):
        self.consume()   # 'class'
        name = self.consume()
        node = ASTNode("ClassDef", value=name.value)
        if self.match(TT.LBRACE):
            self.consume(TT.LBRACE)
            while not self.match(TT.RBRACE) and not self.match(TT.EOF):
                member = self.parse_class_member()
                if member: node.children.append(member)
            self.consume(TT.RBRACE)
            self.consume(TT.SEMI)
        return node

    def parse_class_member(self):
        tok = self.current()
        if tok.type == TT.KEYWORD and tok.value in ('public','private','protected'):
            self.consume()
            self.consume(TT.COLON)
            return ASTNode("AccessSpec", value=tok.value)
        return self.parse_top_level()

    def parse_using(self):
        self.consume()   # 'using'
        node = ASTNode("UsingDecl")
        while not self.match(TT.SEMI) and not self.match(TT.EOF):
            node.children.append(ASTNode("Token", value=self.consume().value))
        self.consume(TT.SEMI)
        return node

    def parse_template(self):
        self.consume()   # 'template'
        node = ASTNode("Template")
        # consume <typename T> etc.
        if self.match(TT.LT):
            self.consume()
            while not self.match(TT.GT) and not self.match(TT.EOF):
                node.children.append(ASTNode("TemplateParam", value=self.consume().value))
            self.consume()
        node.children.append(self.parse_top_level())
        return node

    def parse_statement(self):
        tok = self.current()
        # cout / cin statements
        if tok.type == TT.KEYWORD and tok.value in ('cout','cin'):
            return self.parse_stream_stmt()
        # new expression
        if tok.type == TT.KEYWORD and tok.value == 'new':
            return self.parse_new_stmt()
        return super().parse_statement()

    def parse_stream_stmt(self):
        stream = self.consume()   # cout or cin
        node = ASTNode("StreamOp", value=stream.value)
        # << is tokenized as LT LT (two separate < tokens)
        while not self.match(TT.SEMI) and not self.match(TT.EOF) and not self.match(TT.NEWLINE):
            # consume << (two LT) or >> (two GT)
            if self.current().type in (TT.LT, TT.GT) and self.peek().type == self.current().type:
                self.consume(); self.consume()  # skip << or >>
            else:
                break
            # now consume the operand
            if self.match(TT.SEMI) or self.match(TT.EOF):
                break
            node.children.append(self.parse_primary())
        if self.match(TT.SEMI): self.consume()
        return node

    def parse_new_stmt(self):
        self.consume()  # 'new'
        type_name = self.consume()
        node = ASTNode("NewExpr", value=type_name.value)
        if self.match(TT.LPAREN):
            self.consume()
            while not self.match(TT.RPAREN) and not self.match(TT.EOF):
                node.children.append(self.parse_expr())
                if self.match(TT.COMMA): self.consume()
            self.consume(TT.RPAREN)
        if self.match(TT.SEMI): self.consume()
        return node


# ─────────────────────────────────────────────
# C++ TAC Gen (extends C TAC with cout/cin/class)
# ─────────────────────────────────────────────
class CppTACGen(CTACGen):
    def gen(self, node):
        t = node.type
        if t == "StreamOp":
            if node.value == "cout":
                args = [self.gen_expr(c) for c in node.children]
                self.emit(f"PRINT {', '.join(args)}")
            elif node.value == "cin":
                args = [self.gen_expr(c) for c in node.children]
                self.emit(f"READ  {', '.join(args)}")
        elif t == "ClassDef":
            self.emit(f"CLASS_BEGIN {node.value}")
            for c in node.children: self.gen(c)
            self.emit(f"CLASS_END {node.value}")
        elif t == "Namespace":
            self.emit(f"NAMESPACE_BEGIN {node.value}")
            for c in node.children: self.gen(c)
            self.emit(f"NAMESPACE_END {node.value}")
        elif t == "NewExpr":
            tmp = self.new_temp()
            self.emit(f"{tmp} = ALLOC {node.value}")
        elif t in ("UsingDecl","Template","AccessSpec","TemplateParam","Token"):
            pass  # meta/declarative
        else:
            super().gen(node)


# ─────────────────────────────────────────────
# C++ Parse Table
# ─────────────────────────────────────────────
def get_cpp_parse_table():
    return {
        "Program":      {"int":"TopDecl", "void":"TopDecl", "float":"TopDecl", "class":"ClassDef", "namespace":"NamespaceDef", "using":"UsingDecl", "$":"ε"},
        "TopDecl":      {"int":"Type id FuncOrVar", "void":"Type id (Params) Block", "float":"Type id = Expr ;"},
        "FuncOrVar":    {"(":"( Params ) Block", "=":"= Expr ;", ";":";"},
        "ClassDef":     {"class":"class id { MemberList } ;"},
        "MemberList":   {"public":"AccessSpec : MemberList", "private":"AccessSpec : MemberList", "int":"TopDecl MemberList", "}":"ε"},
        "AccessSpec":   {"public":"public", "private":"private", "protected":"protected"},
        "NamespaceDef": {"namespace":"namespace id { Program }"},
        "UsingDecl":    {"using":"using namespace id ;"},
        "Stmt":         {"if":"IfStmt", "while":"WhileStmt", "for":"ForStmt", "return":"return Expr ;", "cout":"cout StreamTail ;", "cin":"cin StreamTail ;", "id":"id AssignOrCall", "{":"Block"},
        "StreamTail":   {"<<":"<< Expr StreamTail", ">>":">> Expr StreamTail", ";":"ε"},
        "IfStmt":       {"if":"if ( Expr ) Stmt ElseClause"},
        "ElseClause":   {"else":"else Stmt", ";":"ε", "}":"ε"},
        "WhileStmt":    {"while":"while ( Expr ) Stmt"},
        "ForStmt":      {"for":"for ( ForInit ; Expr ; Expr ) Stmt"},
        "Expr":         {"id":"id | Literal | ( Expr ) | Expr BinOp Expr"},
    }


# ─────────────────────────────────────────────
# C++ output simulation
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# C++ AST Interpreter (reuses C interpreter,
# adds cout/cin and class awareness)
# ─────────────────────────────────────────────
from c_compiler import ReturnException, BreakException, ContinueException, CASTInterpreter

class CppASTInterpreter(CASTInterpreter):
    """Extends the C interpreter with C++-specific nodes (cout, StreamOp)."""

    def _exec_stmt(self, node):
        if node is None:
            return
        t = node.type

        # cout << expr << expr << endl ;
        if t == "StreamOp" and node.value == "cout":
            parts = []
            for child in node.children:
                if child is None:
                    continue
                # endl appears as Identifier or Unknown with value 'endl'
                if child.value in ("endl", "std::endl"):
                    parts.append("\n")
                    continue
                val = self._eval(child)
                parts.append(str(val))
            line = "".join(parts)
            if not line.endswith("\n"):
                line += "\n"
            self.output.append(line)
            return

        # cin — skip (no stdin in simulation)
        if t == "StreamOp" and node.value == "cin":
            return

        # ClassDef / Namespace / UsingDecl — skip (just collect functions)
        if t in ("ClassDef", "Namespace", "UsingDecl", "Template",
                 "AccessSpec", "TemplateParam", "Token"):
            # still collect any FuncDef children
            for child in node.children:
                if child and child.type == "FuncDef":
                    self.functions[child.value] = child
            return

        # NewExpr — just return 0 (no heap in simulation)
        if t == "NewExpr":
            return

        # fall through to C interpreter
        super()._exec_stmt(node)

    def _eval(self, node):
        if node is None:
            return 0
        t = node.type

        # endl keyword evaluates to empty (we add \n in StreamOp handler)
        if t == "Identifier" and node.value in ("endl", "std::endl"):
            return ""

        # StrLiteral — return the actual string (no quotes)
        if t == "StrLiteral":
            return node.value

        return super()._eval(node)

    def _collect_functions(self, node):
        """Recursively collect FuncDef from all scopes including namespaces/classes."""
        if node is None:
            return
        for child in node.children:
            if child is None:
                continue
            if child.type == "FuncDef":
                self.functions[child.value] = child
            elif child.type in ("Namespace", "ClassDef", "Program", "Block"):
                self._collect_functions(child)


def simulate_cpp(tree):
    interp = CppASTInterpreter(tree)
    result = interp.run()
    if not result.strip():
        return "[C++ simulation] No output produced."
    return result


# ─────────────────────────────────────────────
# Main C++ Compiler class
# ─────────────────────────────────────────────
class CppCompiler:
    def __init__(self, code):
        self.code = code

    def compile(self):
        print("\n" + "="*60)
        print("  C++ COMPILER — COMPILATION STARTED")
        print("="*60)

        print("\n[1/5] LEXICAL ANALYSIS (Scanner)")
        lexer  = CppLexer(self.code)
        tokens = lexer.tokenize()
        print_tokens(tokens)

        print("\n[2/5] SYNTAX ANALYSIS (Parser)")
        parser = CppParser(tokens)
        tree   = parser.parse()

        print("\n[3/5] PARSE TREE")
        print("\n" + "─"*45)
        print_tree(tree)
        print("─"*45)

        print("\n[4/5] THREE-ADDRESS CODE (TAC)")
        tac = CppTACGen()
        tac.gen(tree)
        tac.print_tac()

        print("\n[5/5] PARSE TABLE (LL(1))")
        print_parse_table(get_cpp_parse_table(), title="C++ Grammar Parse Table")

        print("\n[OUTPUT / RESULT]")
        print("─"*45)
        print(simulate_cpp(tree))
        print("─"*45)
        print("\n✅ C++ compilation complete.")
