# Lexiconic

Lexiconic is a macOS menu bar application that transcribes speech using OpenAI's APIs. It can capture audio from your microphone for real-time transcription or process existing audio files, all controlled from a small microphone icon in the menu bar.

## Features

- **Live microphone transcription** powered by OpenAI's Realtime and Whisper models
- **File transcription** for existing audio recordings
- **Global hotkey (⌥←)** to start/stop or momentarily hold transcription
- **Auto-paste** option that types results into the active app without touching the clipboard
- **LLM cleanup** to add capitalization, punctuation and minor fixes
- **Copy last transcription** from the menu bar

## Installation

```bash
git clone https://github.com/yourusername/Lexiconic.git
cd Lexiconic
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-yourkey
```

## Usage

Run the launcher script:

```bash
python run_lexiconic.py
```

A microphone icon (🎤) will appear in the macOS menu bar. Use the menu or the ⌥← hotkey to control transcription.

### Accessibility permissions

To fully block the default Option+Left Arrow behavior, grant Accessibility permission to Python or your terminal in **System Settings > Privacy & Security > Accessibility**, then restart the app.

## Development

- `src/lexiconic_app.py` – menu bar interface and hotkey logic
- `src/realtime_transcription_test.py` – real-time transcription engine
- `src/whisper_transcription.py` – file-based transcription helpers
- `run_lexiconic.py` – entry point

Pull requests and suggestions are welcome.

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
