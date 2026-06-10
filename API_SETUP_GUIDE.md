# API Setup Guide

Use this guide to prepare the `.env` file for IDC.

## 1. Choose A Provider

Grok is the default provider. Kimi/Moonshot can also be configured and selected from the GUI or server upload page.

For Grok:

1. Open the xAI platform.
2. Create or sign in to your account.
3. Generate an API key.
4. Copy the key and keep it private.

For Kimi:

1. Open the Kimi/Moonshot platform.
2. Generate an API key.
3. Copy the key and keep it private.

## 2. Create the `.env` File

Copy `.env.example` to `.env` and update it with your real key.

Default Grok setup:

```env
GROK_API_KEY=your-grok-api-key-here
GROK_API_URL=https://api.x.ai/v1/chat/completions
GROK_MODEL_NAME=grok-4-1-fast-non-reasoning
IDC_API_PROVIDER=grok
```

Optional Kimi setup:

```env
KIMI_API_KEY=your-kimi-api-key-here
KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions
KIMI_MODEL_NAME=kimi-k2.5
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
