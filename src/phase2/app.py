from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .qa import Answer, answer_query_phase2
from ..phase1.retriever import load_index


BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Mutual Fund FAQ Assistant (Groq RAG-only) - Phase 2")

index_cache = None


@app.on_event("startup")
def load_indices() -> None:
    global index_cache
    index_cache = load_index()


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """
    Chat-style UI inspired by the reference widget image.
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
      padding: 24px;
      background: #f3f4f6;
      color: #111827;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }}
    .container {{
      width: 520px;
      max-width: 100%;
      background: #ffffff;
      border-radius: 24px;
      padding: 12px 0 0 0;
      box-shadow:
        0 15px 30px rgba(15,23,42,0.12),
        0 2px 6px rgba(15,23,42,0.08);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .header {{
      padding: 10px 16px 8px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid #e5e7eb;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .avatar-circle {{
      width: 32px;
      height: 32px;
      border-radius: 999px;
      background: linear-gradient(135deg, #2563eb, #22c55e);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ffffff;
      font-weight: 600;
      font-size: 0.9rem;
    }}
    .header-text-main {{
      font-size: 0.9rem;
      font-weight: 600;
      color: #111827;
    }}
    .header-text-sub {{
      font-size: 0.75rem;
      color: #16a34a;
    }}
    .header-right-dot {{
      width: 4px;
      height: 4px;
      border-radius: 999px;
      background: #9ca3af;
    }}
    .subtitle {{
      font-size: 0.82rem;
      color: #6b7280;
      padding: 0 16px 6px 16px;
    }}
    .note {{
      font-size: 0.76rem;
      color: #6b7280;
      padding: 0 16px 6px 16px;
    }}
    .chips-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 4px 16px 8px 16px;
    }}
    .chip {{
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid #e5e7eb;
      font-size: 0.78rem;
      color: #374151;
      background: #f9fafb;
      cursor: pointer;
    }}
    .chip:hover {{
      background: #eff6ff;
      border-color: #bfdbfe;
    }}
    .chat-body {{
      flex: 1;
      padding: 4px 16px 16px 16px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      overflow-y: auto;
      background: #f9fafb;
      min-height: 420px;
    }}
    .msg-row {{
      display: flex;
      margin-top: 4px;
    }}
    .msg-row.user {{
      justify-content: flex-end;
    }}
    .msg-row.bot {{
      justify-content: flex-start;
    }}
    .bubble {{
      max-width: 78%;
      border-radius: 18px;
      padding: 7px 10px;
      font-size: 0.9rem;
      line-height: 1.3;
    }}
    .bubble.user {{
      background: #2563eb;
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }}
    .bubble.bot {{
      background: #ffffff;
      border: 1px solid #e5e7eb;
      color: #111827;
      border-bottom-left-radius: 4px;
    }}
    .source-line {{
      font-size: 0.7rem;
      color: #6b7280;
      margin-top: 3px;
    }}
    .source-line a {{
      color: #2563eb;
      text-decoration: none;
    }}
    .source-line a:hover {{
      text-decoration: underline;
    }}
    .footer {{
      padding: 12px 16px 14px 16px;
      border-top: 1px solid #e5e7eb;
      background: #ffffff;
    }}
    .input-wrapper {{
      position: relative;
      width: 100%;
    }}
    .input-wrapper input[type="text"] {{
      width: 100%;
      border-radius: 999px;
      border: 1px solid #d1d5db;
      padding: 10px 34px 10px 14px; /* extra right padding for smaller embedded button */
      font-size: 0.9rem;
      outline: none;
      box-sizing: border-box;
    }}
    .input-wrapper input[type="text"]:focus {{
      border-color: #2563eb;
      box-shadow: 0 0 0 1px rgba(37,99,235,0.2);
    }}
    .send-btn {{
      width: 32px;
      height: 32px;
      border-radius: 999px;
      border: none;
      background: linear-gradient(135deg, #2563eb, #22c55e);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      color: #ffffff;
      position: absolute;
      top: 50%;
      right: 5px;
      transform: translateY(-50%);
      padding: 0;
    }}
    .send-btn:disabled {{
      opacity: 0.5;
      cursor: default;
    }}
    .send-icon {{
      border-style: solid;
      border-width: 0 0 0 0;
      width: 0;
      height: 0;
      border-left: 9px solid #ffffff;
      border-top: 6px solid transparent;
      border-bottom: 6px solid transparent;
      transform: translateX(1px);
    }}

    @media (max-width: 520px) {{
      body {{
        padding: 12px;
      }}
      .container {{
        width: 100%;
      }}
      .chat-body {{
        min-height: 320px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="header-left">
        <div class="avatar-circle">MF</div>
        <div>
          <div class="header-text-main">Mutual Fund FAQ assistant</div>
          <div class="header-text-sub">We’re online • Facts-only</div>
        </div>
      </div>
      <div class="header-right-dot"></div>
    </div>

    <div class="subtitle">
      Answers factual questions using only public information from Groww stored in embeddings, with one clear source link in every answer.
    </div>
    <div class="note">
      Note: Facts-only. No investment advice. No PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.
    </div>

    <div class="chips-row">
      <div class="chip" onclick="fillExample('What is the ELSS lock-in period for tax-saving mutual funds?')">ELSS lock-in period?</div>
      <div class="chip" onclick="fillExample('How can I download my capital-gains statement on Groww?')">Download capital-gains statement?</div>
      <div class="chip" onclick="fillExample('What is an expense ratio in a mutual fund?')">What is expense ratio?</div>
    </div>

    <div class="chat-body" id="chatBody">
      <!-- Messages injected by JavaScript -->
      <div class="msg-row bot">
        <div class="bubble bot">
          Hi, I’m your mutual fund FAQ assistant. Ask a factual question about mutual funds on Groww and I’ll answer with a source link.
        </div>
      </div>
    </div>

    <div class="footer">
      <div class="input-wrapper">
        <input id="query" type="text" placeholder="Type a factual mutual fund question..." />
        <button id="askBtn" class="send-btn" onclick="submitQuery()">
          <div class="send-icon"></div>
        </button>
      </div>
    </div>
  </div>

  <script>
    const queryInput = document.getElementById('query');
    const chatBody = document.getElementById('chatBody');
    const askBtn = document.getElementById('askBtn');

    function fillExample(text) {{
      queryInput.value = text;
      queryInput.focus();
    }}

    async function submitQuery() {{
      const q = queryInput.value.trim();
      if (!q) return;

      askBtn.disabled = true;

      appendMessage('user', q);
      queryInput.value = '';
      scrollToBottom();

      const thinkingId = appendMessage('bot', 'Thinking...');

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
        replaceMessageText(thinkingId, data.text || 'I was not able to produce an answer.');
        if (data.source_url || data.last_updated) {{
          appendSourceLine(thinkingId, data.source_url, data.last_updated);
        }}
        scrollToBottom();
      }} catch (e) {{
        replaceMessageText(thinkingId, 'Something went wrong while answering. Please try again.');
      }} finally {{
        askBtn.disabled = false;
      }}
    }}

    function appendMessage(role, text) {{
      const row = document.createElement('div');
      row.className = 'msg-row ' + (role === 'user' ? 'user' : 'bot');

      const bubble = document.createElement('div');
      bubble.className = 'bubble ' + (role === 'user' ? 'user' : 'bot');
      bubble.textContent = text;

      row.appendChild(bubble);
      chatBody.appendChild(row);
      const id = Date.now().toString() + Math.random().toString(16).slice(2);
      row.dataset.msgId = id;
      return id;
    }}

    function replaceMessageText(id, newText) {{
      const row = findMsgRow(id);
      if (!row) return;
      const bubble = row.querySelector('.bubble');
      if (bubble) bubble.textContent = newText;
    }}

    function appendSourceLine(id, url, lastUpdated) {{
      const row = findMsgRow(id);
      if (!row) return;
      const bubble = row.querySelector('.bubble');
      if (!bubble) return;
      const src = document.createElement('div');
      src.className = 'source-line';
      let text = '';
      if (url) {{
        text += 'Source: ';
        const a = document.createElement('a');
        a.href = url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.textContent = url;
        src.appendChild(document.createTextNode('Source: '));
        src.appendChild(a);
      }}
      if (lastUpdated) {{
        const span = document.createElement('span');
        span.textContent = (url ? ' • ' : '') + 'Last updated from sources: ' + lastUpdated;
        src.appendChild(span);
      }}
      bubble.appendChild(src);
    }}

    function findMsgRow(id) {{
      const rows = chatBody.querySelectorAll('.msg-row');
      for (const r of rows) {{
        if (r.dataset.msgId === id) return r;
      }}
      return null;
    }}

    function scrollToBottom() {{
      chatBody.scrollTop = chatBody.scrollHeight;
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

    ans: Answer = answer_query_phase2(query, index=index_cache)
    # Enforce ≤3 sentences (additional safety).
    text = ans.text or ""
    buf = text.replace("?", ".").replace("!", ".")
    sentences = [s.strip() for s in buf.split(".") if s.strip()]
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


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

