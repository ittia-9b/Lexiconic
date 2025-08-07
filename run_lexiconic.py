#!/usr/bin/env python3
"""
Lexiconic Launcher

Simple launcher script for the Lexiconic menu bar app.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Change to project directory so relative imports work
os.chdir(Path(__file__).parent)

# Import and run the app
from whisper_broke_app import main

if __name__ == "__main__":
    main()
