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

st.markdown("### Mutual Fund FAQ assistant")
st.markdown(
    "Answers factual questions using only public information from Groww stored in embeddings, "
    "with **one clear source link** in every answer.\n\n"
    "**Facts-only. No investment advice. No PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.**"
)

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

st.markdown("Try one of these:")
ex1, ex2, ex3 = st.columns(3)
with ex1:
    if st.button("ELSS lock-in?"):
        st.session_state["chip_query"] = "What is the ELSS lock-in period for tax-saving mutual funds?"
        st.rerun()
with ex2:
    if st.button("Capital-gains statement?"):
        st.session_state["chip_query"] = "How can I download my capital-gains statement on Groww?"
        st.rerun()
with ex3:
    if st.button("Expense ratio?"):
        st.session_state["chip_query"] = "What is an expense ratio in a mutual fund?"
        st.rerun()

with st.chat_message("assistant", avatar="📈"):
    st.markdown("Hi, I'm your mutual fund FAQ assistant. Ask a factual question about mutual funds on Groww and I'll answer with a source link.")

for turn in st.session_state["history"]:
    with st.chat_message("user"):
        st.markdown(turn["query"])
    with st.chat_message("assistant", avatar="📈"):
        st.markdown(turn["text"])
        if turn.get("source_url"):
            st.markdown(f"Source: [{turn['source_url']}]({turn['source_url']})")
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
