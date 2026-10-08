#!/usr/bin/env python3
"""
Multi-Language Compiler
Supports: C, C++, Python
Outputs: Tokens, Parse Tree, TAC, Parse Table, Result
"""

import argparse
import io
import os
import sys
import tkinter as tk
import webbrowser
from contextlib import redirect_stdout
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# Add both project root AND src/ folder to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, 'src')
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SRC_DIR)

from c_compiler import CCompiler
from cpp_compiler import CppCompiler
from python_compiler import PythonCompiler

BANNER = """
+--------------------------------------------------------------+
|                 MULTI-LANGUAGE COMPILER v1.0                 |
|           Supports: C | C++ | Python                         |
|      Outputs: Tokens | Parse Tree | TAC | Parse Table        |
+--------------------------------------------------------------+
"""

EXAMPLES = {
    "C": '''#include <stdio.h>

int main() {
    int x = 10;
    int y = 5;
    printf("Sum: %d\\n", x + y);
    return 0;
}
''',
    "C++": '''#include <iostream>
using namespace std;

int main() {
    int a = 12;
    int b = 8;
    cout << "Product: " << a * b << endl;
    return 0;
}
''',
    "Python": '''def greet(name):
    return f"Hello, {name}!"

if __name__ == "__main__":
    for item in ["Alice", "Bob", "Charlie"]:
        print(greet(item))
''',
}


def choose_language():
    print(BANNER)
    print("Select Language:")
    print("  [1] C")
    print("  [2] C++")
    print("  [3] Python")
    print("  [0] Exit")
    while True:
        choice = input("\nEnter choice (0-3): ").strip()
        if choice == "1":
            return "C"
        if choice == "2":
            return "C++"
        if choice == "3":
            return "Python"
        if choice == "0":
            print("Goodbye!")
            sys.exit(0)
        print("Invalid choice. Try again.")


def get_code(language):
    print(f"\n{'=' * 60}")
    print(f"  {language} Compiler — Enter your code")
    print(f"  (Type 'END' on a new line when done)")
    print(f"{'=' * 60}")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def run_compiler(language, code):
    compilers = {
        "C": CCompiler,
        "C++": CppCompiler,
        "Python": PythonCompiler,
    }
    compiler_cls = compilers[language]
    compiler = compiler_cls(code)
    compiler.compile()


class CompilerStudioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Compiler Studio")
        self.root.geometry("1220x820")
        self.root.minsize(980, 680)
        self.root.configure(bg="#0b1120")

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Primary.TButton", background="#7c3aed", foreground="white", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("active", "#6d28d9")])
        style.configure("Sidebar.TFrame", background="#111827")
        style.configure("Panel.TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#111827")
        style.configure("Header.TLabel", background="#0b1120", foreground="#e2e8f0", font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", background="#0b1120", foreground="#94a3b8", font=("Segoe UI", 10))
        style.configure("Accent.TLabel", background="#0f172a", foreground="#a78bfa", font=("Segoe UI", 11, "bold"))
        style.configure("Dark.TNotebook", background="#0f172a")
        style.configure("Dark.TFrame", background="#0f172a")

        self.language_var = tk.StringVar(value="C")

        main_container = ttk.Frame(root, padding=18)
        main_container.pack(fill="both", expand=True)

        sidebar = ttk.Frame(main_container, style="Sidebar.TFrame", padding=18)
        sidebar.pack(side="left", fill="y")

        title = ttk.Label(sidebar, text="Compiler Studio", style="Header.TLabel")
        title.pack(anchor="w", pady=(0, 8))

        subtitle = ttk.Label(sidebar, text="Multi-language compiler toolkit", style="Subtitle.TLabel")
        subtitle.pack(anchor="w", pady=(0, 18))

        language_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        language_frame.pack(fill="x")

        ttk.Label(language_frame, text="Language", style="Accent.TLabel").pack(anchor="w", pady=(0, 8))

        for language in ("C", "C++", "Python"):
            radio = ttk.Radiobutton(
                language_frame,
                text=language,
                variable=self.language_var,
                value=language,
                command=self.on_language_change,
                style="Toolbutton",
            )
            radio.pack(anchor="w", pady=4)

        divider = ttk.Separator(sidebar, orient="horizontal")
        divider.pack(fill="x", pady=18)

        action_frame = ttk.Frame(sidebar, style="Sidebar.TFrame")
        action_frame.pack(fill="x")

        ttk.Button(action_frame, text="Compile", command=self.compile_current, style="Primary.TButton").pack(fill="x", pady=(0, 10))
        ttk.Button(action_frame, text="Load Example", command=self.load_example).pack(fill="x", pady=4)
        ttk.Button(action_frame, text="Clear", command=self.clear_editor).pack(fill="x", pady=4)

        content = ttk.Frame(main_container, style="Panel.TFrame")
        content.pack(side="left", fill="both", expand=True)

        toolbar = ttk.Frame(content, style="Panel.TFrame", padding=(16, 16, 16, 8))
        toolbar.pack(fill="x")

        ttk.Label(toolbar, text="Source Code", style="Accent.TLabel").pack(anchor="w")

        editor_container = ttk.Frame(content, style="Card.TFrame", padding=6)
        editor_container.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.editor = ScrolledText(
            editor_container,
            wrap=tk.WORD,
            font=("Consolas", 12),
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#f8fafc",
            selectbackground="#4f46e5",
            padx=12,
            pady=12,
            borderwidth=0,
            relief="flat",
            width=100,
            height=18,
        )
        self.editor.pack(fill="both", expand=True)
        self.editor.bind("<Control-Return>", lambda event: self.compile_current())

        output_panel = ttk.Frame(content, style="Card.TFrame", padding=6)
        output_panel.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.output = ScrolledText(
            output_panel,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#020817",
            fg="#cbd5e1",
            insertbackground="#f8fafc",
            padx=12,
            pady=12,
            borderwidth=0,
            relief="flat",
            height=14,
        )
        self.output.pack(fill="both", expand=True)
        self.output.configure(state="disabled")

        self.status = ttk.Label(content, text="Ready", foreground="#7dd3fc", background="#0f172a", font=("Segoe UI", 10, "bold"))
        self.status.pack(anchor="w", padx=16, pady=(0, 16))

        self.load_example()

    def on_language_change(self):
        self.load_example()

    def clear_editor(self):
        self.editor.delete("1.0", tk.END)
        self.output.configure(state="normal")
        self.output.delete("1.0", tk.END)
        self.output.configure(state="disabled")
        self.status.config(text="Editor cleared")

    def load_example(self):
        language = self.language_var.get()
        code = EXAMPLES.get(language, EXAMPLES["Python"])
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", code)
        self.status.config(text=f"Loaded {language} example")

    def compile_current(self):
        language = self.language_var.get()
        code = self.editor.get("1.0", tk.END).strip()
        if not code:
            messagebox.showwarning("Empty Input", "Please add some code before compiling.")
            return

        compilers = {
            "C": CCompiler,
            "C++": CppCompiler,
            "Python": PythonCompiler,
        }

        self.status.config(text=f"Compiling {language} source...")
        self.root.update_idletasks()

        try:
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                compiler = compilers[language](code)
                compiler.compile()
            output_text = buffer.getvalue().strip()
            if not output_text:
                output_text = "[Compiler Studio] No output was produced."

            self.output.configure(state="normal")
            self.output.delete("1.0", tk.END)
            self.output.insert("1.0", output_text)
            self.output.configure(state="disabled")
            self.status.config(text=f"{language} compilation completed successfully")
        except Exception as exc:  # pragma: no cover - GUI error reporting
            self.output.configure(state="normal")
            self.output.delete("1.0", tk.END)
            self.output.insert("1.0", f"[Compiler Studio Error] {exc}\n")
            self.output.configure(state="disabled")
            self.status.config(text="Compilation failed")
            messagebox.showerror("Compilation Error", str(exc))


def run_cli():
    while True:
        language = choose_language()
        code = get_code(language)
        if not code.strip():
            print("No code entered. Returning to menu.")
            continue
        run_compiler(language, code)
        print("\n" + "=" * 60)
        again = input("Compile another? (y/n): ").strip().lower()
        if again != "y":
            print("Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Compiler Studio")
    parser.add_argument("--cli", action="store_true", help="Run classic terminal interface")
    parser.add_argument("--gui", action="store_true", help="Run the desktop interface")
    parser.add_argument("--port", type=int, default=8000, help="Port for the browser interface (default: 8000)")
    args = parser.parse_args()

    if args.cli:
        run_cli()
        return

    if not args.gui:
        from web_server import run_web_server

        run_web_server(args.port)
        return

    try:
        root = tk.Tk()
        CompilerStudioApp(root)
        root.mainloop()
    except tk.TclError:
        print("Unable to open the GUI interface in this environment.")
        print("Use: python main.py --cli")
        sys.exit(1)


if __name__ == "__main__":
    main()
