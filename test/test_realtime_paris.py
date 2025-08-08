#!/usr/bin/env python3
"""
Test: Simulate hotkey-driven realtime transcription using test/test1-paris.m4a

This test connects to OpenAI Realtime API and streams the provided audio file
as PCM16 24kHz chunks, paced like live input. It expects to receive at least
one transcription event. Exits with non-zero status if no transcription is
received or if prerequisites are missing.

Prerequisites:
- OPENAI_API_KEY in environment or .env
- ffmpeg installed and on PATH
- Internet connectivity

Run:
  python test/test_realtime_paris.py

(Optional with pytest):
  pytest -q test/test_realtime_paris.py
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path

# Ensure src is importable
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    # Proceed without dotenv
    pass

from realtime_transcription_test import RealtimeTranscriber  # noqa: E402

AUDIO_PATH = ROOT / "test" / "test1-paris.m4a"


def require_prereqs():
    missing = []
    if not os.getenv("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if not AUDIO_PATH.exists():
        missing.append(str(AUDIO_PATH))
    if missing:
        raise SystemExit(
            "Missing prerequisites: " + ", ".join(missing) +
            "\nSet OPENAI_API_KEY in .env, install ffmpeg (e.g., `brew install ffmpeg`), "
            "and ensure the test audio file exists."
        )


async def run_test():
    require_prereqs()

    api_key = os.getenv("OPENAI_API_KEY")
    transcriber = RealtimeTranscriber(api_key)

    print("Simulating hotkey: ⌥← (start)")
    try:
        await transcriber.connect()
        # Start background listener for responses
        response_task = asyncio.create_task(transcriber.listen_for_responses())

        # Stream the file as if live
        await transcriber.stream_file(str(AUDIO_PATH), realtime_factor=1.0, send_commit=True)

        # Give some time for the server to finalize and send transcripts
        await asyncio.sleep(2.0)

        transcriptions = transcriber.get_transcriptions()
        if transcriptions:
            print("\nReceived transcriptions:")
            for i, t in enumerate(transcriptions, 1):
                print(f"{i}. {t}")
        else:
            print("\nNo transcriptions received.")

        # Stop
        print("Simulating hotkey: ⌥← (stop)")
        response_task.cancel()

        # Decide pass/fail
        if not transcriptions or not any(s.strip() for s in transcriptions):
            raise SystemExit(1)

    finally:
        await transcriber.cleanup()


def main():
    try:
        asyncio.run(run_test())
        print("\n✅ Test passed: at least one transcription was received.")
    except SystemExit as e:
        if e.code != 0:
            print("\n❌ Test failed.")
        raise
    except Exception as e:
        print(f"\n❌ Test encountered an error: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
