# AHD Alert Bot — Discord App

A Discord bot that lets any player subscribe to A House Divided alerts and receive DMs when in-game events happen.

## Commands

| Command | Description | Example |
|---|---|---|
| `/subscribe` | Add an alert | `/subscribe alert_type:elections country:US` |
| `/unsubscribe` | Remove an alert | `/unsubscribe alert_type:elections` |
| `/myalerts` | See your subscriptions | `/myalerts` |
| `/ahd` | Bot info & help | `/ahd` |

## Alert types

| Type | Description | Filters |
|---|---|---|
| `elections` | Election opens, closes, or goes upcoming | `country` |
| `legislation` | Bills pass or fail | `country`, `keyword` (bill title) |
| `market` | Stock price moves ≥5% | `keyword` (corporation name) |
| `news` | New news posts | `country`, `keyword` |
| `characters` | Favorability or PI changes | `keyword` (character name) |

## Examples

```
/subscribe alert_type:elections country:US
/subscribe alert_type:legislation country:GB keyword:healthcare
/subscribe alert_type:market keyword:Acme Corp
/subscribe alert_type:news keyword:scandal
/subscribe alert_type:characters keyword:John Smith
```

---

## Setup

### 1. Create a Discord application

1. Go to https://discord.com/developers/applications
2. Click **New Application** → give it a name
3. Go to **Bot** → **Add Bot**
4. Under **Privileged Gateway Intents**, enable nothing (bot doesn't need them)
5. Copy the **Token** — this is your `DISCORD_BOT_TOKEN`
6. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot permissions: `Send Messages` (that's all it needs)
   - Copy the generated URL and open it to add the bot to your server

### 2. Get your AHD API key

Go to Settings → API Keys in A House Divided and create a public key.

### 3. Run with Docker (recommended)

```bash
# Clone the repo
git clone https://github.com/yourname/ahd-alert-bot
cd ahd-alert-bot

# Set environment variables
export DISCORD_BOT_TOKEN="your_bot_token_here"
export AHD_API_KEY="ahd_pub_your_key_here"

# Build and run
docker build -t ahd-bot .
docker run -d \
  --name ahd-bot \
  --restart unless-stopped \
  -e DISCORD_BOT_TOKEN="$DISCORD_BOT_TOKEN" \
  -e AHD_API_KEY="$AHD_API_KEY" \
  -v $(pwd)/data:/app/data \
  ahd-bot
```

### 4. Run directly with Python

```bash
pip install -r requirements.txt

export DISCORD_BOT_TOKEN="your_bot_token_here"
export AHD_API_KEY="ahd_pub_your_key_here"

python src/bot.py
```

---

## Hosting

| Option | Cost | Notes |
|---|---|---|
| **Railway** | Free tier available | Easiest — connect GitHub repo, set env vars, done |
| **Fly.io** | Free tier available | Docker-native, great for small bots |
| **DigitalOcean** | ~$4/month | Simple Droplet + Docker |
| **Raspberry Pi** | One-time hardware | Great if you have one sitting around |
| **VPS (Hetzner)** | ~€3/month | Cheapest paid option |

### Railway (easiest)

1. Push this repo to GitHub
2. Go to railway.app → New Project → Deploy from GitHub repo
3. Add environment variables: `DISCORD_BOT_TOKEN`, `AHD_API_KEY`
4. Railway auto-detects the Dockerfile and deploys

---

## Architecture

```
Discord User
    │
    │  /subscribe elections country:US
    ▼
Discord Bot (discord.py)
    │  saves to SQLite
    ▼
subscriptions.db
    ▲
    │  reads subscribers
Background Poller (runs every 60s)
    │
    │  polls
    ▼
AHD Public API
    │
    │  new event found → match subscribers → DM each user
    ▼
Discord DM ✉️
```

State is stored in `data/subscriptions.db` (SQLite). Mount this as a volume if using Docker so it persists across restarts.
