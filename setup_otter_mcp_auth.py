#!/usr/bin/env python3
"""
Setup script for Otter MCP authentication.
This script helps configure the Otter.ai API key for MCP access.
"""

import os
import sys
from dotenv import load_dotenv

def check_current_auth():
    """Check current authentication setup."""
    load_dotenv()
    
    print("=== Current Otter.ai Authentication Status ===")
    print(f"Username: {os.getenv('OTTER_USERNAME', 'Not set')}")
    print(f"Password: {'*' * len(os.getenv('OTTER_PASSWORD', '')) if os.getenv('OTTER_PASSWORD') else 'Not set'}")
    print(f"API Key: {os.getenv('OTTER_API_KEY', 'Not set')}")
    print()

def generate_api_key_instructions():
    """Provide instructions for generating an API key."""
    print("=== How to Generate Otter.ai API Key ===")
    print("1. Log in to your Otter.ai account at https://otter.ai")
    print("2. Click on your profile icon (top right)")
    print("3. Select 'Apps' from the dropdown menu")
    print("4. Click 'Create a Zap' to initiate API key generation")
    print("5. Copy the generated API key (it won't be shown again)")
    print("6. Store it securely as it grants access to your Otter.ai data")
    print()

def update_env_file(api_key):
    """Update the .env file with the API key."""
    env_path = '.env'
    
    # Read current .env file
    env_lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Check if OTTER_API_KEY already exists
    api_key_exists = False
    for i, line in enumerate(env_lines):
        if line.startswith('OTTER_API_KEY='):
            env_lines[i] = f'OTTER_API_KEY={api_key}\n'
            api_key_exists = True
            break
    
    # Add API key if it doesn't exist
    if not api_key_exists:
        env_lines.append(f'OTTER_API_KEY={api_key}\n')
    
    # Write updated .env file
    with open(env_path, 'w') as f:
        f.writelines(env_lines)
    
    print(f"✅ Updated .env file with API key")

def test_api_key(api_key):
    """Test the API key by making a simple request."""
    try:
        import requests
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Test with a simple endpoint
        response = requests.get('https://otter.ai/api/public/me', headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✅ API key is valid and working!")
            return True
        else:
            print(f"❌ API key test failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API key: {e}")
        return False

def main():
    """Main setup function."""
    print("Otter MCP Authentication Setup")
    print("=" * 40)
    
    # Check current status
    check_current_auth()
    
    # Check if API key already exists
    load_dotenv()
    existing_api_key = os.getenv('OTTER_API_KEY')
    
    if existing_api_key and existing_api_key != 'test_key':
        print("Found existing API key. Testing...")
        if test_api_key(existing_api_key):
            print("✅ API key is already configured and working!")
            return
        else:
            print("❌ Existing API key is not working. Please generate a new one.")
    
    # Provide instructions for generating API key
    generate_api_key_instructions()
    
    # Ask user for API key
    api_key = input("Enter your Otter.ai API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("Skipping API key setup. You can run this script again later.")
        return
    
    # Update .env file
    update_env_file(api_key)
    
    # Test the API key
    print("\nTesting API key...")
    if test_api_key(api_key):
        print("\n🎉 Otter MCP authentication setup complete!")
        print("You can now use the MCP tools to access your Otter.ai meetings.")
    else:
        print("\n❌ API key test failed. Please check your key and try again.")
        print("You may need to regenerate the API key from your Otter.ai account.")

if __name__ == "__main__":
    main()

