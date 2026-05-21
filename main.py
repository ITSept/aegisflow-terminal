#!/usr/bin/env python3
"""
AegisFlow Terminal - Phase 5: Textual UI
"""

import sys
import asyncio
from ui.dashboard import AegisFlowDashboard

if __name__ == "__main__":
    try:
        app = AegisFlowDashboard()
        app.run()
    except KeyboardInterrupt:
        print("\nExited by user.")