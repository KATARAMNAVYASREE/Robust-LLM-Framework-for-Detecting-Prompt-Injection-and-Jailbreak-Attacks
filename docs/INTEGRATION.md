# Integration steps

1. Activate the existing `.venv` in the existing project directory.
2. Install add-on dependencies:
   `pip install streamlit fastapi uvicorn beautifulsoup4`
3. Copy `security_layer/`, `security_dashboard.py`, and `security_api.py` into the existing project root. Do not overwrite `app/detector.py` or model artifacts.
4. Launch dashboard: `streamlit run security_dashboard.py`
5. Launch API in another terminal: `uvicorn security_api:app --reload`
6. Open `http://127.0.0.1:8000/docs` for interactive API documentation.
7. Test `/health` first, then `/analyze`.
8. In dashboard settings, audit text storage is disabled by default. Enable it only for synthetic test prompts or where you have permission to store inputs.
9. Run your existing tests after integration: `python -m pytest -q`.

## Security integration notes
- Keep this service local during development.
- Do not expose the API publicly without authentication, rate limits, HTTPS, and deployment hardening.
- A `BLOCK` or `ALLOW` decision is not a security guarantee.
- Document scanning should occur before adding content to a vector store. Re-scan retrieved chunks at query time as well.
- Do not pass untrusted document instructions to an LLM as privileged instructions.
