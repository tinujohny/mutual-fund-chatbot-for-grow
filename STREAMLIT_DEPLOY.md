# Deploy this app on Streamlit Community Cloud

## Important: Python version

Streamlit Community Cloud **ignores `runtime.txt`** for existing apps. The Python version is chosen **only when you first create the app**, in **Advanced settings**.

If you see **"Error installing requirements"** and logs show **Building wheel for pillow … error** or **python3.14**, your app was created with Python 3.14. Pillow does not install reliably on 3.14 on Cloud.

### Fix: Redeploy with Python 3.11

1. **Save your settings**  
   In Streamlit Cloud → your app → **Manage app**, note or save:
   - Repository URL and branch
   - Main file path (`streamlit_app.py`)
   - **Secrets** (e.g. `GROQ_API_KEY`, `GROQ_MODEL`) — copy them somewhere safe.

2. **Delete the app**  
   In **Manage app**, use **Delete app** (or equivalent). This is required; you cannot change Python version in place.

3. **Create a new app**
   - **New app** → connect the same repo and branch.
   - Set **Main file path** to `streamlit_app.py`.
   - Open **Advanced settings**.
   - In **Python version**, select **3.11** (do not leave default 3.12/3.14).
   - Save.

4. **Restore secrets**  
   In the new app’s **Settings → Secrets**, paste back your secrets (e.g. `GROQ_API_KEY`, `GROQ_MODEL`).

5. **Deploy**  
   Streamlit will install from `requirements.txt` using Python 3.11; Pillow will install from a wheel and the app should start.

## requirements.txt

Keep only:

```
streamlit==1.33.0
httpx==0.27.0
beautifulsoup4==4.12.3
```

No need to add `pillow` or `numpy`; Streamlit brings compatible versions when the Python version is 3.11.
