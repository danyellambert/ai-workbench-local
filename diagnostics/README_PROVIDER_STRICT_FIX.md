# Provider strict runtime fix

Replace these files in the repository:

- `src/services/runtime_controls.py`
- `src/providers/registry.py`
- `diagnostics/sitecustomize.py` (optional, only for future tracing)

What changed:

- Runtime provider resolution no longer silently falls back to another provider when the active profile selected a provider explicitly.
- Preferences/Runtime Controls no longer probe remote providers automatically while rendering payloads.
- Ollama Hosted API-key configured status now checks the macOS Keychain credential, not only the environment variable.
- Ollama Hosted model names are canonicalized for the current presets:
  - `nemotron-3-nano:30b` -> `nemotron-3-nano:30b-cloud`
  - `nemotron-3-super` -> `nemotron-3-super:cloud`
- The diagnostics `sitecustomize.py` now traces `urllib.request.urlopen`, which is what `OllamaProvider` uses for native/Ollama-compatible HTTP calls.

After replacing the files, restart the app.
