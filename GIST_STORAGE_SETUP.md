# Gist Storage Setup

This project uses GitHub Gist to store persistent data (recap history, tag rotation) outside the repository.

## Setup Instructions

### 1. Create a GitHub Gist (Automatic)

The first time you run the workflow, it will automatically create a new private Gist and print the Gist ID in the logs.

### 2. Add the GIST_ID Secret

After the first run:
1. Check the workflow logs for a message like: `🆕 Created new Gist! Add this as secret GIST_ID: abc123...`
2. Go to your repository Settings → Secrets and variables → Actions
3. Add a new secret named `GIST_ID` with the value from the logs

### 3. Token Permissions

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions. No additional token setup is required.

## What's Stored in the Gist

The Gist contains a JSON file (`portfolio_recap_data.json`) with:

```json
{
  "recap_history": [
    {
      "timestamp": "2026-01-02T10:00:00",
      "content": "First 1000 chars of recap..."
    }
  ],
  "used_tags": ["NVDA", "MSFT", "AMZN", "GOOG", "TSM"],
  "last_updated": "2026-01-02T10:00:00"
}
```

## Features

### Tag Rotation (Max 5 per post)
- Only 5 `$` tags are used per post
- Tags rotate automatically to ensure variety
- Prevents the same stocks from being tagged every time

### No $ Tags in Market Overview
- The "🌍 MARKET NEWS RECAP" section uses plain text for indices
- Only "💼 PORTFOLIO FOCUS" section uses `$` tags
- This ensures only valid eToro symbols are tagged

### Valid eToro Symbols Only
- Tags are limited to symbols in your portfolio that exist on eToro
- No more `$SP500` or `$EuroStoxx` (these don't exist on eToro)
