# Robust LLM Security Shield — upgrade add-on

This add-on is designed to sit beside the existing project. It imports the existing `app.detector.analyze_text` function and does not replace the trained model or existing detector.

## Features
- Redesigned Streamlit dashboard with prompt, voice, document/RAG, evaluation, analytics, and about tabs.
- HTML comment / hidden-element / script-style content indicators, zero-width and bidi control checks, limited Base64 decoding.
- Explainability panel with matched suspicious spans and detector evidence.
- CSV evaluation runner for labeled `text,label` data and standard metrics.
- Local audit analytics and CSV export; prompt text storage is off by default.
- FastAPI endpoints `/health`, `/analyze`, and `/scan-document`.
- Optional offline/local speech transcription using `faster-whisper`; no paid API or API key.

## Install (Windows PowerShell, from project root)
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-upgrade.txt
python -m pip install pytest
```
If Streamlit/ FastAPI / BeautifulSoup / pandas are already installed, pip will confirm or update compatible versions.

## Run dashboard
```powershell
python -m streamlit run security_shield_dashboard_fixed.py
```

## Run API (new terminal)
```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn security_api:app --reload
```
Open `http://127.0.0.1:8000/docs` for interactive API testing.

## Optional microphone transcription
Install local open-source speech transcription:
```powershell
python -m pip install faster-whisper
```
Restart Streamlit. The first use downloads the selected open-source model files and requires internet access; later inference runs locally. Use the Voice Input tab to record audio, transcribe it, then analyze the transcript. This is record-then-transcribe, not ChatGPT-style live streaming voice.

## Test the add-on
```powershell
python -m pytest tests/test_upgrade_features.py -q
```
Run from the project root so Python can import the existing `app` package.

## Important limitations
- This add-on does not provide an LLM response-generation/chat engine. It scans input and reports a security decision. To generate answers in multiple languages, connect a local multilingual model separately; the current feature transcribes speech and analyzes text.
- The detector's quality in Telugu, Romanized Telugu and code-mixed text depends on its model/data; accepting multilingual input is not the same as reliable multilingual detection.
- HTML checks are heuristics, not a browser renderer. They do not guarantee detection of every hidden payload or encoded attack.
- Review/Block policies should be validated on independent, labeled data before deployment.
- Do not expose the local API to the public internet without authentication, rate limiting, request limits, and a security review.
