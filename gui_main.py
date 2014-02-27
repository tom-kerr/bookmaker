#!/usr/bin/env python3
""" Launches a GUI session
"""
from gui.main import BookmakerGUI

def init_session():
    i = BookmakerGUI()
    
if __name__ == "__main__":
    init_session()
else:
    os.exit(1)
    
    
