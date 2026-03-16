# Deploy: Backend on Streamlit, Frontend on Vercel

This guide walks you through deploying the **backend (chat app)** on **Streamlit Community Cloud** and the **frontend (landing page with embedded chat)** on **Vercel**, using the same GitHub repo.

---

## Prerequisites

- A **GitHub** account and this repo pushed to GitHub (e.g. `https://github.com/tinujohny/mutual-fund-chatbot-for-grow`)
- A **Streamlit Community Cloud** account (free): [share.streamlit.io](https://share.streamlit.io)
- A **Vercel** account (free): [vercel.com](https://vercel.com)
- Your **Groq API key** (for the chatbot)

---

## Part 1: Deploy backend on Streamlit Cloud

1. **Go to Streamlit Community Cloud**  
   Open [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.

2. **Create a new app**  
   - Click **“New app”**.
   - **Repository:** choose `tinujohny/mutual-fund-chatbot-for-grow` (or your repo).
   - **Branch:** `main`.
   - **Main file path:** `streamlit_app.py`.
   - Click **“Advanced settings”** and set **Python version** to **3.11** (required for dependencies).
   - Click **“Deploy”**.

3. **Add secrets**  
   After the app is created:
   - Open your app → **“Manage app”** (or the three dots) → **“Settings”** → **“Secrets”**.
   - Add:
     ```env
     GROQ_API_KEY=your_groq_api_key_here
     GROQ_MODEL=llama-3.1-8b-instant
     ```
   - Save. The app will redeploy.

4. **Copy your Streamlit app URL**  
   Once the app is running, copy the URL from the browser, e.g.:
   - `https://mutual-fund-chatbot-for-groww.streamlit.app`  
   You will need this for the frontend in Part 2.

5. **Optional: custom subdomain**  
   In **“Manage app” → “Settings”**, you can set a custom subdomain (e.g. `mutual-fund-chatbot-for-groww`).

---

## Part 2: Deploy frontend on Vercel

1. **Go to Vercel**  
   Open [vercel.com](https://vercel.com) and sign in with GitHub.

2. **Import the same GitHub repo**  
   - Click **“Add New…” → “Project”**.
   - Import `tinujohny/mutual-fund-chatbot-for-grow` (or your repo).
   - **Important:** Before deploying, set **“Root Directory”** to **`frontend`**:
     - Click **“Edit”** next to “Root Directory”.
     - Choose **“frontend”** (the folder that contains `index.html`).
     - Confirm.
   - Leave **Framework Preset** as “Other” (no build step).
   - Click **“Deploy”**.

3. **Point the frontend to your Streamlit app**  
   After the first deploy, the frontend will still have a placeholder URL. Update it to your real Streamlit URL:

   - In your repo, open **`frontend/index.html`**.
   - Find the line:
     ```javascript
     var STREAMLIT_APP_URL = 'https://YOUR-STREAMLIT-APP-URL.streamlit.app';
     ```
   - Replace `https://YOUR-STREAMLIT-APP-URL.streamlit.app` with your actual Streamlit URL (from Part 1, step 4), e.g.:
     ```javascript
     var STREAMLIT_APP_URL = 'https://mutual-fund-chatbot-for-groww.streamlit.app';
     ```
   - Also update the `src` in the iframe on the line above it to the same URL:
     ```html
     <iframe ... src="https://mutual-fund-chatbot-for-groww.streamlit.app" ...>
     ```
   - Save, commit, and push to GitHub:
     ```bash
     git add frontend/index.html
     git commit -m "Use Streamlit app URL in frontend"
     git push
     ```
   - Vercel will automatically redeploy. Your Vercel URL (e.g. `https://your-project.vercel.app`) will then show the landing page with the chat embedded.

---

## Part 3: GitHub – what to push

Ensure these are in your repo and pushed to `main` (or the branch you use):

| Path | Purpose |
|------|--------|
| `streamlit_app.py` | Streamlit entrypoint (backend + chat UI) |
| `src/` | Phase 1 & 2 code (ingest, retriever, QA, config) |
| `requirements.txt` | Python deps for Streamlit |
| `runtime.txt` | Optional: `python-3.11` for Streamlit |
| `frontend/index.html` | Vercel frontend (iframe to Streamlit) |
| `vercel.json` | Optional Vercel config at repo root |

**Do not** commit:

- `.env` (use Streamlit Secrets for `GROQ_API_KEY`)
- `data/` (ingested data; Streamlit will rebuild if missing)

---

## Summary

| Service | URL you get | Role |
|--------|-------------|------|
| **Streamlit** | `https://<your-app>.streamlit.app` | Backend + chat app (runs RAG, Groq, UI) |
| **Vercel** | `https://<your-project>.vercel.app` | Frontend page that embeds the Streamlit app in an iframe |

Users open the **Vercel URL**; the page loads and shows the Streamlit chat inside the iframe. All chat logic and API calls run in the Streamlit app.

---

## Troubleshooting

- **Streamlit: “Error installing requirements”**  
  Make sure **Python version** is set to **3.11** in Streamlit Cloud (Advanced settings). If the app was created with a different version, delete the app and create a new one with 3.11.

- **Streamlit: “ModuleNotFoundError: dotenv”**  
  Ensure `requirements.txt` includes `python-dotenv==1.0.1` and that you’ve pushed the change.

- **Streamlit: “FileNotFoundError” for chunks**  
  On first run, the app will try to crawl and build the index. If Groww blocks requests from the cloud, run ingestion locally once, then commit `data/chunks.jsonl` (and adjust `.gitignore` if needed) so the file is in the repo.

- **Vercel: blank or wrong page**  
  Confirm **Root Directory** is set to **`frontend`** and that `frontend/index.html` has the correct Streamlit URL in both the iframe `src` and the `STREAMLIT_APP_URL` variable.

- **Frontend shows “refused to connect” in iframe**  
  Check that the Streamlit URL in `frontend/index.html` is correct and that the Streamlit app loads when opened in a new tab.
