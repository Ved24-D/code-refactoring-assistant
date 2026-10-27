import ast
import difflib
import os
from typing import Any

import streamlit as st

try:
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit
    from radon.raw import analyze
except ImportError:
    cc_visit = mi_visit = analyze = None

st.set_page_config(page_title="CodeRefine | Python Refactoring Assistant", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 2rem; max-width: 1400px;}
.hero {padding: 1.5rem 1.7rem; border: 1px solid rgba(128,128,128,.25); border-radius: 18px; margin-bottom: 1rem;}
.hero h1 {margin: 0; font-size: 2.35rem;}
.hero p {margin: .45rem 0 0 0; opacity: .78;}
.small-note {opacity:.75; font-size:.88rem;}
</style>
<div class="hero">
  <h1>🛠️ CodeRefine</h1>
  <p>Analyze, refactor, and compare Python code for readability and maintainability.</p>
</div>
""", unsafe_allow_html=True)

DEFAULT_CODE = '''def calculate_total(prices):
    total = 0
    for i in range(len(prices)):
        total = total + prices[i]
    return total

prices = [10, 20, 30, 40]
print(calculate_total(prices))
'''


def get_saved_openrouter_api_key() -> str:
    try:
        secret_value = st.secrets.get("OPENROUTER_API_KEY", "")
    except Exception:
        return ""
    if secret_value is None:
        return ""
    if isinstance(secret_value, str):
        return secret_value.strip()
    return str(secret_value).strip()


with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("Refactoring engine", ["OpenRouter API", "Rule-based demo (no API key)"])
    model = st.text_input("OpenRouter model", value="openai/gpt-4o-mini", help="Choose a model available to your OpenRouter account.")
    saved_api_key = get_saved_openrouter_api_key()
    api_key_input = st.text_input("OpenRouter API key", type="password", value=saved_api_key, help="Used only for this session. Do not paste keys into source code.")
    st.caption("You can analyze code without an API key. AI refactoring requires an OpenRouter key and an available model.")

left, right = st.columns(2, gap="large")
with left:
    st.subheader("Original Python code")
    source_code = st.text_area("Enter or paste code", value=DEFAULT_CODE, height=340, label_visibility="collapsed", key="source")
    analyze_clicked = st.button("Analyze code", use_container_width=True)
with right:
    st.subheader("Refactoring result")
    st.caption("The refactored version will appear here after you run refactoring.")
    if "refactored_code" not in st.session_state:
        st.session_state.refactored_code = ""
    if st.session_state.refactored_code:
        st.code(st.session_state.refactored_code, language="python")
    else:
        st.info("Your improved code will appear here.")


def code_metrics(code: str) -> dict[str, Any]:
    tree = ast.parse(code)
    lines = code.splitlines()
    nonblank = sum(bool(line.strip()) for line in lines)
    functions = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in ast.walk(tree))
    classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    complexity = None
    maintainability = None
    raw = None
    if cc_visit:
        blocks = cc_visit(code)
        complexity = round(sum(b.complexity for b in blocks) / len(blocks), 2) if blocks else 1.0
    if mi_visit:
        maintainability = round(mi_visit(code, multi=True), 2)
    if analyze:
        report = analyze(code)
        raw = {"Comments": report.comments, "Blank lines": report.blank, "Logical lines": report.lloc}
    return {"Lines": len(lines), "Nonblank lines": nonblank, "Functions": functions, "Classes": classes,
            "Average block complexity": complexity, "Maintainability index": maintainability, "Raw": raw}


def rule_based_refactor(code: str) -> str:
    # Deliberately conservative demo: this does not claim semantic optimization.
    replacements = {
        "total = total + prices[i]": "total += prices[i]",
        "for i in range(len(prices)):\n        total += prices[i]": "for price in prices:\n        total += price",
    }
    result = code
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def openrouter_refactor(code: str, key: str, model_name: str) -> str:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Missing dependency 'requests'. Install requirements.txt.") from exc
    prompt = """Refactor the following Python code for readability and maintainability, and improve performance only where justified. Preserve behavior and public interfaces. Do not add explanations, Markdown fences, or unrelated features. Return only complete Python source code. If a change could alter behavior, keep the original behavior.\n\nCODE:\n""" + code
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "http://localhost:8501", "X-Title": "CodeRefine"},
        json={"model": model_name, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenRouter request failed ({response.status_code}): {response.text[:500]}")
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1]
        if content.rstrip().endswith("```"):
            content = content.rstrip()[:-3].rstrip()
        if content.lower().startswith("python\n"):
            content = content[7:]
    return content.strip()

if analyze_clicked:
    if not source_code.strip():
        st.warning("Enter some Python code first.")
    else:
        try:
            ast.parse(source_code)
            metrics = code_metrics(source_code)
            st.session_state.original_metrics = metrics
            st.session_state.original_code = source_code
            st.success("Original code passed Python syntax validation.")
        except SyntaxError as e:
            st.error(f"Syntax error on line {e.lineno}: {e.msg}")
        except Exception as e:
            st.error(f"Analysis failed: {e}")

st.divider()
st.subheader("Refactor code")
refactor_col, validate_col = st.columns([1, 1])
with refactor_col:
    if st.button("✨ Refactor Python code", type="primary", use_container_width=True):
        if not source_code.strip():
            st.warning("Enter some code first.")
        else:
            try:
                ast.parse(source_code)
                with st.spinner("Refactoring code…"):
                    if provider == "OpenRouter API":
                        key = api_key_input.strip() or get_saved_openrouter_api_key() or os.getenv("OPENROUTER_API_KEY", "").strip()
                        if not key:
                            raise RuntimeError("Add your OpenRouter API key in the sidebar or set OPENROUTER_API_KEY as an environment variable.")
                        result = openrouter_refactor(source_code, key, model.strip())
                    else:
                        result = rule_based_refactor(source_code)
                ast.parse(result)
                st.session_state.refactored_code = result
                st.session_state.original_code = source_code
                st.session_state.original_metrics = code_metrics(source_code)
                st.session_state.refactored_metrics = code_metrics(result)
                st.success("Refactoring completed. The output passed syntax validation.")
                st.rerun()
            except SyntaxError as e:
                st.error(f"Refactor output is not valid Python (line {e.lineno}): {e.msg}")
            except Exception as e:
                st.error(str(e))
with validate_col:
    if st.button("Validate current result", use_container_width=True):
        result = st.session_state.get("refactored_code", "")
        if not result:
            st.warning("Refactor the code first.")
        else:
            try:
                ast.parse(result)
                st.success("Refactored code is syntactically valid Python.")
            except SyntaxError as e:
                st.error(f"Syntax error on line {e.lineno}: {e.msg}")

if st.session_state.get("refactored_code"):
    original = st.session_state.get("original_code", source_code)
    improved = st.session_state.refactored_code
    st.divider()
    st.subheader("Before and after")
    tab1, tab2, tab3 = st.tabs(["Refactored code", "Diff", "Metrics"])
    with tab1:
        st.code(improved, language="python")
        st.download_button("Download refactored .py", data=improved, file_name="refactored_code.py", mime="text/x-python")
    with tab2:
        diff = difflib.unified_diff(original.splitlines(), improved.splitlines(), fromfile="original.py", tofile="refactored.py", lineterm="")
        st.code("\n".join(diff) or "No changes detected.", language="diff")
    with tab3:
        try:
            old = code_metrics(original)
            new = code_metrics(improved)
            cols = st.columns(4)
            cols[0].metric("Original lines", old["Lines"])
            cols[1].metric("Refactored lines", new["Lines"], delta=new["Lines"] - old["Lines"])
            cols[2].metric("Original functions", old["Functions"])
            cols[3].metric("Refactored functions", new["Functions"], delta=new["Functions"] - old["Functions"])
            if old["Average block complexity"] is not None:
                cols = st.columns(2)
                cols[0].metric("Original avg. complexity", old["Average block complexity"])
                cols[1].metric("Refactored avg. complexity", new["Average block complexity"], delta=round(new["Average block complexity"] - old["Average block complexity"], 2))
            if old["Maintainability index"] is not None:
                cols = st.columns(2)
                cols[0].metric("Original maintainability index", old["Maintainability index"])
                cols[1].metric("Refactored maintainability index", new["Maintainability index"], delta=round(new["Maintainability index"] - old["Maintainability index"], 2))
            st.caption("Metrics are static indicators, not proof that the code is faster or behaviorally equivalent. No submitted code is executed by this app.")
        except Exception as e:
            st.error(f"Could not calculate metrics: {e}")

st.divider()
st.markdown("<p class='small-note'>Safety note: this starter app parses and analyzes submitted code but does not execute it. Performance benchmarking and behavior-equivalence tests should only be added with an isolated execution environment.</p>", unsafe_allow_html=True)
# --------------------------------------------------
# Behavioral Equivalence Testing
# --------------------------------------------------

def run_equivalence_tests(original_func, refactored_func, test_cases):
    """
    Compare two trusted functions against the same test cases.

    NOTE:
    Only pass trusted Python functions to this utility.
    Do not use it to execute arbitrary user-submitted code.
    """
    results = []

    for test_input in test_cases:
        try:
            original_output = original_func(test_input)
            refactored_output = refactored_func(test_input)

            passed = original_output == refactored_output

            results.append({
                "Input": repr(test_input),
                "Original Output": repr(original_output),
                "Refactored Output": repr(refactored_output),
                "Status": "PASS" if passed else "FAIL",
            })

        except Exception as exc:
            results.append({
                "Input": repr(test_input),
                "Original Output": "Error",
                "Refactored Output": str(exc),
                "Status": "ERROR",
            })

    return results


def original_sum_function(prices):
    total = 0
    for i in range(len(prices)):
        total = total + prices[i]
    return total


def refactored_sum_function(prices):
    return sum(prices)


st.divider()
st.subheader("🧪 Behavioral Equivalence Testing")

st.write(
    "Compare the original and refactored summation implementations "
    "against a set of predefined test inputs."
)

if st.button("Run Equivalence Tests", use_container_width=True):
    test_cases = [
        [10, 20, 30, 40],
        [],
        [5],
        [-5, 10, -2],
        [1, 2, 3, 4, 5],
    ]

    results = run_equivalence_tests(
        original_sum_function,
        refactored_sum_function,
        test_cases,
    )

    import pandas as pd

    st.dataframe(results, use_container_width=True)

    passed_count = sum(
        result["Status"] == "PASS"
        for result in results
    )

    st.metric(
        "Tests Passed",
        f"{passed_count}/{len(results)}",
    )

    if passed_count == len(results):
        st.success(
            "All predefined test cases passed."
        )
    else:
        st.warning(
            "Some test cases failed. Review the results."
        )