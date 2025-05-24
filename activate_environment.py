#!/usr/bin/env python
"""
Environment Activation Helper Script
This script helps activate the conda environment across different platforms.
"""

import os
import platform
import subprocess
import sys

def main():
    """Main function to handle environment activation"""
    conda_path = r"e:\Github Repositories\codelens\.conda"
    
    print(f"Attempting to activate conda environment at: {conda_path}")
    print(f"Detected OS: {platform.system()}")
    
    if platform.system() == "Windows":
        activate_on_windows(conda_path)
    else:
        activate_on_unix(conda_path)

def activate_on_windows(conda_path):
    """Handle activation on Windows"""
    # Check if conda is available
    try:
        subprocess.run(["conda", "--version"], check=True, capture_output=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Conda not found. Please install Miniconda or Anaconda first.")
        return
    
    print("\nActivation options:")
    print("1. Try direct activation (using Command Prompt)")
    print("2. List available environments")
    print("3. Initialize conda for your shell")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        print("\nTo activate the environment, copy and run this command in your Command Prompt:")
        print(f"conda activate {conda_path}")
        
        print("\nOr run this batch file:")
        print(r"e:\Github Repositories\codelens\activate_conda.cmd")
        
    elif choice == "2":
        print("\nListing available conda environments:")
        subprocess.run(["conda", "env", "list"])
        
        env_name = input("\nEnter the environment name to activate (from list above): ")
        if env_name:
            print(f"\nTo activate, run: conda activate {env_name}")
            
    elif choice == "3":
        print("\nInitializing conda for Command Prompt:")
        print("Run this command in Command Prompt:")
        print("conda init cmd.exe")
        
        print("\nFor PowerShell:")
        print("conda init powershell")
    
    print("\nAfter activation, run the Flask application with:")
    print("flask run --debug")

def activate_on_unix(conda_path):
    """Handle activation on Unix-like systems"""
    escaped_path = conda_path.replace(" ", r"\ ")
    
    print("\nTo activate the environment, run:")
    print(f"conda activate {escaped_path}")
    
    print("\nOr using the shell script:")
    print(r"bash e:/Github\ Repositories/codelens/activate_conda.sh")
    
    print("\nIf that doesn't work, try listing environments:")
    print("conda env list")

if __name__ == "__main__":
    main()
