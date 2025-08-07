#!/usr/bin/env python3
"""
Lexiconic - Menu Bar Audio Transcription App

A macOS menu bar application that provides both real-time transcription
and file-based Whisper transcription capabilities.
"""

import os
import sys
import asyncio
import threading
import subprocess
from pathlib import Path

# Add src directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from AppKit import (
    NSApplication, NSStatusBar, NSVariableStatusItemLength, 
    NSMenu, NSMenuItem, NSAlert, NSOpenPanel, NSFileHandlingPanelOKButton,
    NSPasteboard, NSStringPboardType
)
from PyObjCTools import AppHelper
from dotenv import load_dotenv

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

# Import our transcription modules
from realtime_transcription_test import RealtimeTranscriber
from whisper_transcription import translate_audio

# Load environment variables
load_dotenv()

class LexiconicApp:
    # Define hotkeys
    HOTKEY_START = {'key': keyboard.Key.left, 'modifiers': {keyboard.Key.alt}}
    HOTKEY_STOP = {'key': keyboard.Key.alt_r, 'modifiers': {keyboard.Key.alt}}

    def get_hotkey_str(self, hotkey_def):
        # Helper to create human-readable hotkey strings
        mod_map = {keyboard.Key.alt: "⌥", keyboard.Key.cmd: "⌘", keyboard.Key.ctrl: "⌃", keyboard.Key.shift: "⇧"}
        mods = "".join([mod_map.get(mod, "") for mod in hotkey_def['modifiers']])
        key_name = hotkey_def['key'].char if hasattr(hotkey_def['key'], 'char') else hotkey_def['key'].name
        return f"{mods}{key_name.upper()}"

    def __init__(self):
        self.app = NSApplication.sharedApplication()
        self.setup_menu_bar()
        
        # Transcription state
        self.realtime_transcriber = None
        self.is_realtime_active = False
        self.transcription_thread = None
        self.hotkey_manager = None
        
        # Get API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            self.show_alert("API Key Missing", 
                          "Please set your OPENAI_API_KEY in the .env file")
            
        # Setup global hotkeys
        self.setup_global_hotkeys()

        # Set the app delegate to self to handle lifecycle events
        self.app.setDelegate_(self)
    
    def setup_menu_bar(self):
        """Setup the menu bar interface"""
        statusbar = NSStatusBar.systemStatusBar()
        self.status_item = statusbar.statusItemWithLength_(NSVariableStatusItemLength)
        self.status_item.setTitle_("🎤")  # Microphone icon
        
        # Create menu
        self.menu = NSMenu.alloc().init()
        
        # Real-time transcription section
        realtime_header = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Real-time Transcription", None, "")
        realtime_header.setEnabled_(False)
        self.menu.addItem_(realtime_header)
        
        start_hotkey_str = self.get_hotkey_str(self.HOTKEY_START)
        self.start_realtime_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"▶ Start Live Transcription ({start_hotkey_str})", "startRealtimeTranscription:", "")
        self.start_realtime_item.setTarget_(self)
        self.menu.addItem_(self.start_realtime_item)
        
        stop_hotkey_str = self.get_hotkey_str(self.HOTKEY_STOP)
        self.stop_realtime_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"⏹ Stop Live Transcription ({stop_hotkey_str})", "stopRealtimeTranscription:", "")
        self.stop_realtime_item.setTarget_(self)
        self.stop_realtime_item.setEnabled_(False)
        self.menu.addItem_(self.stop_realtime_item)
        
        # Separator
        self.menu.addItem_(NSMenuItem.separatorItem())
        
        # File transcription section
        file_header = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "File Transcription", None, "")
        file_header.setEnabled_(False)
        self.menu.addItem_(file_header)
        
        transcribe_file_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "📁 Transcribe Audio File...", "transcribeFile:", "t")
        transcribe_file_item.setTarget_(self)
        self.menu.addItem_(transcribe_file_item)
        
        # Separator
        self.menu.addItem_(NSMenuItem.separatorItem())
        
        # Utility items
        copy_transcriptions_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "📋 Copy Last Transcription", "copyLastTranscription:", "c")
        copy_transcriptions_item.setTarget_(self)
        self.menu.addItem_(copy_transcriptions_item)
        
        # Separator
        self.menu.addItem_(NSMenuItem.separatorItem())
        
        # App controls
        about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "About Lexiconic", "showAbout:", "")
        about_item.setTarget_(self)
        self.menu.addItem_(about_item)
        
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", "terminate:", "q")
        quit_item.setTarget_(self.app)
        self.menu.addItem_(quit_item)
        
        self.status_item.setMenu_(self.menu)
        
        # Store last transcription for copying
        self.last_transcription = ""
    
    def startRealtimeTranscription_(self, sender):
        """Start real-time transcription"""
        if not self.api_key:
            self.show_alert("API Key Missing", 
                          "Please set your OPENAI_API_KEY in the .env file")
            return
        
        if self.is_realtime_active:
            return
        
        print("Starting real-time transcription...")
        self.is_realtime_active = True
        
        # Update menu items
        self.start_realtime_item.setEnabled_(False)
        self.stop_realtime_item.setEnabled_(True)
        self.status_item.setTitle_("🔴")  # Red dot to indicate recording
        
        # Start transcription in a separate thread
        self.transcription_thread = threading.Thread(
            target=self.run_realtime_transcription,
            daemon=True
        )
        self.transcription_thread.start()
    
    def stopRealtimeTranscription_(self, sender):
        """Stop real-time transcription"""
        if not self.is_realtime_active:
            return
        
        print("Stopping real-time transcription...")
        self.is_realtime_active = False
        
        # Update menu items
        self.start_realtime_item.setEnabled_(True)
        self.stop_realtime_item.setEnabled_(False)
        self.status_item.setTitle_("🎤")  # Back to microphone
        
        # Stop the transcriber
        if self.realtime_transcriber:
            self.realtime_transcriber.stop_recording()
    
    def run_realtime_transcription(self):
        """Run real-time transcription in async context"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the transcription
            loop.run_until_complete(self.async_realtime_transcription())
        except Exception as e:
            print(f"Error in real-time transcription: {e}")
        finally:
            # Clean up
            self.is_realtime_active = False
            self.start_realtime_item.setEnabled_(True)
            self.stop_realtime_item.setEnabled_(False)
            self.status_item.setTitle_("🎤")
    
    async def async_realtime_transcription(self):
        """Async real-time transcription logic"""
        self.realtime_transcriber = RealtimeTranscriber(self.api_key)
        
        try:
            await self.realtime_transcriber.connect()
            self.realtime_transcriber.setup_audio()
            
            # Start listening for responses in background
            response_task = asyncio.create_task(
                self.realtime_transcriber.listen_for_responses()
            )
            
            # Start recording
            await self.realtime_transcriber.start_recording()
            
            # Keep running while active
            while self.is_realtime_active:
                await asyncio.sleep(0.1)
                
                # Check for new transcriptions and store the latest
                transcriptions = self.realtime_transcriber.get_transcriptions()
                if transcriptions:
                    self.last_transcription = transcriptions[-1]
            
            # Cancel response task
            response_task.cancel()
            
        except Exception as e:
            print(f"Error in async transcription: {e}")
        finally:
            await self.realtime_transcriber.cleanup()
    
    def transcribeFile_(self, sender):
        """Open file dialog and transcribe selected audio file"""
        if not self.api_key:
            self.show_alert("API Key Missing", 
                          "Please set your OPENAI_API_KEY in the .env file")
            return
        
        # Create file open dialog
        panel = NSOpenPanel.openPanel()
        panel.setTitle_("Select Audio File to Transcribe")
        panel.setPrompt_("Transcribe")
        panel.setAllowedFileTypes_([
            "m4a", "mp3", "mp4", "mpeg", "mpga", "wav", "webm"
        ])
        
        # Show dialog
        if panel.runModal() == NSFileHandlingPanelOKButton:
            file_url = panel.URL()
            file_path = file_url.path()
            
            print(f"Transcribing file: {file_path}")
            
            # Show progress
            self.status_item.setTitle_("⏳")
            
            # Run transcription in background thread
            threading.Thread(
                target=self.transcribe_file_background,
                args=(file_path,),
                daemon=True
            ).start()
    
    def transcribe_file_background(self, file_path):
        """Transcribe file in background thread"""
        try:
            # Use a generic prompt for file transcription
            prompt = "This is an audio recording that needs to be transcribed accurately."
            
            # Transcribe the file
            result = translate_audio(file_path, prompt)
            
            # Store result
            self.last_transcription = result
            
            # Show result
            self.show_transcription_result(result, file_path)
            
        except Exception as e:
            error_msg = f"Error transcribing file: {e}"
            print(error_msg)
            self.show_alert("Transcription Error", error_msg)
        finally:
            # Reset status
            self.status_item.setTitle_("🎤")
    
    def copyLastTranscription_(self, sender):
        """Copy the last transcription to clipboard"""
        if not self.last_transcription:
            self.show_alert("No Transcription", 
                          "No transcription available to copy.")
            return
        
        self.copy_to_clipboard(self.last_transcription)
        print(f"Copied to clipboard: {self.last_transcription[:50]}...")
        
        # Briefly change icon to indicate success
        self.status_item.setTitle_("✅")
        threading.Timer(1.0, lambda: self.status_item.setTitle_("🎤")).start()

    def setup_global_hotkeys(self):
        """Setup global hotkeys for transcription control"""
        if not HAS_PYNPUT:
            print("Warning: pynput not available - global hotkeys disabled")
            return
            
        try:
            def on_start_hotkey():
                if not self.is_realtime_active:
                    self.startRealtimeTranscription_(None)

            def on_stop_hotkey():
                if self.is_realtime_active:
                    self.stopRealtimeTranscription_(None)
            
            # Register hotkeys
            start_combo = "+".join([f"<{mod.name}>" for mod in self.HOTKEY_START['modifiers']] + [f"<{self.HOTKEY_START['key'].name}>"])
            stop_combo = "+".join([f"<{mod.name}>" for mod in self.HOTKEY_STOP['modifiers']] + [f"<{self.HOTKEY_STOP['key'].name}>"])

            self.hotkey_manager = keyboard.GlobalHotKeys({
                start_combo: on_start_hotkey,
                stop_combo: on_stop_hotkey
            })
            
            # Start hotkey listener in background thread
            # Start hotkey listener in background thread
            def run_listener():
                with self.hotkey_manager as listener:
                    listener.join()

            hotkey_thread = threading.Thread(target=run_listener, daemon=True)
            hotkey_thread.start()
            
            print(f"Global hotkeys registered: {self.get_hotkey_str(self.HOTKEY_START)} (start), {self.get_hotkey_str(self.HOTKEY_STOP)} (stop)")
            
        except Exception as e:
            print(f"Failed to setup global hotkeys: {e}")

    def applicationWillTerminate_(self, notification):
        """Cleanup when the application is about to terminate."""
        print("Lexiconic is shutting down...")
        if self.hotkey_manager:
            self.hotkey_manager.stop()
    
    def showAbout_(self, sender):
        """Show about dialog"""
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Lexiconic")
        alert.setInformativeText_(
            "A macOS menu bar app for audio transcription.\n\n"
            "Features:\n"
            "• Real-time live transcription\n"
            "• File-based audio transcription\n"
            "• Clipboard integration\n\n"
            "Powered by OpenAI Whisper"
        )
        alert.addButtonWithTitle_("OK")
        alert.runModal()
    
    def show_alert(self, title, message):
        """Show an alert dialog"""
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        alert.runModal()
    
    def show_transcription_result(self, transcription, file_path=None):
        """Show transcription result in an alert"""
        title = "Transcription Complete"
        if file_path:
            filename = os.path.basename(file_path)
            title = f"Transcription: {filename}"
        
        # Truncate very long transcriptions for display
        display_text = transcription
        if len(transcription) > 500:
            display_text = transcription[:500] + "...\n\n(Full text copied to clipboard)"
            # Auto-copy long transcriptions
            pasteboard = NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            pasteboard.setString_forType_(transcription, NSStringPboardType)
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(display_text)
        alert.addButtonWithTitle_("Copy to Clipboard")
        alert.addButtonWithTitle_("OK")
        
        response = alert.runModal()
        if response == 1000:  # First button (Copy)
            pasteboard = NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            pasteboard.setString_forType_(transcription, NSStringPboardType)

def main():
    """Main entry point"""
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not found in environment variables")
        print("Please set your API key in the .env file")
    
    app = LexiconicApp()
    print("Lexiconic started. Check your menu bar!")
    AppHelper.runEventLoop()

if __name__ == "__main__":
    main()
