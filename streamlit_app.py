import streamlit as st

from src.phase1.retriever import load_index
from src.phase2.qa import answer_query_phase2

@st.cache_resource
def get_index():
    return load_index()

st.set_page_config(
    page_title="Mutual Fund FAQ assistant",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Match FastAPI chat UI: card, header, chips, bubbles, footer
st.markdown("""
<style>
  /* Center card like FastAPI */
  .stApp {
    max-width: 560px;
    margin: 0 auto;
    padding: 24px 16px 24px 16px;
    background: #f3f4f6;
  }
  [data-testid="stAppViewContainer"] {
    background: #f3f4f6;
  }
  /* Card container */
  section[data-testid="stSidebar"] { display: none; }
  div.block-container {
    max-width: 560px;
    padding: 12px 0 0 0;
    background: #ffffff;
    border-radius: 24px;
    box-shadow: 0 15px 30px rgba(15,23,42,0.12), 0 2px 6px rgba(15,23,42,0.08);
    overflow: visible;
  }
  /* Header row */
  .mf-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 16px 8px 16px;
    border-bottom: 1px solid #e5e7eb;
  }
  .mf-header-left { display: flex; align-items: center; gap: 10px; }
  .mf-avatar {
    width: 32px; height: 32px; border-radius: 999px;
    background: linear-gradient(135deg, #2563eb, #22c55e);
    color: #fff; font-weight: 600; font-size: 0.9rem;
    display: flex; align-items: center; justify-content: center;
  }
  .mf-title { font-size: 0.9rem; font-weight: 600; color: #111827; margin: 0; }
  .mf-status { font-size: 0.75rem; color: #16a34a; margin: 0; }
  .mf-subtitle {
    font-size: 0.82rem; color: #6b7280; padding: 0 16px 6px 16px; margin: 0;
    line-height: 1.4;
  }
  .mf-note {
    font-size: 0.76rem; color: #6b7280; padding: 0 16px 12px 16px; margin: 0;
    line-height: 1.4;
  }
  /* Chip buttons (suggested questions) - style all main-container buttons except chat send */
  div.block-container div[data-testid="column"] .stButton > button,
  div.block-container .stButton > button {
    padding: 8px 14px;
    border-radius: 999px;
    border: 1px solid #e5e7eb;
    font-size: 0.8rem;
    color: #374151;
    background: #f9fafb;
    white-space: normal;
    min-height: 2.2em;
  }
  div.block-container .stButton > button:hover {
    background: #eff6ff;
    border-color: #bfdbfe;
  }
  /* Chip row spacing */
  .mf-chips-row { padding: 8px 16px 16px 16px; }
  /* Chat area spacing */
  [data-testid="stChatMessage"] {
    padding: 6px 0;
  }
  [data-testid="stChatMessage"] p { margin: 0; }
  .mf-source {
    font-size: 0.7rem; color: #6b7280; margin-top: 4px;
  }
  .mf-source a { color: #2563eb; text-decoration: none; }
  .mf-source a:hover { text-decoration: underline; }
  .mf-updated { font-size: 0.7rem; color: #6b7280; margin-top: 2px; }
  /* Chat input: visible send button - multiple selectors for different Streamlit versions */
  .stChatFloatingInputContainer button,
  div:has(textarea[placeholder*="factual"]) button,
  [data-testid="stChatInputContainer"] button,
  section[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #2563eb, #22c55e) !important;
    color: white !important;
    border: none !important;
    border-radius: 50% !important;
    min-width: 38px !important;
    width: 38px !important;
    height: 38px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
  }
  .stChatFloatingInputContainer button:hover,
  div:has(textarea[placeholder*="factual"]) button:hover,
  [data-testid="stChatInputContainer"] button:hover,
  section[data-testid="stChatInput"] button:hover {
    opacity: 0.95;
  }
  .stChatFloatingInputContainer button svg,
  div:has(textarea[placeholder*="factual"]) button svg {
    fill: white !important;
  }
</style>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state["history"] = []

index = get_index()

# Process chip click from previous run
if st.session_state.get("chip_query"):
    q = st.session_state.pop("chip_query", None)
    if q and q.strip():
        ans = answer_query_phase2(q, index=index)
        st.session_state["history"].append({
            "query": q,
            "text": ans.text,
            "source_url": ans.source_url,
            "last_updated": ans.last_updated,
            "refused": ans.refused,
        })
    st.rerun()

# Header
st.markdown("""
<div class="mf-header">
  <div class="mf-header-left">
    <div class="mf-avatar">MF</div>
    <div>
      <p class="mf-title">Mutual Fund FAQ assistant</p>
      <p class="mf-status">We're online • Facts-only</p>
    </div>
  </div>
</div>
<p class="mf-subtitle">Answers factual questions using only public information from Groww stored in embeddings, with one clear source link in every answer.</p>
<p class="mf-note">Note: Facts-only. No investment advice. No PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.</p>
""", unsafe_allow_html=True)

# Chips: two rows so no truncation; consistent spacing
st.markdown('<div class="mf-chips-row">', unsafe_allow_html=True)
r1c1, r1c2 = st.columns(2)
with r1c1:
    if st.button("ELSS lock-in period?"):
        st.session_state["chip_query"] = "What is the ELSS lock-in period for tax-saving mutual funds?"
        st.rerun()
with r1c2:
    if st.button("Download capital-gains statement?"):
        st.session_state["chip_query"] = "How can I download my capital-gains statement on Groww?"
        st.rerun()
if st.button("What is expense ratio?"):
    st.session_state["chip_query"] = "What is an expense ratio in a mutual fund?"
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# Chat area: welcome + history
st.markdown('<div class="mf-chat-wrap">', unsafe_allow_html=True)

with st.chat_message("assistant", avatar="📈"):
    st.markdown("Hi, I'm your mutual fund FAQ assistant. Ask a factual question about mutual funds on Groww and I'll answer with a source link.")

for turn in st.session_state["history"]:
    with st.chat_message("user"):
        st.markdown(turn["query"])
    with st.chat_message("assistant", avatar="📈"):
        st.markdown(turn["text"])
        if turn.get("source_url"):
            st.markdown(f'<p class="mf-source">Source: <a href="{turn["source_url"]}" target="_blank" rel="noopener">{turn["source_url"]}</a></p>', unsafe_allow_html=True)
        if turn.get("last_updated"):
            st.caption(f"Last updated from sources: {turn['last_updated']}")

# Chat input at bottom
prompt = st.chat_input("Type a factual mutual fund question...")
if prompt and prompt.strip():
    ans = answer_query_phase2(prompt, index=index)
    st.session_state["history"].append({
        "query": prompt,
        "text": ans.text,
        "source_url": ans.source_url,
        "last_updated": ans.last_updated,
        "refused": ans.refused,
    })
    st.rerun()
