const examples = {
  C: `#include <stdio.h>

int main() {
    int x = 10;
    int y = 5;
    printf("Sum: %d\\n", x + y);
    return 0;
}`,
  "C++": `#include <iostream>
using namespace std;

int main() {
    int a = 12;
    int b = 8;
    cout << "Product: " << a * b << endl;
    return 0;
}`,
  Python: `def greet(name):
    return "Hello, " + name

for item in ["Alice", "Bob", "Charlie"]:
    print(greet(item))`,
};

const editor = document.querySelector("#code-editor");
const lineNumbers = document.querySelector("#line-numbers");
const codeStats = document.querySelector("#code-stats");
const fileLabel = document.querySelector("#file-label");
const outputContent = document.querySelector("#output-content");
const outputStatus = document.querySelector("#output-status");
const outputMessage = document.querySelector("#output-message");
const outputLanguage = document.querySelector("#output-language");
const compileButton = document.querySelector("#compile-button");
const servedByLivePreview = ["3000", "5500"].includes(window.location.port);
const compilerApiOrigin = servedByLivePreview
  ? "http://127.0.0.1:8000"
  : window.location.origin;
let language = "C";
let latestOutput = "";

function updateEditorStats() {
  const lines = editor.value.split("\n").length;
  lineNumbers.textContent = Array.from({ length: lines }, (_, index) => index + 1).join("\n");
  lineNumbers.scrollTop = editor.scrollTop;
  codeStats.textContent = `${lines} ${lines === 1 ? "line" : "lines"} · ${editor.value.length} chars`;
}

function setLanguage(nextLanguage) {
  language = nextLanguage;
  document.querySelectorAll(".language-tab").forEach((tab) => {
    const selected = tab.dataset.language === language;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
  });
  fileLabel.textContent = language === "C++" ? "main.cpp" : language === "Python" ? "main.py" : "main.c";
  outputLanguage.textContent = language;
  editor.value = examples[language];
  updateEditorStats();
}

function setStatus(text, state = "") {
  outputStatus.textContent = text;
  outputStatus.className = `output-status ${state}`.trim();
}

function showServerConnectionError(detail) {
  latestOutput = [
    "This page is not connected to the Compiler Studio server.",
    "",
    "Close this page, open PowerShell in the project folder, and run:",
    "  py main.py",
    "",
    "Then open http://127.0.0.1:8000 in your browser.",
    "Do not open frontend/index.html with Live Server.",
    detail ? `\nDetails: ${detail}` : "",
  ].join("\n");
  outputContent.replaceChildren();
  const output = document.createElement("pre");
  output.className = "output-text";
  output.textContent = latestOutput;
  outputContent.append(output);
  setStatus("SERVER NOT FOUND", "error");
  outputMessage.textContent = "Start Compiler Studio with py main.py";
}

async function compile() {
  const code = editor.value.trim();
  if (!code) {
    editor.focus();
    outputMessage.textContent = "Add source code to compile";
    return;
  }

  compileButton.disabled = true;
  compileButton.querySelector("span:nth-child(2)").textContent = "Compiling…";
  setStatus("RUNNING", "running");
  outputMessage.textContent = `Compiling ${language} source…`;

  try {
    const response = await fetch(`${compilerApiOrigin}/api/compile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language, code }),
    });
    if (!response.headers.get("content-type")?.includes("application/json")) {
      showServerConnectionError(`The page origin returned HTTP ${response.status}, not the compiler API.`);
      return;
    }
    const result = await response.json();
    latestOutput = [result.output, result.error ? `\n[Compiler Error] ${result.error}` : ""].join("").trim();
    outputContent.replaceChildren();
    const output = document.createElement("pre");
    output.className = "output-text";
    output.textContent = latestOutput || "Compilation completed without output.";
    outputContent.append(output);

    if (!response.ok) {
      setStatus("ERROR", "error");
      outputMessage.textContent = "Compilation failed — review the diagnostic output";
    } else {
      setStatus("SUCCESS", "success");
      outputMessage.textContent = `${language} compilation completed`;
    }
  } catch (error) {
    showServerConnectionError(error.message);
  } finally {
    compileButton.disabled = false;
    compileButton.querySelector("span:nth-child(2)").textContent = "Compile";
  }
}

async function checkServerConnection() {
  try {
    const response = await fetch(`${compilerApiOrigin}/api/health`, { cache: "no-store" });
    if (!response.ok || !response.headers.get("content-type")?.includes("application/json")) {
      showServerConnectionError(`The page origin returned HTTP ${response.status}, not the compiler health endpoint.`);
      return;
    }
    const result = await response.json();
    if (result.status !== "ok") {
      showServerConnectionError("The local compiler health check did not succeed.");
    }
  } catch (error) {
    showServerConnectionError(error.message);
  }
}

document.querySelectorAll(".language-tab").forEach((tab) => {
  tab.addEventListener("click", () => setLanguage(tab.dataset.language));
});
document.querySelector("#load-example").addEventListener("click", () => setLanguage(language));
document.querySelector("#clear-code").addEventListener("click", () => {
  editor.value = "";
  latestOutput = "";
  updateEditorStats();
  editor.focus();
});
document.querySelector("#copy-output").addEventListener("click", async (event) => {
  if (!latestOutput) return;
  try {
    await navigator.clipboard.writeText(latestOutput);
    event.currentTarget.textContent = "Copied";
    window.setTimeout(() => { event.currentTarget.textContent = "Copy"; }, 1200);
  } catch {
    outputMessage.textContent = "Clipboard access is unavailable in this browser";
  }
});
document.querySelector("#empty-compile").addEventListener("click", compile);
compileButton.addEventListener("click", compile);
editor.addEventListener("input", updateEditorStats);
editor.addEventListener("scroll", () => { lineNumbers.scrollTop = editor.scrollTop; });
editor.addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    editor.setRangeText("    ", start, end, "end");
    updateEditorStats();
  }
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    compile();
  }
});

setLanguage(language);
checkServerConnection();
