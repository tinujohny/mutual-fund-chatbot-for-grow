# Mutual Fund FAQ Chatbot (Groww)

A facts-only mutual fund FAQ assistant that uses public information from Groww. Answers factual questions with source links; refuses advice, PII, and performance claims.

## Run locally

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Run the Streamlit app (backend + chat UI)
python3 -m streamlit run streamlit_app.py
```

## Deploy: Backend (Streamlit) + Frontend (Vercel)

**Backend** runs on **Streamlit Community Cloud** (chat app + RAG + Groq).  
**Frontend** runs on **Vercel** (landing page that embeds the Streamlit app).

👉 **Step-by-step instructions:** see **[DEPLOY.md](DEPLOY.md)**.

Quick summary:

1. **Streamlit:** Connect your GitHub repo → set main file to `streamlit_app.py` → set Python 3.11 → add `GROQ_API_KEY` in Secrets.
2. **Vercel:** Import the same repo → set **Root Directory** to `frontend` → deploy.
3. **Connect:** In `frontend/index.html`, replace `YOUR-STREAMLIT-APP-URL` with your Streamlit app URL, then push to GitHub so Vercel redeploys.

## Repo structure

- `streamlit_app.py` – Streamlit entrypoint (used for local run and Streamlit Cloud).
- `src/phase1/` – Data ingestion and retrieval (Groww crawl, chunks, keyword search).
- `src/phase2/` – QA with Groq, policy (PII, intent), config.
- `frontend/index.html` – Static page for Vercel that embeds the Streamlit app.
- `DEPLOY.md` – Full deployment guide.
