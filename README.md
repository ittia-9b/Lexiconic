# Lexiconic-pyobjc

A macOS menu bar application for real-time speech transcription with global hotkey controls.

## Description

Lexiconic is a menu bar application for macOS that provides real-time speech transcription with global hotkey controls. Built using PyObjC and OpenAI's Whisper API, it integrates seamlessly with the macOS interface and allows you to transcribe audio with simple keyboard shortcuts.

## Features

- Real-time speech transcription using OpenAI's Whisper API
- Global hotkey controls (Option+Left Arrow to start/stop transcription)
- Auto-paste functionality that types live transcription without clipboard pollution
- LLM post-processing for transcription cleanup (capitalization, punctuation, word corrections)
- System menu bar integration with 🎤 icon
- Native macOS look and feel

## Requirements

- macOS 10.9 or later
- Python 3.7+
- PyObjC
- OpenAI API key for transcription and LLM post-processing

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/Lexiconic-pyobjc.git
cd Lexiconic-pyobjc
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install pyobjc openai python-dotenv
```

4. Set up your OpenAI API key:
Create a `.env` file in the project root with your OpenAI API key:
```bash
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the application:
```bash
python src/whisper_broke_app.py
```

The application will appear in your menu bar with a 🎤 icon. Click on it to access the menu options.

### Hotkeys
- Option+Left Arrow: Toggle real-time transcription on/off

### Menu Options
- 🎤 Start/Stop Real-time Transcription: Toggle transcription
- 📋 Copy Last Transcription: Copy the last transcription to clipboard
- 📂 Transcribe Audio File: Select an audio file to transcribe
- ⌨️ Enable/Disable Auto-Paste: Toggle auto-paste functionality
- 🧠 Enable/Disable LLM Cleanup: Toggle LLM post-processing
- ℹ️ About: Show application information
- ⚙️ Quit: Exit the application

### Accessibility Permissions
To fully block the default Option+Left Arrow behavior (preventing cursor movement), you need to grant Accessibility permissions:
1. Open System Preferences > Security & Privacy > Privacy
2. Select Accessibility from the left sidebar
3. Click the lock icon and enter your password
4. Add this application (Python or your terminal) to the list
5. Restart the application

Without these permissions, the hotkey will work but won't block the default macOS behavior.

## Development

For development, you can modify `src/whisper_broke_app.py` to add new features or customize existing ones. The application uses PyObjC to interface with native macOS APIs.

### Project Structure
- `src/whisper_broke_app.py`: Main application code
- `src/audio_transcriber.py`: Audio transcription functionality
- `run_whisper_broke.py`: Launcher script
- `.env`: Environment variables

### Dependencies
- `pyobjc`: Python to Objective-C bridge for macOS APIs
- `openai`: OpenAI API client for transcription and LLM processing
- `python-dotenv`: Environment variable management

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [PyObjC](https://pyobjc.readthedocs.io/)
- macOS integration powered by Cocoa frameworks
