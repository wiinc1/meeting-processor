#!/usr/bin/env python3
"""
Simple script to add Otter API key to .env file.
Usage: python add_otter_api_key.py YOUR_API_KEY_HERE
"""

import sys
import os

def add_api_key_to_env(api_key):
    """Add API key to .env file."""
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
    
    print(f"✅ Added OTTER_API_KEY to .env file")
    return True

def test_api_key(api_key):
    """Test the API key."""
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
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python add_otter_api_key.py YOUR_API_KEY_HERE")
        print("Example: python add_otter_api_key.py otter_1234567890abcdef")
        sys.exit(1)
    
    api_key = sys.argv[1].strip()
    
    if not api_key:
        print("❌ Please provide a valid API key")
        sys.exit(1)
    
    print(f"Adding API key: {api_key[:10]}...")
    
    # Add to .env file
    if add_api_key_to_env(api_key):
        print("✅ API key added to .env file")
        
        # Test the API key
        print("Testing API key...")
        if test_api_key(api_key):
            print("🎉 Otter MCP authentication setup complete!")
            print("You can now use the MCP tools to access your Otter.ai meetings.")
        else:
            print("❌ API key test failed. Please check your key and try again.")
    else:
        print("❌ Failed to add API key to .env file")

if __name__ == "__main__":
    main()

