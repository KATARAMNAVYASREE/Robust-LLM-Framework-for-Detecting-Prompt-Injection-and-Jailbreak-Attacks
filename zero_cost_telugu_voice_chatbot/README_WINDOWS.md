# Zero-Cost Telugu Voice Chatbot for Windows

## Safety and compatibility
Copy these files into the existing project root, the folder containing `app\detector.py`.
Do NOT overwrite `app\detector.py`, your trained `.joblib` model, or `security_logs.db`.
The app imports and calls your existing `analyze_text()` before Ollama. It sends a prompt only when the detector action maps to `ALLOW`; unknown return formats fail closed to `REVIEW`.

## Install
Recommended: 64-bit Python 3.11. From PowerShell in the existing project root:
```powershell
py -0p
Set-ExecutionPolicy -Scope Process Bypass
.\setup_windows.ps1
```
If Python 3.11 is missing, install it from python.org. The setup script uses a separate `.venv-voice` environment so your existing `.venv` and installed packages remain untouched.

Ensure Ollama is installed and the model exists:
```powershell
ollama list
ollama pull qwen2.5:3b
```
Start the app:
```powershell
.\.venv-voice\Scripts\python.exe -m streamlit run local_multilingual_chatbot.py
```

## How it works
1. Record Telugu speech.
2. Click Transcribe Telugu.
3. Review the original Telugu transcript and Romanized text.
4. Correct mistakes, then click Check security and send.
5. Only an `ALLOW` result is sent to local Ollama.

## Important transliteration note
ITRANS converts Telugu script into Latin characters. It is not an English translation and may not match casual Telugu texting exactly. Transliteration cannot correct words that speech recognition heard incorrectly, so review the transcript.

## Hardware / realistic limitations
- First-time setup downloads the packages and quantized Telugu ONNX model (~190 MB plus tokens); extra space is needed for Python packages and Ollama's model.
- The app uses CPU inference with 2–4 threads. CPU-only systems can be slow, especially on the first model load.
- 16 GB RAM is preferable when VS Code, a browser, Ollama and the speech model run together; 8 GB may be tight.
- Accuracy depends on accent, noise, microphone quality, sentence length and Telugu-English code-switching. No ASR guarantees exact transcripts.
- Speech processing and chatbot inference are local after download; internet is needed for initial downloads only.
- This is a prototype security layer, not a guarantee that all prompt injection will be detected.

## Troubleshooting
- `ModuleNotFoundError: app`: run Streamlit from the project root that contains `app\detector.py`.
- Model missing: rerun `.\setup_windows.ps1`.
- Ollama unavailable: open Ollama from Start, or run `ollama serve` in a separate terminal.
- All messages show REVIEW: inspect the dictionary returned by `analyze_text()` and map its actual action field in `security_action()` in this new file only. Do not replace the detector or model.
