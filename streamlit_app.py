import streamlit as st

from src.phase1.retriever import load_index
from src.phase2.qa import answer_query_phase2

# Bump when you deploy — if you don’t see this line on Streamlit Cloud, the new code isn’t live yet.
APP_UI_VERSION = "2025-03-18 bordered-chat"

@st.cache_resource
def get_index():
    return load_index()

st.set_page_config(
    page_title="Mutual Fund FAQ assistant",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Centered header (minimal HTML — avoids heavy CSS that breaks embed layout)
st.markdown(
    """
<div style="text-align: center; max-width: 42rem; margin: 0 auto 1rem auto;">
  <h2 style="margin: 0 0 0.35rem 0; font-weight: 600;">Mutual Fund FAQ assistant</h2>
  <p style="margin: 0; color: #6b7280; font-size: 0.95rem; line-height: 1.45;">
    Answers factual questions using only public information from Groww stored in embeddings,
    with <strong>one clear source link</strong> in every answer.
  </p>
  <p style="margin: 0.6rem 0 0 0; font-size: 0.88rem; line-height: 1.4;">
    <strong>Facts-only.</strong> No investment advice. No PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.
  </p>
</div>
""",
    unsafe_allow_html=True,
)
st.caption(f"UI: {APP_UI_VERSION} — if this text is missing after refresh, push latest `streamlit_app.py` to GitHub and reboot the app.")

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

st.markdown(
    """
<p style="text-align:center;margin:1rem 0 0.6rem 0;color:#9ca3af;font-size:0.9rem;">Try one of these:</p>
""",
    unsafe_allow_html=True,
)
# Centered row with space between chips
_pad_l, ex1, ex2, ex3, _pad_r = st.columns([0.08, 1, 1, 1, 0.08])
with ex1:
    if st.button("ELSS lock-in?", use_container_width=True, key="chip_elss"):
        st.session_state["chip_query"] = "What is the ELSS lock-in period for tax-saving mutual funds?"
        st.rerun()
with ex2:
    if st.button("Capital-gains statement?", use_container_width=True, key="chip_cg"):
        st.session_state["chip_query"] = "How can I download my capital-gains statement on Groww?"
        st.rerun()
with ex3:
    if st.button("Expense ratio?", use_container_width=True, key="chip_er"):
        st.session_state["chip_query"] = "What is an expense ratio in a mutual fund?"
        st.rerun()

st.markdown(
    """
<style>
  /* Bordered chat panel + breathing room above chat input */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border-color: #4b5563 !important;
    padding: 0.75rem 0.5rem 0.5rem 0.5rem !important;
    margin-top: 0.25rem !important;
    margin-bottom: 1rem !important;
    max-width: 42rem;
    margin-left: auto !important;
    margin-right: auto !important;
  }
  [data-testid="stChatInput"] {
    margin-top: 0.5rem !important;
    max-width: 42rem;
    margin-left: auto !important;
    margin-right: auto !important;
  }
</style>
""",
    unsafe_allow_html=True,
)

# Clear gap between suggestion buttons and chat area
st.markdown('<div style="height: 1.25rem;"></div>', unsafe_allow_html=True)

with st.container(border=True):
    with st.chat_message("assistant", avatar="📈"):
        st.markdown(
            "Hi, I'm your mutual fund FAQ assistant. Ask a factual question about mutual funds on Groww "
            "and I'll answer with a source link."
        )

    for turn in st.session_state["history"]:
        with st.chat_message("user"):
            st.markdown(turn["query"])
        with st.chat_message("assistant", avatar="📈"):
            st.markdown(turn["text"])
            if turn.get("source_url"):
                st.markdown(f"Source: [{turn['source_url']}]({turn['source_url']})")
            if turn.get("last_updated"):
                st.caption(f"Last updated from sources: {turn['last_updated']}")

# Chat input at bottom (outside bordered box so it stays usable)
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
