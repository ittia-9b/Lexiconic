#!/usr/bin/env python3
"""
OpenAI Realtime Transcription Test Script

This script demonstrates how to use OpenAI's Realtime API for live audio transcription.
It captures audio from your microphone and sends it to OpenAI for real-time transcription.

Requirements:
- OpenAI API key
- pyaudio for audio capture
- websockets for real-time communication
"""

import asyncio
import json
import base64
import os
import sys
import threading
import time
import queue
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Missing python-dotenv. Install with: pip install python-dotenv")
    # Continue if not present, fallback to normal env


try:
    import pyaudio
    import aiohttp
except ImportError:
    print("Missing required packages. Install with:")
    print("pip install pyaudio aiohttp openai")
    sys.exit(1)

# Audio configuration
SAMPLE_RATE = 24000  # OpenAI Realtime API expects 24kHz
CHUNK_SIZE = 1024
CHANNELS = 1
FORMAT = pyaudio.paInt16

class RealtimeTranscriber:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.websocket = None
        self.audio_stream = None
        self.pyaudio_instance = None
        self.is_recording = False
        self.transcription_buffer = []
        self.audio_queue = queue.Queue()
        self.loop = None
        
    async def connect(self):
        """Connect to OpenAI Realtime API"""
        uri = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"
        
        try:
            # Use aiohttp for WebSocket connection with proper headers
            self.session = aiohttp.ClientSession()
            self.websocket = await self.session.ws_connect(
                uri,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "OpenAI-Beta": "realtime=v1"
                }
            )
            print("✅ Connected to OpenAI Realtime API")
            
            # Send session configuration
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["text", "audio"],
                    "instructions": "You are a helpful assistant that transcribes audio in real-time.",
                    "voice": "alloy",
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "whisper-1"
                    },
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.7,  # Increased threshold for less sensitivity
                        "prefix_padding_ms": 500,  # Increased padding before speech
                        "silence_duration_ms": 500  # Increased silence duration to end speech
                    }
                }
            }
            
            await self.websocket.send_str(json.dumps(session_config))
            print("📝 Session configured for transcription")
            
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            raise
    
    def setup_audio(self):
        """Initialize audio capture"""
        self.pyaudio_instance = pyaudio.PyAudio()
        
        try:
            self.audio_stream = self.pyaudio_instance.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE
            )
            print("🎤 Audio capture initialized")
        except Exception as e:
            print(f"❌ Failed to initialize audio: {e}")
            raise
    
    async def _audio_capture_loop(self):
        """Continuously capture audio and queue it for sending"""
        while self.is_recording:
            try:
                if self.audio_stream:
                    # Read audio data
                    audio_data = self.audio_stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    
                    if self.websocket and not self.websocket.closed:
                        # Create audio event
                        audio_event = {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(audio_data).decode('utf-8')
                        }
                        
                        # Send audio data
                        await self._send_audio_data(audio_event)
                
                # Small delay to prevent overwhelming the API
                await asyncio.sleep(0.01)
                
            except Exception as e:
                print(f"⚠️ Error in audio capture: {e}")
                await asyncio.sleep(0.1)
    
    async def _send_audio_data(self, audio_event):
        """Send audio data to websocket"""
        try:
            if self.websocket and not self.websocket.closed:
                await self.websocket.send_str(json.dumps(audio_event))
        except Exception as e:
            print(f"⚠️ Error sending audio data: {e}")
    
    async def listen_for_responses(self):
        """Listen for responses from OpenAI"""
        try:
            async for msg in self.websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_response(data)
                    except json.JSONDecodeError:
                        print(f"⚠️ Invalid JSON received: {msg.data}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"❌ WebSocket error: {self.websocket.exception()}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    print("🔌 Connection closed")
                    break
        except Exception as e:
            print(f"❌ Error listening for responses: {e}")
    
    async def _handle_response(self, data):
        """Handle different types of responses from OpenAI"""
        event_type = data.get("type", "")
        
        if event_type == "session.created":
            print("🎯 Session created successfully")
        
        elif event_type == "input_audio_buffer.speech_started":
            print("🗣️ Speech detected...")
        
        elif event_type == "input_audio_buffer.speech_stopped":
            print("🤫 Speech ended")
        
        elif event_type == "conversation.item.input_audio_transcription.completed":
            transcript = data.get("transcript", "")
            if transcript:
                print(f"📝 Transcription: {transcript}")
                self.transcription_buffer.append(transcript)
        
        elif event_type == "conversation.item.input_audio_transcription.failed":
            error = data.get("error", {})
            print(f"❌ Transcription failed: {error}")
        
        elif event_type == "error":
            error = data.get("error", {})
            print(f"❌ API Error: {error}")
        
        # Uncomment to see all events for debugging
        # else:
        #     print(f"📨 Event: {event_type}")
    
    async def start_recording(self):
        """Start audio recording"""
        self.is_recording = True
        print("🔴 Recording started - speak into your microphone!")
        
        # Start the audio capture loop
        asyncio.create_task(self._audio_capture_loop())
    
    def stop_recording(self):
        """Stop audio recording"""
        self.is_recording = False
        if self.audio_stream:
            self.audio_stream.stop_stream()
        print("⏹️ Recording stopped")
    
    async def cleanup(self):
        """Clean up resources"""
        self.stop_recording()
        
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        
        if hasattr(self, 'session') and self.session:
            await self.session.close()
        
        if self.audio_stream:
            self.audio_stream.close()
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
        
        print("🧹 Cleanup completed")
    
    def get_transcriptions(self):
        """Get all transcriptions collected so far"""
        return self.transcription_buffer.copy()

async def main():
    """Main function to run the realtime transcription test"""
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Please set your OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return
    
    transcriber = RealtimeTranscriber(api_key)
    
    try:
        # Setup
        print("🚀 Starting OpenAI Realtime Transcription Test")
        print("=" * 50)
        
        await transcriber.connect()
        transcriber.setup_audio()
        
        # Start listening for responses in background
        response_task = asyncio.create_task(transcriber.listen_for_responses())
        
        # Start recording
        await transcriber.start_recording()
        
        print("\n💡 Instructions:")
        print("- Speak into your microphone")
        print("- Press Enter to stop recording")
        print("- Type 'quit' to exit")
        print("=" * 50)
        
        # Wait for user input
        def wait_for_input():
            while True:
                user_input = input().strip().lower()
                if user_input == 'quit':
                    return 'quit'
                elif user_input == '':
                    return 'stop'
        
        # Run input waiting in a thread
        input_thread = threading.Thread(target=wait_for_input)
        input_thread.daemon = True
        input_thread.start()
        
        # Keep running until user stops
        while input_thread.is_alive():
            await asyncio.sleep(0.1)
        
        # Stop recording
        transcriber.stop_recording()
        
        # Wait a moment for final transcriptions
        await asyncio.sleep(2)
        
        # Show results
        transcriptions = transcriber.get_transcriptions()
        if transcriptions:
            print("\n📋 Final Transcriptions:")
            print("=" * 50)
            for i, transcript in enumerate(transcriptions, 1):
                print(f"{i}. {transcript}")
        else:
            print("\n📭 No transcriptions captured")
        
        # Cancel response task
        response_task.cancel()
        
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await transcriber.cleanup()
        print("👋 Test completed!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
