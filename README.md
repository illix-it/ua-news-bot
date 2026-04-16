README.md

# Smart News UA Bot

A Telegram bot that automatically turns RSS news into clean Telegram posts.

It can:
- fetch news from RSS feeds,
- rewrite posts with Gemini,
- publish text, single-image posts, image albums, and videos,
- brand images and videos with a logo and watermark text,
- resolve video both from RSS and from article pages,
- fall back safely when AI, media, or Telegram upload fails.

---

## Features

### Content
- RSS parsing
- URL-based deduplication
- AI rewrite with Gemini
- fallback formatter if AI fails
- channel CTA at the end of posts
- optional video source note, for example:
    - `🎥 Video: Suspilne`

### Media
- single image posting
- multi-image album posting
- video posting
- direct video URL support
- YouTube and embed support through `yt-dlp`
- branding for both images and videos

### Reliability
- AI fallback if Gemini is unavailable
- caption splitting for Telegram media posts
- fallback if Telegram rejects oversized video uploads
- safe handling of repeated failures to avoid infinite retry loops

---

## Current Media Priority

The bot currently uses this priority:

1. if there are **2 or more images** → send an **album**
2. if there is **1 image** → send a **photo post**
3. if there are no images but video is available → send a **video post**
4. if there is no usable media → send a **text-only post**

In other words:

**photo > video**

If an article page contains both a photo and an embedded YouTube video, the bot will choose the photo.

---

## Project Structure

```text
src/ua_news_bot/
  ai/
  media/
  sources/
  aggregator.py
  config.py
  dedup_sqlite.py
  formatter.py
  main.py
  models.py
  telegram_client.py

scripts/
tests/
data/


⸻

Requirements
	•	Python 3.13+
	•	uv
	•	ffmpeg-full
	•	yt-dlp

⸻

Installation

1. Clone the project

git clone <your-repo-url>
cd ua-news-bot

2. Install Python dependencies

uv sync

3. Install FFmpeg and yt-dlp

macOS (Homebrew)

brew install ffmpeg-full
brew install yt-dlp

Verify installation:

yt-dlp --version
/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -version
/opt/homebrew/opt/ffmpeg-full/bin/ffprobe -version


⸻

Environment Setup

Copy the example file:

cp .env.example .env

Then fill in the required values:
	•	TELEGRAM_BOT_TOKEN
	•	TELEGRAM_CHAT_ID
	•	GEMINI_API_KEY or GEMINI_API_KEYS

⸻

Running the Bot

Dry run

uv run python -m ua_news_bot.main

If DRY_RUN=true, the bot does not publish to Telegram. Instead, it prints:
	•	the RSS-based post,
	•	the AI-generated post,
	•	media decisions,
	•	fallback information.

Real publishing

Set in .env:

DRY_RUN=false

Then run:

uv run python -m ua_news_bot.main


⸻

Recommended Local Testing Setup

For local channel testing:

DRY_RUN=false
MAX_POSTS_PER_RUN=3
RESET_DEDUP_ON_START=true
DEDUP_DB_PATH=data/seen_test.sqlite3
MEDIA_DEBUG=true

This makes testing easier because:
	•	old seen items are forgotten on each fresh start,
	•	the bot can send a few posts in one run,
	•	logs stay detailed.

After testing, a safer setup is:

RESET_DEDUP_ON_START=false
DEDUP_DB_PATH=data/seen.sqlite3
MEDIA_DEBUG=false
MAX_POSTS_PER_RUN=1


⸻

How AI Works

If AI_ENABLED=true, the bot uses Gemini to generate the final Telegram post.

AI receives:
	•	the article title,
	•	the RSS summary or article text passed into the enhancer.

If Gemini:
	•	returns poor output,
	•	fails,
	•	is unavailable,
	•	returns invalid or broken HTML,

the bot automatically falls back to the internal formatter and still publishes the news item.

⸻

How Media Works

Images
	•	images are taken from RSS when available,
	•	if multiple images exist, the bot can send an album,
	•	branding is applied to each image:
	•	channel logo,
	•	watermark text.

Video

The bot can use:
	•	direct video URLs,
	•	video discovered on the article page,
	•	YouTube or embeds resolved through yt-dlp.

After that:
	•	the video is branded,
	•	checked against the upload size threshold,
	•	uploaded to Telegram,
	•	or replaced by a fallback if needed.

⸻

Telegram Caption Fallback

Telegram media captions have size limits.

The bot handles that automatically:
	•	it tries to send the full caption with the media,
	•	if the text is too long:
	•	the media gets a safe shortened caption,
	•	the remaining text is sent as a separate message.

This works for:
	•	photo posts,
	•	albums,
	•	videos.

⸻

Oversized Video Protection

If Telegram returns:

Request Entity Too Large

the bot does not get stuck in a retry loop.

Instead it:
	•	falls back to photo, if photo is available,
	•	otherwise falls back to text,
	•	marks the item as processed after a successful fallback.

There is also a preventive size threshold controlled by:
	•	MAX_VIDEO_UPLOAD_MB

⸻

Supported Posting Types

The bot can publish:
	•	text-only posts
	•	single-image posts
	•	multi-image albums
	•	video posts

⸻

Debug and Utility Scripts

Test video pipeline

uv run python scripts/test_video_pipeline.py

Test album sending

uv run python scripts/test_album_send.py

Preview watermark sizes

uv run python scripts/test_watermark_preview.py
open /tmp/smart_news_watermark_preview

Debug RSS and media behavior

uv run python scripts/debug_rss_media.py

This is useful to inspect:
	•	RSS image URLs,
	•	RSS video URLs,
	•	resolver output,
	•	why the bot chose photo, album, video, or text.

⸻

Tests

Run tests:

uv run python -m unittest discover -s tests -p "test_*.py" -v

Run linting and formatting:

uv run ruff check . --fix
uv run ruff format .


⸻

Important Environment Variables

Telegram
	•	TELEGRAM_BOT_TOKEN
	•	TELEGRAM_CHAT_ID

General bot settings
	•	DRY_RUN
	•	MAX_POSTS_PER_RUN
	•	POLL_INTERVAL_SECONDS

Startup behavior
	•	INIT_SKIP_EXISTING
	•	INIT_POST_LATEST

Dedup
	•	DEDUP_DB_PATH
	•	RESET_DEDUP_ON_START
	•	DRY_RUN_MARK_SEEN

AI and Gemini
	•	AI_ENABLED
	•	AI_PROVIDER
	•	GEMINI_API_KEY
	•	GEMINI_API_KEYS
	•	GEMINI_MODEL
	•	CHANNEL_LANGUAGE

Channel CTA
	•	CHANNEL_CTA_TEXT
	•	CHANNEL_CTA_URL

FFmpeg and FFprobe
	•	FFMPEG_BIN
	•	FFPROBE_BIN

yt-dlp
	•	YTDLP_ENABLED
	•	YTDLP_BIN

Watermark and branding
	•	WATERMARK_TEXT
	•	WATERMARK_LOGO_PATH
	•	WATERMARK_MARGIN
	•	WATERMARK_IMAGE_LOGO_SCALE
	•	WATERMARK_IMAGE_TEXT_SCALE
	•	WATERMARK_VIDEO_LOGO_SCALE
	•	WATERMARK_VIDEO_TEXT_SCALE

Media behavior
	•	VIDEO_SOURCE_TEXT
	•	TELEGRAM_MEDIA_CAPTION_LIMIT
	•	TELEGRAM_MAX_MEDIA_IMAGES
	•	MAX_VIDEO_UPLOAD_MB
	•	MEDIA_DEBUG

⸻

Common Issues

1. Video is present on the website, but the bot sends a photo

That is expected with the current priority:

photo > video

If the bot sees a usable image, it chooses the image first.

2. Telegram returns Request Entity Too Large

This means the video upload is too large.

The bot should fall back automatically, but you can also reduce risk by:
	•	lowering video quality,
	•	lowering MAX_VIDEO_UPLOAD_MB,
	•	preferring photo fallback.

3. drawtext does not work in FFmpeg

You need ffmpeg-full, not the basic ffmpeg build.

4. The bot sends one post and then stops sending anything

Usually this is normal:
	•	the item was marked as seen,
	•	there are no newer RSS items yet.

For testing, use:

RESET_DEDUP_ON_START=true
DEDUP_DB_PATH=data/seen_test.sqlite3

5. Gemini sometimes fails with 503

This can happen during high load.
The bot should fall back automatically to the internal formatter.
