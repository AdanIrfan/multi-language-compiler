"""
Shared Token Types and Base Lexer
Used by C, C++, and Python compilers
"""

import re

# ──────────────────────────────────────────────────────────
#  Token class
# ──────────────────────────────────────────────────────────
class Token:
    def __init__(self, type_, value, line=0):
        self.type  = type_
        self.value = value
        self.line  = line

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


# ──────────────────────────────────────────────────────────
#  Token type constants (shared across languages)
# ──────────────────────────────────────────────────────────
class TT:
    # Literals
    INT_LIT   = "INT_LIT"
    FLOAT_LIT = "FLOAT_LIT"
    STR_LIT   = "STR_LIT"
    CHAR_LIT  = "CHAR_LIT"
    BOOL_LIT  = "BOOL_LIT"

    # Identifier / keywords
    IDENT     = "IDENT"
    KEYWORD   = "KEYWORD"

    # Operators
    PLUS   = "PLUS"
    MINUS  = "MINUS"
    STAR   = "STAR"
    SLASH  = "SLASH"
    PERCENT= "PERCENT"
    EQ     = "EQ"
    NEQ    = "NEQ"
    LT     = "LT"
    GT     = "GT"
    LTE    = "LTE"
    GTE    = "GTE"
    ASSIGN = "ASSIGN"
    AND    = "AND"
    OR     = "OR"
    NOT    = "NOT"
    INC    = "INC"
    DEC    = "DEC"
    PLUS_EQ = "PLUS_EQ"
    MINUS_EQ= "MINUS_EQ"

    # Delimiters
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LBRACKET="LBRACKET"
    RBRACKET="RBRACKET"
    SEMI   = "SEMI"
    COLON  = "COLON"
    COMMA  = "COMMA"
    DOT    = "DOT"
    ARROW  = "ARROW"
    HASH   = "HASH"

    # Special
    NEWLINE= "NEWLINE"
    INDENT = "INDENT"
    DEDENT = "DEDENT"
    EOF    = "EOF"
    COMMENT= "COMMENT"


# ──────────────────────────────────────────────────────────
#  Utility: pretty print tokens table
# ──────────────────────────────────────────────────────────
def print_tokens(tokens):
    print("\n" + "-"*55)
    print(f"{'TOKEN TYPE':<18} {'VALUE':<25} {'LINE'}")
    print("-"*55)
    for t in tokens:
        if t.type in (TT.EOF, TT.NEWLINE, TT.INDENT, TT.DEDENT):
            continue
        print(f"{t.type:<18} {str(t.value):<25} {t.line}")
    print("-"*55)


# ──────────────────────────────────────────────────────────
#  AST Node base
# ──────────────────────────────────────────────────────────
class ASTNode:
    def __init__(self, type_, children=None, value=None):
        self.type     = type_
        self.children = children or []
        self.value    = value

    def __repr__(self):
        return f"ASTNode({self.type}, {self.value})"


# ──────────────────────────────────────────────────────────
#  Pretty-print parse tree
# ──────────────────────────────────────────────────────────
def print_tree(node, prefix="", is_last=True):
    if node is None:
        return
    connector = "`-- " if is_last else "|-- "
    label = node.type
    if node.value is not None:
        label += f" [{node.value}]"
    print(prefix + connector + label)
    child_prefix = prefix + ("    " if is_last else "|   ")
    valid_children = [c for c in node.children if c is not None]
    for i, child in enumerate(valid_children):
        print_tree(child, child_prefix, i == len(valid_children) - 1)


# ──────────────────────────────────────────────────────────
#  TAC (Three-Address Code) generator
# ──────────────────────────────────────────────────────────
class TACGenerator:
    def __init__(self):
        self.code    = []
        self._temp   = 0
        self._label  = 0

    def new_temp(self):
        self._temp += 1
        return f"t{self._temp}"

    def new_label(self):
        self._label += 1
        return f"L{self._label}"

    def emit(self, instruction):
        self.code.append(instruction)

    def print_tac(self):
        print("\n" + "-"*45)
        print("THREE-ADDRESS CODE (TAC)")
        print("-"*45)
        for i, line in enumerate(self.code, 1):
            print(f"  {i:>3}:  {line}")
        print("-"*45)


# ──────────────────────────────────────────────────────────
#  Parse Table printer (LL(1) style display)
# ──────────────────────────────────────────────────────────
def print_parse_table(table, title="PARSE TABLE"):
    """
    table: dict of { NonTerminal: { Terminal: Production } }
    """
    print("\n" + "-"*70)
    print(f"  {title}")
    print("-"*70)
    # Collect all terminals
    terminals = sorted({t for row in table.values() for t in row})
    col_w = 18
    nt_w  = 20
    # Header
    header = f"{'Non-Terminal':<{nt_w}}" + "".join(f"{t:<{col_w}}" for t in terminals)
    print(header)
    print("-"*70)
    for nt, row in table.items():
        line = f"{nt:<{nt_w}}"
        for t in terminals:
            prod = row.get(t, "")
            line += f"{str(prod):<{col_w}}"
        print(line)
    print("-"*70)
