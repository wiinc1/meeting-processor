# Meeting Processing System

An automated system that processes meeting recordings from Notion, transcribes them using OpenAI Whisper, generates AI summaries and action items, and creates tasks in Asana.

## Overview

This system monitors a Notion database for new MP4 meeting recordings, processes them through AI transcription and summarization, and creates structured action items in Asana with email summaries for manual distribution.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Notion DB     │───▶│  Python Service  │───▶│   Asana Tasks   │
│  (MP4 Files)    │    │  (LaunchAgent)   │    │  (MCP Server)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Email Content   │
                       │  (Manual Send)   │
                       └──────────────────┘
```

## Features

- **Real-time Processing**: Monitors Notion database for new MP4 files
- **High-Accuracy Transcription**: Uses OpenAI Whisper for local processing
- **AI Summarization**: Generates meeting summaries and extracts action items
- **Asana Integration**: Creates tasks and subtasks with owner assignments
- **Email Generation**: Creates email content for manual distribution
- **Error Handling**: Creates Asana tasks for processing failures
- **macOS Integration**: Runs as LaunchAgent service

## Requirements

- Python 3.8+
- OpenAI Whisper
- Notion API access
- Asana MCP server
- macOS (for LaunchAgent)

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables
4. Set up LaunchAgent service
5. Configure Notion and Asana integrations

## Usage

The service runs automatically as a background process, monitoring your Notion database for new meeting recordings and processing them through the complete workflow.

## License

MIT
