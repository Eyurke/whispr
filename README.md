# Whispr

**Local push-to-talk dictation for Windows.** Hold a hotkey, speak, release — your words are typed into whatever app you're using. An open, offline alternative to [Wispr Flow](https://wisprflow.ai/) / Typeless: all speech recognition runs on your machine via [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and nothing ever leaves it.

```
        hold Ctrl+Win ──► speak ──► release ──► text appears where your cursor is
```

## Features

- **Works in every app** — Slack, browsers, editors, terminals, email: text is inserted into whatever has focus, via fast clipboard-paste (clipboard is restored afterwards) or simulated typing.
- **Push-to-talk + hands-free** — hold `Ctrl+Win` to talk; a quick tap locks recording so you can speak hands-free, tap again to finish. `Esc` cancels.
- **100% offline & private** — Whisper runs locally (CPU int8 or CUDA float16, picked automatically). No account, no cloud, no telemetry.
- **Clean text out** — automatic punctuation and capitalization, filler-word removal (*um, uh, hmm*), smart spacing so consecutive dictations chain naturally.
- **Personal dictionary** — names and jargon are passed to Whisper as hotwords and casing is enforced (e.g. `GitHub`, `Wispr Flow`).
- **Text replacements** — e.g. `gonna -> going to`, applied automatically.
- **Spoken commands** *(optional)* — "new line", "new paragraph".
- **Live overlay** — a small pill at the bottom of the screen shows mic levels while you speak and progress while transcribing; it never steals focus.
- **History & stats** — searchable local history (SQLite) with words/minute stats. Double-click any entry to copy it.
- **99 languages** — Whisper multilingual models; set a fixed language or auto-detect.
- **System tray app** — pause/resume, settings, history, start-with-Windows.

## Install

Requirements: Windows 10/11, Python 3.10–3.13, a microphone. (No GPU needed — a modern CPU transcribes a sentence in about a second; an NVIDIA GPU is used automatically if present.)

```powershell
git clone https://github.com/Eyurke/whispr.git
cd whispr
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

The installer creates a virtual environment, installs dependencies, and puts **Whispr** in your Start Menu. On first run the speech model (~460 MB for `small`) is downloaded once, then everything is offline.

Run it directly instead:

```powershell
.venv\Scripts\pythonw.exe run_whispr.pyw
```

## Usage

| Action | How |
|---|---|
| Dictate | Hold `Ctrl+Win`, speak, release |
| Hands-free mode | Tap `Ctrl+Win` quickly — recording locks; tap again to finish |
| Cancel a recording | `Esc` |
| Pause/resume, settings, history | Right-click the tray icon |

The overlay pill shows what's happening: **purple bars** = listening (bars follow your voice), **dots** = transcribing, **✓** = text inserted.

## Choosing a model

Open **Settings… → Speech model** from the tray icon.

| Model | Size | Speed (Ryzen-class CPU) | Quality |
|---|---|---|---|
| `tiny` / `base` | 75–145 MB | instant | okay for quick notes |
| `small` *(default)* | 460 MB | ~1 s per sentence | very good |
| `distil-large-v3` | 1.5 GB | ~2–3 s | excellent (English) |
| `large-v3` | 3 GB | slowest | best, all languages |

## Privacy

Everything is local: audio is captured to RAM, transcribed on your machine, and discarded. History is a local SQLite file in `%APPDATA%\Whispr` (you can turn it off or clear it in Settings). The only network access ever made is the one-time model download from Hugging Face.

## Troubleshooting

- **Nothing is typed into elevated (admin) windows** — Windows blocks input injection into elevated apps from non-elevated ones. Run Whispr as administrator if you need to dictate into admin windows.
- **Hotkey doesn't respond in some games** — some anticheat/fullscreen apps swallow low-level hooks; try a different hotkey (e.g. `f9`) in Settings.
- **"Didn't catch that"** — the mic heard silence. Check Windows' default input device or pick a specific microphone in Settings.
- **Paste doesn't work in a specific app** — switch *Insert text by* to *Typing* in Settings.
- Logs live at `%APPDATA%\Whispr\whispr.log`.

## Development

```powershell
.venv\Scripts\python.exe -m pytest            # full suite (e2e tests need an idle desktop)
.venv\Scripts\python.exe -m pytest -m "not e2e"  # fast logic tests only
.venv\Scripts\python.exe -m whispr            # run with console output
```

Architecture: a `keyboard` low-level hook feeds a pure push-to-talk state machine (`hotkey.py`); audio is captured with `sounddevice` (`audio.py`), transcribed by faster-whisper (`transcriber.py`), cleaned up (`formatter.py`), and injected with SendInput (`inject.py`). Tk renders the overlay/settings/history; pystray runs the tray icon. See module docstrings for the threading model.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with Wispr Flow or Typeless; this is an independent open-source project for personal use.
