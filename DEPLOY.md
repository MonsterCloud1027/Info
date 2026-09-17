# Deploy Expert Rate App to Streamlit Community Cloud

## 1. Push this project to GitHub

Create a **public** GitHub repository (or private if your Streamlit account supports it), then push `main`.

Required files in the repo:

- `expert_rate_app.py` — app entry point
- `choose/` — rating images
- `requirements.txt`
- `expert_ratings/` — optional; created automatically online

## 2. Deploy on Streamlit Cloud

1. Open https://share.streamlit.io/ and sign in with GitHub
2. **New app**
3. Select the repository, branch `main`
4. Main file path: `expert_rate_app.py`
5. Click **Deploy**

You will get a URL like `https://xxxxx.streamlit.app` to share with mentors.

## 3. Important note about ratings storage

Streamlit Cloud’s disk can reset when the app sleeps or restarts.  
In the **Results** page, use **Download all ratings (JSON)** regularly to keep a backup.

## Local run

```bash
streamlit run expert_rate_app.py
```
