from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .qa import Answer, answer_query
from .retriever import load_index


BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Mutual Fund FAQ Assistant (Groww RAG) - Phase 1")

index_cache = None


@app.on_event("startup")
def load_indices() -> None:
    global index_cache
    # Lazy build/load of index at startup.
    index_cache = load_index()


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """
    Tiny UI: welcome line, 3 example questions, and a note.
    """
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Mutual Fund FAQ Assistant</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      padding: 0;
      background: #0b1120;
      color: #e5e7eb;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }}
    .container {{
      max-width: 720px;
      width: 100%;
      background: #020617;
      border-radius: 16px;
      padding: 24px 28px 32px 28px;
      box-shadow: 0 25px 50px -12px rgba(15,23,42,0.8);
      border: 1px solid rgba(148,163,184,0.25);
    }}
    h1 {{
      font-size: 1.6rem;
      margin-bottom: 0.25rem;
    }}
    .subtitle {{
      font-size: 0.9rem;
      color: #9ca3af;
      margin-bottom: 1.2rem;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.75rem;
      padding: 3px 10px;
      border-radius: 999px;
      background: rgba(22,163,74,0.08);
      color: #4ade80;
      border: 1px solid rgba(74,222,128,0.25);
      margin-bottom: 0.9rem;
    }}
    .examples {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }}
    .example-pill {{
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.4);
      font-size: 0.8rem;
      color: #e5e7eb;
      cursor: pointer;
      background: rgba(15,23,42,0.9);
    }}
    .example-pill:hover {{
      background: rgba(30,64,175,0.8);
    }}
    .note {{
      font-size: 0.78rem;
      color: #9ca3af;
      margin-bottom: 0.8rem;
    }}
    .input-row {{
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.75rem;
    }}
    input[type="text"] {{
      flex: 1;
      padding: 0.6rem 0.75rem;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.5);
      background: #020617;
      color: #e5e7eb;
      font-size: 0.9rem;
      outline: none;
    }}
    input[type="text"]:focus {{
      border-color: #4f46e5;
      box-shadow: 0 0 0 1px rgba(79,70,229,0.5);
    }}
    button {{
      padding: 0.6rem 1.1rem;
      border-radius: 999px;
      border: none;
      background: linear-gradient(to right, #4f46e5, #22c55e);
      color: white;
      font-weight: 500;
      cursor: pointer;
      font-size: 0.9rem;
    }}
    button:disabled {{
      opacity: 0.5;
      cursor: default;
    }}
    .answer-card {{
      border-radius: 12px;
      border: 1px solid rgba(148,163,184,0.4);
      padding: 0.75rem 0.85rem;
      font-size: 0.88rem;
      background: rgba(15,23,42,0.9);
      min-height: 3rem;
    }}
    .source {{
      margin-top: 0.45rem;
      font-size: 0.78rem;
      color: #9ca3af;
    }}
    .source a {{
      color: #60a5fa;
      text-decoration: none;
    }}
    .source a:hover {{
      text-decoration: underline;
    }}
    .footnote {{
      margin-top: 0.4rem;
      font-size: 0.75rem;
      color: #6b7280;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="badge">Phase 1 • Facts-only • Groww public data</div>
    <h1>Mutual Fund FAQ assistant</h1>
    <div class="subtitle">
      Answers factual questions about mutual funds using public information from Groww, with one clear source link in every response.
    </div>

    <div class="note"><strong>Note:</strong> Facts-only. No investment advice. No PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.</div>

    <div class="examples">
      <div class="example-pill" onclick="fillExample('What is the ELSS lock-in period for tax-saving mutual funds?')">
        ELSS lock-in period?
      </div>
      <div class="example-pill" onclick="fillExample('How can I download my capital-gains statement on Groww?')">
        Download capital-gains statement?
      </div>
      <div class="example-pill" onclick="fillExample('What is an expense ratio in a mutual fund?')">
        What is expense ratio?
      </div>
    </div>

    <div class="input-row">
      <input id="query" type="text" placeholder="Ask a factual mutual fund question..." />
      <button id="askBtn" onclick="submitQuery()">Ask</button>
    </div>

    <div class="answer-card" id="answerBox">
      Ask a question to see a factual response here.
    </div>
    <div class="source" id="sourceBox"></div>
    <div class="footnote" id="lastUpdatedBox"></div>
  </div>

  <script>
    const queryInput = document.getElementById('query');
    const answerBox = document.getElementById('answerBox');
    const sourceBox = document.getElementById('sourceBox');
    const lastUpdatedBox = document.getElementById('lastUpdatedBox');
    const askBtn = document.getElementById('askBtn');

    function fillExample(text) {{
      queryInput.value = text;
      queryInput.focus();
    }}

    async function submitQuery() {{
      const q = queryInput.value.trim();
      if (!q) return;

      askBtn.disabled = true;
      answerBox.textContent = 'Thinking...';
      sourceBox.textContent = '';
      lastUpdatedBox.textContent = '';

      try {{
        const res = await fetch('/ask', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ query: q }})
        }});
        if (!res.ok) {{
          throw new Error('Request failed');
        }}
        const data = await res.json();
        answerBox.textContent = data.text;
        if (data.source_url) {{
          sourceBox.innerHTML = 'Source: <a href=\"' + data.source_url + '\" target=\"_blank\" rel=\"noopener noreferrer\">' + data.source_url + '</a>';
        }} else {{
          sourceBox.textContent = '';
        }}
        if (data.last_updated) {{
          lastUpdatedBox.textContent = 'Last updated from sources: ' + data.last_updated;
        }} else {{
          lastUpdatedBox.textContent = 'Last updated from sources: not available';
        }}
      }} catch (e) {{
        answerBox.textContent = 'Something went wrong while answering. Please try again.';
        sourceBox.textContent = '';
        lastUpdatedBox.textContent = '';
      }} finally {{
        askBtn.disabled = false;
      }}
    }}

    queryInput.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter') {{
        submitQuery();
      }}
    }});
  </script>
</body>
</html>
    """


@app.post("/ask")
async def ask(payload: Dict[str, Any], request: Request) -> JSONResponse:
    query = (payload.get("query") or "").strip()
    if not query:
        return JSONResponse(
            status_code=400,
            content={"error": "Query is required."},
        )

    global index_cache
    if index_cache is None:
        index_cache = load_index()

    ans: Answer = answer_query(query, index=index_cache)
    # Ensure ≤3 sentences for transparency and brevity.
    text = ans.text
    # Basic enforcement: split and truncate.
    sentences = [s.strip() for s in re_split_sentences(text) if s.strip()]
    if len(sentences) > 3:
        sentences = sentences[:3]
        text = " ".join(sentences)

    return JSONResponse(
        {
            "text": text,
            "source_url": ans.source_url,
            "last_updated": ans.last_updated,
            "intent": ans.intent.value,
            "refused": ans.refused,
        }
    )


def re_split_sentences(text: str) -> list[str]:
    buf = text.replace("?", ".").replace("!", ".")
    return buf.split(".")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

