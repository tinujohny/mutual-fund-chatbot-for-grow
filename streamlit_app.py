import streamlit as st

from src.phase1.retriever import load_index
from src.phase2.qa import answer_query_phase2

@st.cache_resource
def get_index():
    return load_index()

st.set_page_config(page_title="Mutual Fund FAQ assistant", page_icon="📈")

st.markdown("### Mutual Fund FAQ assistant")
st.markdown(
    "Answers factual questions using only public information from Groww stored in embeddings, "
    "with one clear source link in every answer.\n\n"
    "**Facts-only. No investment advice. No PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers.**"
)

query = st.text_input("Ask a factual mutual fund question:")

if "history" not in st.session_state:
    st.session_state["history"] = []

index = get_index()

if st.button("Ask") and query.strip():
    ans = answer_query_phase2(query, index=index)
    st.session_state["history"].append(
        {
            "query": query,
            "text": ans.text,
            "source_url": ans.source_url,
            "last_updated": ans.last_updated,
            "refused": ans.refused,
        }
    )

for turn in reversed(st.session_state["history"]):
    st.markdown(f"**You:** {turn['query']}")
    st.markdown(f"**Bot:** {turn['text']}")
    if turn["source_url"]:
        st.markdown(f"Source: [{turn['source_url']}]({turn['source_url']})")
    if turn["last_updated"]:
        st.caption(f"Last updated from sources: {turn['last_updated']}")
    st.markdown("---")