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
    NSPasteboard, NSStringPboardType, NSEvent, NSEventMask,
    NSKeyDownMask, NSAlternateKeyMask
)

# Import Quartz for event tapping (to block default behavior)
try:
    from Quartz import (
        CGEventTapCreate, CGEventTapEnable, CGEventGetIntegerValueField,
        CGEventField, kCGEventTapOptionDefault, kCGSessionEventTap,
        kCGEventKeyDown, kCGEventFlagMaskAlternate, kCGHeadInsertEventTap,
        CGEventMask, CGEventTapIsEnabled
    )
    from CoreFoundation import (
        CFRunLoopGetCurrent, CFRunLoopAddSource, CFRunLoopGetMain,
        kCFRunLoopCommonModes, CFMachPortCreateRunLoopSource
    )
    HAS_EVENT_TAP = True
except ImportError:
    HAS_EVENT_TAP = False
from PyObjCTools import AppHelper
from dotenv import load_dotenv

# We'll use a simple polling approach for hotkeys
import time

# Import our transcription modules
from realtime_transcription_test import RealtimeTranscriber
from whisper_transcription import translate_audio

# Load environment variables
load_dotenv()

class LexiconicApp:
    # Key codes for arrow keys
    KEY_LEFT_ARROW = 123
    KEY_RIGHT_ARROW = 124
    
    def __init__(self):
        self.app = NSApplication.sharedApplication()
        self.setup_menu_bar()
        
        # Transcription state
        self.realtime_transcriber = None
        self.is_realtime_active = False
        self.transcription_thread = None
        
        # Hotkey monitoring
        self.hotkey_thread = None
        self.hotkey_active = True
        
        # Auto-paste functionality
        self.auto_paste_enabled = True
        self.last_pasted_length = 0
        
        # LLM post-processing
        self.post_process_enabled = False
        
        # Get API key
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            self.show_alert("API Key Missing", 
                          "Please set your OPENAI_API_KEY in the .env file")
            
        # Initialize event_tap attribute
        self.event_tap = None
        
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
        
        self.start_realtime_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "▶ Start Live Transcription (⌥←)", "toggleRealtimeTranscription:", "")
        self.start_realtime_item.setTarget_(self)
        self.menu.addItem_(self.start_realtime_item)
        
        self.stop_realtime_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "⏹ Stop Live Transcription (⌥←)", "toggleRealtimeTranscription:", "")
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
        
        # Auto-paste toggle
        self.auto_paste_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "⌨️ Enable Auto-Paste", "toggleAutoPaste:", "p")
        self.auto_paste_item.setTarget_(self)
        self.menu.addItem_(self.auto_paste_item)
        
        # LLM post-processing toggle
        self.post_process_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "🧠 Enable LLM Cleanup", "togglePostProcessing:", "l")
        self.post_process_item.setTarget_(self)
        self.menu.addItem_(self.post_process_item)
        
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
    
    def toggleRealtimeTranscription_(self, sender):
        """Toggle real-time transcription on/off"""
        if self.is_realtime_active:
            self.stopRealtimeTranscription_(sender)
        else:
            self.startRealtimeTranscription_(sender)
    
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
        
        # Reset auto-paste tracking for new session
        self.last_pasted_length = 0
        
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
        
        # Stop the transcriber with better error handling
        if self.realtime_transcriber:
            try:
                self.realtime_transcriber.stop_recording()
            except Exception as e:
                print(f"Warning: Error stopping transcriber: {e}")
            
        # Post-process transcription if enabled
        if self.post_process_enabled and self.last_transcription:
            threading.Thread(
                target=self.post_process_transcription,
                daemon=True
            ).start()
    
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
            # Clean up with better error handling
            self.is_realtime_active = False
            try:
                self.start_realtime_item.setEnabled_(True)
                self.stop_realtime_item.setEnabled_(False)
                self.status_item.setTitle_("🎤")
            except Exception as ui_error:
                print(f"Warning: UI cleanup error: {ui_error}")
    
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
                    latest_transcription = transcriptions[-1]
                    self.last_transcription = latest_transcription
                    
                    # Auto-paste if enabled
                    if self.auto_paste_enabled:
                        self.handle_auto_paste(latest_transcription)
            
            # Cancel response task
            response_task.cancel()
            
        except Exception as e:
            print(f"Error in async transcription: {e}")
        finally:
            try:
                if self.realtime_transcriber:
                    await self.realtime_transcriber.cleanup()
            except Exception as cleanup_error:
                print(f"Warning: Cleanup error: {cleanup_error}")
    
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
    
    def toggleAutoPaste_(self, sender):
        """Toggle auto-paste functionality"""
        self.auto_paste_enabled = not self.auto_paste_enabled
        
        if self.auto_paste_enabled:
            self.auto_paste_item.setTitle_("⌨️ Disable Auto-Paste")
            print("Auto-paste enabled - transcriptions will be typed automatically")
        else:
            self.auto_paste_item.setTitle_("⌨️ Enable Auto-Paste")
            print("Auto-paste disabled")
            
        # Reset paste tracking when toggling
        self.last_pasted_length = 0
        
        # Reset when starting new transcription
        if not self.is_realtime_active:
            self.last_pasted_length = 0
    
    def handle_auto_paste(self, transcription):
        """Handle auto-pasting of transcription without using clipboard"""
        try:
            # Only paste new content (incremental)
            if len(transcription) > self.last_pasted_length:
                new_content = transcription[self.last_pasted_length:]
                
                # Skip pasting if the new content is too short or just punctuation
                if len(new_content.strip()) < 2:
                    # Still update the last pasted length to avoid accumulating old content
                    self.last_pasted_length = len(transcription)
                    return
                    
                # Get the frontmost application to avoid pasting into terminal/IDE
                check_app_script = 'tell application "System Events" to get name of first application process whose frontmost is true'
                result = subprocess.run(['osascript', '-e', check_app_script], 
                                      capture_output=True, text=True, timeout=1)
                
                if result.returncode == 0:
                    frontmost_app = result.stdout.strip()
                    # Skip auto-paste for development tools and terminal
                    skip_apps = ['Terminal', 'iTerm', 'iTerm2', 'Windsurf', 'Visual Studio Code', 'Xcode', 'PyCharm']
                    if any(app.lower() in frontmost_app.lower() for app in skip_apps):
                        print(f"Skipping auto-paste for {frontmost_app}")
                        # Still update the last pasted length to avoid accumulating old content
                        self.last_pasted_length = len(transcription)
                        return
                
                # Use AppleScript to type the text without affecting clipboard
                # Better escaping for AppleScript
                escaped_text = new_content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                applescript = f'tell application "System Events" to keystroke "{escaped_text}"'
                
                result = subprocess.run(['osascript', '-e', applescript], 
                             capture_output=True, text=True, timeout=2)
                
                if result.returncode == 0:
                    # Only update last_pasted_length on successful paste
                    self.last_pasted_length = len(transcription)
                else:
                    print(f"Auto-paste failed: {result.stderr}")
                
        except Exception as e:
            print(f"Error in auto-paste: {e}")
            # On error, still update the last pasted length to avoid accumulating old content
            self.last_pasted_length = len(transcription)
    
    def togglePostProcessing_(self, sender):
        """Toggle LLM post-processing functionality"""
        self.post_process_enabled = not self.post_process_enabled
        
        if self.post_process_enabled:
            self.post_process_item.setTitle_("🧠 Disable LLM Cleanup")
            print("LLM post-processing enabled - transcriptions will be cleaned up after completion")
        else:
            self.post_process_item.setTitle_("🧠 Enable LLM Cleanup")
            print("LLM post-processing disabled")
    
    def post_process_transcription(self):
        """Post-process transcription using a low-cost LLM model"""
        try:
            print("🧠 Post-processing transcription with LLM...")
            
            # Use a low-cost model for cleanup
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            prompt = f"""Please clean up this transcription by:
1. Fixing capitalization errors
2. Adding proper punctuation
3. Correcting obvious word errors
4. Maintaining the original meaning and tone

Transcription to clean:
{self.last_transcription}

Cleaned version:"""
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Low-cost model
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that cleans up transcriptions. Return only the cleaned text, no explanations."}, 
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            cleaned_text = response.choices[0].message.content.strip()
            
            # Update the last transcription with cleaned version
            self.last_transcription = cleaned_text
            
            # Show the cleaned result on main thread using dispatch
            from Foundation import NSOperationQueue
            def show_result():
                self.show_transcription_result(cleaned_text, "LLM Cleaned Transcription")
            
            NSOperationQueue.mainQueue().addOperationWithBlock_(show_result)
            
            print(f"✅ Transcription cleaned: {cleaned_text[:50]}...")
            
        except Exception as e:
            print(f"Error in LLM post-processing: {e}")
            # Show error on main thread using dispatch
            from Foundation import NSOperationQueue
            def show_error():
                self.show_alert("LLM Processing Error", f"Failed to process transcription: {e}")
            
            NSOperationQueue.mainQueue().addOperationWithBlock_(show_error)

    def setup_global_hotkeys(self):
        """Setup global hotkeys using event tap to block default behavior"""
        if not HAS_EVENT_TAP:
            print("Warning: Quartz framework not available for event tapping")
            print("To enable full hotkey blocking, please install the Quartz framework:")
            print("pip install pyobjc-framework-Quartz")
            print("Falling back to monitor method (cannot block default behavior)")
            self.setup_fallback_hotkeys()
            return
            
        try:
            # Create event mask for key down events
            event_mask = CGEventMask(1 << kCGEventKeyDown)
            
            # Create event tap that can intercept and block events
            # Using kCGHeadInsertEventTap for highest priority to ensure blocking
            self.event_tap = CGEventTapCreate(
                kCGSessionEventTap,  # tap location
                kCGHeadInsertEventTap,  # placement - highest priority to ensure blocking
                kCGEventTapOptionListenOnly,  # options - listen only first to test
                event_mask,  # event mask
                self.event_tap_callback,  # callback
                None  # user info
            )
            
            if self.event_tap:
                # Create run loop source and add to main run loop
                run_loop_source = CFMachPortCreateRunLoopSource(None, self.event_tap, 0)
                # Ensure we're adding to the main run loop
                main_run_loop = CFRunLoopGetMain()
                CFRunLoopAddSource(main_run_loop, run_loop_source, kCFRunLoopCommonModes)
                
                # Enable the event tap
                CGEventTapEnable(self.event_tap, True)
                
                # Verify the event tap is enabled
                is_enabled = CGEventTapIsEnabled(self.event_tap)
                if is_enabled:
                    print(f"Global hotkeys registered: ⌥← (toggle start/stop)")
                    print("✅ Event tap enabled - default Option+Left behavior will be blocked")
                else:
                    print(f"Global hotkeys registered: ⌥← (toggle start/stop)")
                    print("⚠️  Event tap created but not enabled - falling back to monitor method")
                    print("To enable full hotkey blocking, please grant Accessibility permissions:")
                    print("1. Open System Preferences > Security & Privacy > Privacy")
                    print("2. Select Accessibility from the left sidebar")
                    print("3. Click the lock icon and enter your password")
                    print("4. Add this application (Python or your terminal) to the list")
                    print("5. Restart the application")
                    # Disable the event tap and fall back
                    CGEventTapEnable(self.event_tap, False)
                    self.event_tap = None
                    self.setup_fallback_hotkeys()
            else:
                print("Failed to create event tap - falling back to monitor")
                print("To enable full hotkey blocking, please grant Accessibility permissions:")
                print("1. Open System Preferences > Security & Privacy > Privacy")
                print("2. Select Accessibility from the left sidebar")
                print("3. Click the lock icon and enter your password")
                print("4. Add this application (Python or your terminal) to the list")
                print("5. Restart the application")
                self.setup_fallback_hotkeys()
                
        except Exception as e:
            print(f"Failed to setup event tap hotkeys: {e}")
            print("Falling back to monitor method")
            self.setup_fallback_hotkeys()
    
    def setup_fallback_hotkeys(self):
        """Fallback hotkey setup using NSEvent monitoring (can't block default behavior)"""
        try:
            # Add global monitor for key events
            NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
                NSKeyDownMask,
                self.handle_global_key_event
            )
            
            print("Fallback hotkeys registered: ⌥← (toggle start/stop)")
            print("Note: Default Option+Left behavior CANNOT be blocked without Accessibility permissions")
                
        except Exception as e:
            print(f"Failed to setup fallback hotkeys: {e}")
            print("Menu bar buttons will still work")
    
    def event_tap_callback(self, proxy, event_type, event, user_info):
        """Handle event tap callbacks - can block default behavior"""
        try:
            if event_type == kCGEventKeyDown:
                # Get key code and flags
                key_code = CGEventGetIntegerValueField(event, CGEventField.kCGKeyboardEventKeycode)
                flags = CGEventGetIntegerValueField(event, CGEventField.kCGEventFlagMask)
                
                # Check if Option key is pressed and it's left arrow
                if (flags & kCGEventFlagMaskAlternate) and key_code == self.KEY_LEFT_ARROW:
                    print(f"Hotkey triggered: Toggling transcription (key_code={key_code}, flags={flags})")
                    # Call method on main thread
                    from Foundation import NSOperationQueue
                    def toggle_transcription():
                        self.toggleRealtimeTranscription_(None)
                    NSOperationQueue.mainQueue().addOperationWithBlock_(toggle_transcription)
                    
                    # Return None to consume/block the event
                    print("Blocking default behavior for Option+Left Arrow")
                    return None
                        
        except Exception as e:
            print(f"Error in event tap callback: {e}")
        
        # Return the event unmodified for other key combinations
        return event
    
    def handle_global_key_event(self, event):
        """Fallback global key event handler (can't block default behavior)"""
        try:
            # Get key code and modifier flags
            key_code = event.keyCode()
            modifiers = event.modifierFlags()
            
            # Check if Option key is pressed
            if modifiers & NSAlternateKeyMask:
                if key_code == self.KEY_LEFT_ARROW:
                    print("Hotkey triggered: Toggling transcription (fallback)")
                    # Call method directly - we're already on the main thread
                    self.toggleRealtimeTranscription_(None)
                        
        except Exception as e:
            print(f"Error handling global key event: {e}")

    def applicationWillTerminate_(self, notification):
        """Cleanup when the application is about to terminate."""
        print("Lexiconic is shutting down...")
        
        # Stop hotkey monitoring
        self.hotkey_active = False
        
        # Disable event tap if it exists
        if hasattr(self, 'event_tap') and self.event_tap and HAS_EVENT_TAP:
            try:
                CGEventTapEnable(self.event_tap, False)
                # Event tap reference for blocking behavior
                self.event_tap = None
            except:
                pass
    
    def showAbout_(self, sender):
        """Show about dialog"""
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Lexiconic")
        alert.setInformativeText_(
            "A macOS menu bar app for audio transcription.\n\n"
            "Features:\n"
            "• Real-time live transcription\n"
            "• File-based audio transcription\n"
            "• Clipboard integration\n"
            "• Global hotkeys (⌥← start, ⌥→ stop)\n\n"
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
    
    def show_transcription_result(self, transcription, title_or_file_path=None):
        """Show transcription result in an alert"""
        if title_or_file_path:
            if title_or_file_path.startswith("/") or title_or_file_path.endswith((".mp3", ".wav", ".m4a", ".mp4")):
                # It's a file path
                filename = os.path.basename(title_or_file_path)
                title = f"Transcription: {filename}"
            else:
                # It's a custom title
                title = title_or_file_path
        else:
            title = "Transcription Complete"
        
        # Truncate very long transcriptions for display
        display_text = transcription
        if len(transcription) > 500:
            display_text = transcription[:500] + "...\n\n(Full text copied to clipboard)"
            # Auto-copy long transcriptions
            self.copy_to_clipboard(transcription)
        
        alert = NSAlert.alloc().init()
        alert.setMessageText_(title)
        alert.setInformativeText_(display_text)
        alert.addButtonWithTitle_("Copy to Clipboard")
        alert.addButtonWithTitle_("OK")
        
        response = alert.runModal()
        if response == 1000:  # First button (Copy)
            self.copy_to_clipboard(transcription)
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(text, NSStringPboardType)

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
