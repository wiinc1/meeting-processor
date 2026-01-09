# Otter MCP Authentication Setup

## Current Status
- ✅ Username/Password credentials found in `.env`
- ❌ API Key not configured for MCP access
- ❌ MCP tools returning 403 Forbidden errors

## Problem
The Otter MCP (Model Context Protocol) requires an API key for authentication, but your current setup only has username/password credentials. The MCP tools are failing with 403 Forbidden because they can't authenticate.

## Solution: Generate and Configure API Key

### Step 1: Generate API Key from Otter.ai
1. **Log in to Otter.ai**: Go to https://otter.ai and sign in with your account
2. **Access Apps Section**: Click on your profile icon (top right corner)
3. **Select Apps**: Choose "Apps" from the dropdown menu
4. **Create API Key**: Click "Create a Zap" to generate an API key
5. **Copy the Key**: Save the API key immediately (it won't be shown again)

### Step 2: Add API Key to Environment
Add this line to your `.env` file:
```
OTTER_API_KEY=your_generated_api_key_here
```

### Step 3: Test MCP Connection
After adding the API key, test the MCP tools:
```python
# Test user info
mcp_otter_meeting_mcp_get_user_info()

# Test meeting search
mcp_otter_meeting_mcp_search(created_after="2025/10/16", created_before="2025/10/16")
```

## Alternative: Use Existing API Integration
If you prefer not to set up MCP authentication, you can continue using your existing Otter API integration in `otter_api.py` which already works with username/password authentication.

## Files Modified
- `.env` - Added OTTER_API_KEY
- `setup_otter_mcp_auth.py` - Created setup script
- `OTTER_MCP_SETUP.md` - This documentation

## Next Steps
1. Generate API key from Otter.ai account
2. Add API key to `.env` file
3. Test MCP connection
4. Query yesterday's meetings using MCP tools

