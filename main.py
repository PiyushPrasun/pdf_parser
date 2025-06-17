#!/usr/bin/env python3
"""
Main entry point for the PDF Parser application
"""

import os
import sys
import argparse
from src.cli import main as cli_main

def main():
    """
    Main entry point with web interface option
    """
    parser = argparse.ArgumentParser(description="PDF Parser - Extract and process PDF content")
    parser.add_argument("--web", action="store_true", help="Start the web interface")
    parser.add_argument("--port", type=int, default=5000, help="Port for web interface (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Host for web interface (default: 0.0.0.0)")
    
    # Add a rest parameter to catch all other arguments for the CLI
    parser.add_argument("rest", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    
    args, unknown = parser.parse_known_args()
    
    if args.web:
        # Import here to avoid import errors if dependencies aren't installed
        try:
            from app import app
            print(f"Starting web interface at http://{args.host}:{args.port}")
            app.run(debug=True, host=args.host, port=args.port)
        except ImportError as e:
            print(f"Error starting web interface: {str(e)}")
            print("Please ensure Flask is installed by running: pip install flask")
            sys.exit(1)
    else:
        # Pass the remaining arguments to the CLI
        sys.argv = [sys.argv[0]] + args.rest
        cli_main()

if __name__ == "__main__":
    main()
