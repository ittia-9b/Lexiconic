# Lexiconic Project Plan

## Tier 1: Core Application & OSD Setup

This tier focuses on building the fundamental application framework and getting the basic On-Screen Display (OSD) working.

- [ ] **Implement Overhead OSD**: Create the basic, real-time user feedback overlay that displays AI-generated context on the screen
- [ ] **Implement Hotkeys**: Create a system for binding custom actions to mouse and trackpad gestures
- [ ] **Implement Audio Cues**: For extra sensory UI feedback
- [ ] **Implement Gestures**: Create a system for binding custom actions to mouse and trackpad gestures
- [ ] **Real-time Transcription Test**: Establish a working pipeline to test real-time transcription performance
- [ ] **System Tray Application**: Research and implement a lightweight system tray/menu bar app to host the application
  - [ ] Investigate PyObjC for macOS integration
- [ ] **Auto-Clipboard Functionality**: Create a feature to automatically copy key information (like the project summary) to the clipboard

## Tier 2: Transcription Engine Improvements

This tier is about enhancing the quality and robustness of the core transcription process.

- [ ] **Implement VAD**: Integrate Voice Activity Detection (VAD) to more accurately capture speech and ignore silence
- [ ] **Develop Audio Quality Modes**: Create distinct processing modes for different microphone qualities
  - [ ] **Whisper Mode**: Optimized for quiet, clear speech
  - [ ] **"Bad Mic" Mode**: A mode with enhanced filtering for noisy environments or low-quality microphones
- [ ] **Custom Lexicon Presets**: Allow users to load presets for special vocabularies, like regional dialects or technical jargon

## Tier 3: AI Feature Expansion & Contextual Awareness

This tier expands on the core OSD by adding more intelligent, context-aware features based on our brainstorming.

- [ ] **Implement Stateful Memory**: Evolve the AI from stateless analysis to having a memory of the previous state
  - [ ] **Task Completion Tracking**: Automatically detect when a current_step is completed and trigger a temporary "Task Complete!" notification on the OSD
  - [ ] **Smarter Summaries**: Generate more dynamic project_summary updates that reference recently completed tasks
- [ ] **Problem/Blocker Detection**: Teach the AI to identify keywords indicating frustration or a problem, adding a "Current Blocker" field to the overlay
- [ ] **Automatic Component ID / Glossary**: Automatically identify and list specific components, tools, or key terms mentioned during the stream
- [ ] **Vocabulary & Phrasing Enhancements**:
  - [ ] **Vocab-Builder**: Analyze transcribed text and suggest more apt or precise vocabulary
  - [ ] **Quick Dictionary/Thesaurus**: Implement an in-app feature to look up words
- [ ] **Content & Usage Tracking**:
  - [ ] **Word Counter/Tracker**: Add analytics to track word usage over a session
  - [ ] **Quote Puller**: Implement a feature to automatically identify and pull interesting or notable quotes

## Tier 4: UI/UX & User Interaction

This tier focuses on improving the user experience and visual presentation.

- [ ] **Implement Mouse & Trackpad Gestures**: Create a system for binding custom actions to mouse and trackpad gestures
- [ ] **Add UI Animations**: Incorporate subtle animations, such as for the tray icon, to provide visual feedback

## Tier 5: Testing & Deployment

This tier covers the necessary steps for ensuring the application is robust and ready for use.

- [ ] **Develop a Comprehensive Test Set**: Create a standardized set of audio clips and scenarios to test for regressions and improvements
- [ ] **Setup Payments & Accounts**: If planning for distribution, set up payment processing and any required special accounts

## Tier 6: Advanced & Future Concepts

These are more speculative, long-term ideas to explore once the core application is mature.

- [ ] **Style Transfer**: Implement a feature to adapt the user's speech to a different writing style
  - [ ] Allow providing a sample text corpus for the AI to emulate
  - [ ] Investigate auto-detection of a desired style
- [ ] **OCR Transcription**: Explore adding vision capabilities to transcribe text from the screen or images