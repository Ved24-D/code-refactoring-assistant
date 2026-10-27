# CodeRefine — Code Refactoring Assistant

A Streamlit starter application for analyzing Python code and refactoring it with an OpenRouter chat-completions model.

## Features
- Python syntax validation using `ast.parse`
- Static metrics: lines, functions, classes, cyclomatic complexity, maintainability index
- AI refactoring through OpenRouter (optional)
- Conservative rule-based demo mode that requires no API key
- Before/after code view, unified diff, and `.py` download
- Does not execute user-submitted code

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder and run:

   ```bash
   python -m venv .venv
   # Windows:
   .venv\\Scripts\\activate
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   streamlit run app.py
   ```

3. Open the local URL printed by Streamlit.
4. Select **OpenRouter API** and enter your API key in the sidebar to use AI refactoring, or select **Rule-based demo** to try the app without a key.

## API key handling
- Do not commit API keys to GitHub.
- For local development, you may set the `OPENROUTER_API_KEY` environment variable.
- For Streamlit Community Cloud, add `OPENROUTER_API_KEY` under app Settings → Secrets, using TOML syntax:

  ```toml
  OPENROUTER_API_KEY = "your-key-here"
  ```

## Deploy to Streamlit Community Cloud
1. Push `app.py`, `requirements.txt`, and `README.md` to a GitHub repository.
2. Create a new app in Streamlit Community Cloud and select the repository and `app.py`.
3. Add `OPENROUTER_API_KEY` to the app's Secrets if you want AI refactoring.
4. Deploy and test the deployed URL.

## Important limitations
- Syntax validity does not prove behavior equivalence.
- Complexity/maintainability scores are static estimates, not runtime performance measurements.
- This version intentionally does not run arbitrary submitted code. Add execution tests or benchmarks only in a properly isolated sandbox with resource limits.
