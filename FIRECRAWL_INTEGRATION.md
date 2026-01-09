# Firecrawl Integration for Otter.ai Scraping

This document explains how to use Firecrawl's open source library to enhance Otter.ai transcript scraping in your project.

## Overview

Firecrawl provides a powerful alternative to Selenium-based scraping with several advantages:

- **Better JavaScript handling**: More reliable for dynamic content
- **Simplified authentication**: Better session management
- **Structured data extraction**: Built-in markdown/JSON output
- **Rate limiting and retry logic**: Built-in robustness
- **No browser dependencies**: Lighter weight than Selenium

## Setup

### 1. Install Firecrawl

The Firecrawl Python SDK has been added to your `requirements.txt`:

```bash
pip install firecrawl-py==4.3.6
```

### 2. Get Firecrawl API Key

1. Sign up at [Firecrawl.dev](https://www.firecrawl.dev/)
2. Get your API key from the dashboard
3. Add it to your `.env` file:

```bash
FIRECRAWL_API_KEY=fc-your_api_key_here
```

### 3. Environment Variables

Add these to your `.env` file for Firecrawl authentication:

```bash
# Firecrawl API Key
FIRECRAWL_API_KEY=fc-your_api_key_here

# Otter.ai credentials (for authentication)
OTTER_USERNAME=your_otter_username
OTTER_PASSWORD=your_otter_password
```

## Usage

### Command Line Options

Your main script now supports multiple scraper backends:

```bash
# Use Firecrawl (recommended)
python main.py --scraper firecrawl --run-once

# Use Selenium (existing)
python main.py --scraper selenium --run-once

# Auto-detect best available backend
python main.py --scraper auto --run-once

# Use direct API (existing)
python main.py --scraper api --run-once
```

### Available Scraper Backends

1. **`firecrawl`**: Uses Firecrawl for enhanced web scraping
2. **`selenium`**: Uses Selenium WebDriver (existing functionality)
3. **`api`**: Uses direct Otter.ai API calls (existing functionality)
4. **`auto`**: Automatically selects the best available backend

### Firecrawl-Specific Options

When using Firecrawl, you can also use the standalone Firecrawl scraper:

```bash
# Standalone Firecrawl scraper
python otter_firecrawl.py --limit 10 --output data

# With specific API key
python otter_firecrawl.py --api-key fc-your_key_here --limit 5
```

## Architecture

### New Files Added

1. **`otter_firecrawl.py`**: Firecrawl-based scraper implementation
2. **`otter_scraper_factory.py`**: Factory for creating different scraper types
3. **`FIRECRAWL_INTEGRATION.md`**: This documentation

### Updated Files

1. **`main.py`**: Added support for multiple scraper backends
2. **`requirements.txt`**: Added Firecrawl dependency

## How It Works

### Firecrawl Scraper (`otter_firecrawl.py`)

The Firecrawl scraper provides these key methods:

- `authenticate()`: Handle Otter.ai authentication
- `get_all_meetings()`: Extract meeting list from Otter.ai
- `get_meeting_details()`: Get detailed transcript, summary, action items
- `export_meetings_data()`: Save data to files

### Unified Interface (`otter_scraper_factory.py`)

The factory pattern allows you to use any scraper backend with the same interface:

```python
from otter_scraper_factory import UnifiedOtterScraper

# Create scraper
scraper = UnifiedOtterScraper(backend='firecrawl')

# Use unified interface
scraper.setup()
scraper.authenticate()
meetings = scraper.get_all_meetings(limit=10)
```

## Benefits of Firecrawl

### vs Selenium

| Feature | Firecrawl | Selenium |
|---------|-----------|----------|
| JavaScript handling | ✅ Better | ⚠️ Good |
| Session management | ✅ Built-in | ❌ Manual |
| Rate limiting | ✅ Built-in | ❌ Manual |
| Browser dependencies | ❌ None | ✅ Required |
| Structured output | ✅ JSON/Markdown | ❌ HTML parsing |
| Authentication | ✅ Simplified | ⚠️ Complex |

### vs Direct API

| Feature | Firecrawl | Direct API |
|---------|-----------|------------|
| Dynamic content | ✅ Handles JS | ❌ Static only |
| Authentication | ✅ Session-based | ⚠️ Token-based |
| Rate limiting | ✅ Built-in | ❌ Manual |
| Error handling | ✅ Robust | ⚠️ Basic |

## Configuration

### Auto-Detection Logic

The system automatically chooses the best backend:

1. **Firecrawl**: If `FIRECRAWL_API_KEY` is set and valid
2. **Selenium**: If Firecrawl unavailable but Selenium installed
3. **API**: If neither available but API credentials exist

### Environment Variables

```bash
# Firecrawl (preferred)
FIRECRAWL_API_KEY=fc-your_key_here

# Otter.ai credentials
OTTER_USERNAME=your_username
OTTER_PASSWORD=your_password

# Notion integration
NOTION_API_KEY=your_notion_key
```

## Troubleshooting

### Common Issues

1. **"Firecrawl API key not found"**
   - Ensure `FIRECRAWL_API_KEY` is set in `.env`
   - Verify the API key is valid

2. **"Authentication failed"**
   - Check Otter.ai credentials in `.env`
   - Verify Otter.ai account access

3. **"No meetings found"**
   - Check if you have meetings in your Otter.ai account
   - Verify authentication was successful

### Debug Mode

Enable debug logging to see detailed information:

```bash
python main.py --scraper firecrawl --debug --run-once
```

### Fallback Options

If Firecrawl fails, the system can fall back to other methods:

```bash
# Try Firecrawl first, fallback to Selenium
python main.py --scraper auto --run-once

# Force Selenium if Firecrawl has issues
python main.py --scraper selenium --run-once
```

## Performance Comparison

### Speed
- **Firecrawl**: ~2-3x faster than Selenium
- **API**: Fastest (when available)
- **Selenium**: Slowest (browser overhead)

### Reliability
- **Firecrawl**: High (built-in retry logic)
- **API**: High (when working)
- **Selenium**: Medium (browser stability issues)

### Resource Usage
- **Firecrawl**: Low (no browser)
- **API**: Lowest
- **Selenium**: High (browser memory)

## Best Practices

1. **Use Firecrawl for production**: Most reliable and efficient
2. **Keep Selenium as backup**: For edge cases or debugging
3. **Monitor API limits**: Firecrawl has usage limits
4. **Test authentication**: Ensure credentials work before scheduling
5. **Use auto-detection**: Let the system choose the best backend

## Examples

### Basic Usage

```bash
# Simple Firecrawl scraping
python main.py --scraper firecrawl --run-once

# With debug output
python main.py --scraper firecrawl --debug --run-once

# Limit number of meetings
python main.py --scraper firecrawl --run-once --max-meetings 5
```

### Advanced Usage

```bash
# Use specific browser for Selenium fallback
python main.py --scraper auto --browser chrome --headless

# Use Chrome profile for persistent sessions
python main.py --scraper selenium --profile-dir /path/to/chrome/profile
```

### Programmatic Usage

```python
from otter_scraper_factory import UnifiedOtterScraper

# Create Firecrawl scraper
scraper = UnifiedOtterScraper(backend='firecrawl')
scraper.setup()

# Authenticate
if scraper.authenticate():
    # Get meetings
    meetings = scraper.get_all_meetings(limit=10)
    
    # Process each meeting
    for meeting in meetings:
        details = scraper.get_meeting_details(meeting['id'])
        print(f"Meeting: {meeting['title']}")
        print(f"Transcript length: {len(details.get('transcript', ''))}")

# Clean up
scraper.close()
```

## Migration from Selenium

If you're currently using Selenium, migration is simple:

1. **Add Firecrawl API key** to your `.env` file
2. **Change scraper argument**: `--scraper firecrawl`
3. **Test the integration**: Run with `--debug` flag
4. **Monitor performance**: Check logs for any issues

The unified interface ensures your existing code continues to work with minimal changes.

## Support

For issues with Firecrawl integration:

1. Check the logs in `logs/` directory
2. Enable debug mode with `--debug` flag
3. Verify API key and credentials
4. Test with `--scraper auto` for automatic fallback

The system is designed to be robust and will automatically fall back to other methods if Firecrawl fails.



