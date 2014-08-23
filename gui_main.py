#!/usr/bin/env python3
""" Launches a GUI session
"""
from gui.main import BookmakerGui

def init_session():
    i = BookmakerGui()
    
if __name__ == "__main__":
    init_session()
else:
    os.exit(1)
    
    
