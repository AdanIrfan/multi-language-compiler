# Multi-Language Compiler - Presentation Slides

## Slide 1: Project Title
- Multi-Language Compiler
- A simple compiler tool for C, C++, and Python
- Shows how code is read, parsed, and translated step by step

## Slide 2: What the Project Does
- Lets the user choose a language
- Reads code input from the user
- Converts the code into:
  - Tokens
  - Parse tree
  - Three-address code
  - Parse table
- Also shows a final result or simulation output

## Slide 3: Supported Languages
- C
- C++
- Python

## Slide 4: Main Components
- main.py
  - User interface and menu
  - Selects language and reads code
- shared.py
  - Token definitions
  - AST node and tree printing
  - TAC generator
  - Parse table printer
- c_compiler.py
  - C lexer and parser
  - C-specific grammar and output
- cpp_compiler.py
  - Extends C support
  - Adds C++ class, namespace, cout/cin
- python_compiler.py
  - Python lexer with indent support
  - Python parser and TAC generation
  - Executes the code for result output

## Slide 5: How It Works
- Step 1: Lexical analysis
  - Breaks code into tokens
- Step 2: Syntax analysis
  - Builds a parse tree
- Step 3: Parse tree display
- Step 4: Generate TAC
  - Simple intermediate code
- Step 5: Print parse table
  - Shows grammar decisions
- Step 6: Show result
  - Simulated output or runtime result

## Slide 6: Why This Project Is Useful
- Helps understand compiler stages
- Works with multiple languages
- Visualizes internal parser structures
- Good for learning language processing

## Slide 7: Demo Example
- Choose a language
- Enter code (end with END)
- See:
  - token list
  - tree view
  - TAC lines
  - grammar table
  - program result

## Slide 8: Key Takeaway
- This project is a simple compiler educational tool
- It shows how source code becomes structured data
- It supports multiple languages with one framework
