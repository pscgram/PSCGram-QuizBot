# PSCGram QuizBot

Existing Telegram quiz bot built with `python-telegram-bot` 21.x, aiohttp and SQLAlchemy. The project uses a custom inline-button MCQ interface (not Telegram quiz polls).

## Implemented features

- Four-option inline MCQs, immediate answer validation, explanations and score summaries.
- Random, daily, practice, wrong-answer, bookmark, subject and topic modes.
- Timed sessions with persisted session state and resume support.
- Quiz creation with multiple manual questions through the admin conversation.
- PDF upload by an admin in a private chat and PDF ingestion from a configured channel.
- Selectable-text extraction and page-level OCR fallback for scanned/mixed PDFs.
- AI-generated MCQ drafts, duplicate checking on approval, and admin review.
- User history, score totals and daily/weekly/monthly/all-time leaderboards.
- Admin statistics and broadcast.
- Premium grant/revoke, expiry checks and Telegram Stars purchase.
- SQLite for local testing and PostgreSQL for production.

## Requirements

- Python 3.11 or newer.
- Telegram bot token from BotFather.
- PostgreSQL recommended for production.
- `OPENAI_API_KEY` for AI PDF question generation.
- For scanned PDFs: Tesseract OCR and Poppler system packages. The Render build command installs these packages.

## Local configuration

1. Copy `.env.example` to `.env`.
2. Set `BOT_TOKEN`.
3. Set `ADMIN_IDS` to comma-separated numeric Telegram user IDs.
4. Set `DATABASE_URL` (SQLite is the default for local development).
5. Set a long random `WEBHOOK_SECRET`.
6. Optionally set `OPENAI_API_KEY` and `PDF_CHANNEL_ID`.
7. Install Python dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

The application entry point is `python -m bot`. It runs the aiohttp webhook server and therefore also requires a public HTTPS hostname and `WEBHOOK_SECRET`; it is not a local polling runner.

## Render deployment

This repository is configured as a Render **Web Service**, because `bot/__main__.py` starts an aiohttp HTTP server and `bot/main.py` registers Telegram's webhook.

1. Push the complete project directory to the existing GitHub repository.
2. In Render, create or update a Web Service connected to that repository.
3. Use:
   - Build command: `apt-get update && apt-get install -y tesseract-ocr poppler-utils && pip install -r requirements.txt`
   - Start command: `python -m bot`
   - Health check path: `/health`
4. Configure these environment variables:

   | Variable | Required | Value |
   |---|---|---|
   | `BOT_TOKEN` | Yes | Telegram bot token from BotFather |
   | `ADMIN_IDS` | Yes | Comma-separated numeric Telegram user IDs |
   | `DATABASE_URL` | Yes for production | Render PostgreSQL internal connection URL |
   | `WEBHOOK_SECRET` | Yes | Random secret; Render Blueprint can generate it |
   | `OPENAI_API_KEY` | Only for AI imports | OpenAI API key |
   | `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini` |
   | `PDF_CHANNEL_ID` | No | Numeric channel ID, including leading minus sign |
   | `PREMIUM_PRICE_STARS` | No | Defaults to `500` |
   | `DEFAULT_QUIZ_QUESTIONS` | No | Defaults to `10` |
   | `DEFAULT_TEST_MINUTES` | No | Defaults to `15` |

   Render supplies `RENDER_EXTERNAL_HOSTNAME` and `PORT` automatically. Do not set either manually unless your hosting setup requires it.

5. Deploy and confirm that `/health` returns a JSON status response.
6. Start the bot in Telegram and verify the admin and user workflows.

**Important:** Use a managed PostgreSQL database for production. SQLite files on ephemeral hosting may be lost during redeploys or instance replacement. Do not expose the database publicly.

## Admin workflow

- `/admin` opens the dashboard.
- **Create quiz & add questions** starts manual quiz creation. Follow the prompts to add as many questions as needed.
- `/done` completes quiz creation.
- `/cancel` cancels the current conversation and clears its temporary state. A quiz with already-saved questions is retained but deactivated; an empty quiz is removed.
- Grant/revoke buttons request a user ID and (for grants) a positive number of days.
- Direct commands are also supported:
  - `/premium grant USER_ID DAYS`
  - `/premium revoke USER_ID`

Only IDs in `ADMIN_IDS` can use admin actions.

## PDF import

- Open Admin Dashboard → Upload PDF, then upload a PDF document in the same private chat.
- Files larger than 20 MB are rejected.
- The bot extracts selectable text and OCRs pages without selectable text. PDF page markers are retained in the extracted source.
- AI-generated questions are stored as drafts and require admin approval before publication.
- OCR requires the Tesseract executable and Poppler tools in addition to the Python packages.
- For channel ingestion, add the bot as a channel administrator and configure `PDF_CHANNEL_ID`. The bot processes new PDF posts; it cannot retrieve historical channel posts.

## Current limitations identified in the audit

These behaviours are not fully implemented and should not be treated as completed features:

- The **Previous Year** button does not yet filter questions by the `year` field; it currently draws from the general approved-question pool.
- **Full Mock Test** currently uses `DEFAULT_QUIZ_QUESTIONS` (10 by default), not a separately configured full-paper length.
- Timed exams check the deadline when the user interacts with the quiz; they do not automatically submit at the exact deadline while the user is idle, and there is no live countdown refresh.
- Question order can be randomized, but answer options are not shuffled.
- Admin-created quiz records are not yet exposed as a separate selectable quiz catalogue to users. Their questions can be reached through the general, subject and topic question pools.
- User progress currently consists mainly of recent attempt history; there is no detailed per-user analytics dashboard.
- Premium validation is currently applied to Full Mock Test. Other quiz modes are not premium-restricted.

## Telegram Stars

The premium invoice uses Telegram Stars (`XTR`) and an empty provider token as required for Stars invoices. Pre-checkout verifies invoice payload, currency and amount; successful-payment handling checks those details and avoids processing the same Telegram charge twice. The configured price is `PREMIUM_PRICE_STARS`.

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```

The automated tests cover fingerprint normalization, chunk boundaries, invalid PDF handling, selectable PDF extraction and premium grant/revoke persistence. Telegram handler execution, live Stars checkout, OpenAI generation, webhook delivery and real scanned-PDF OCR require external services or system binaries and must be smoke-tested after deployment.

## Security

- Never commit `.env`, bot tokens, database passwords or OpenAI keys.
- Keep `WEBHOOK_SECRET` private.
- Use HTTPS and a private PostgreSQL connection.
- Give the bot only the Telegram channel permissions it needs.
