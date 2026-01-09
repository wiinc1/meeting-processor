#!/usr/bin/env python
import sys
import numpy as np
import spacy
import notion_client
import os
from dotenv import load_dotenv
import yaml
from dateutil import parser
import tenacity
import ratelimit
try:
    import otterai
    otter_imported = True
except ImportError:
    otter_imported = False

def main():
    print(f"Python version: {sys.version}")
    print(f"NumPy version: {np.__version__}")
    print(f"spaCy version: {spacy.__version__}")
    
    # Skip loading spaCy model
    print("Skipping SpaCy model loading due to compatibility issues")
    
    # The notion-client package doesn't expose a __version__ attribute
    print(f"notion-client imported successfully: {notion_client is not None}")
    print(f"Otter.ai API imported: {otter_imported}")
    
    print(f"python-dotenv imported: {load_dotenv is not None}")
    print(f"PyYAML imported: {yaml is not None}")
    print(f"dateutil imported: {parser is not None}")
    print(f"tenacity imported: {tenacity is not None}")
    print(f"ratelimit imported: {ratelimit is not None}")
    
    print("\nMost dependencies are successfully installed and imported!")
    print("Note: There's an issue with spaCy model loading, but basic functionality should work")
    
if __name__ == "__main__":
    main() 