# Grok API Setup Guide

Use this guide to prepare the `.env` file for IDC.

## 1. Get an API Key

1. Open the xAI platform.
2. Create or sign in to your account.
3. Generate an API key.
4. Copy the key and keep it private.

## 2. Create the `.env` File

Copy `.env.example` to `.env` and update it with your real key:

```env
GROK_API_KEY=your-grok-api-key-here
GROK_API_URL=https://api.x.ai/v1/chat/completions
MODEL_NAME=grok-4-1-fast-non-reasoning
```

## 3. Where to Put the File

For source runs:

- place `.env` in the project root

For packaged `.exe` runs:

- place `.env` next to the executable

You can also set:

```text
IDC_ENV_FILE=C:\path\to\.env
```

## 4. Security Rules

- Never commit `.env`.
- Never paste a real API key into source files or markdown docs.
- Rotate the key if it is exposed.
