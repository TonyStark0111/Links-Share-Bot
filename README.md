<p align="center">
  <img src="https://user-images.githubusercontent.com/73097560/115834477-dbab4500-a447-11eb-908a-139a6bdaec5c.gif" />
</p>



<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="https://telegra.ph/file/64d61b1f3933fbc18925e-4ba9274225dadacc17.jpg" width="90px" style="border-radius: 50%;" />
      </td>
      <td>
        <img src="https://readme-typing-svg.herokuapp.com?color=00BFFF&width=600&lines=Hey+There,+This+is+LinkShareBot+%F0%9F%A5%80+%E2%9D%97%EF%B8%8F" />
      </td>
    </tr>
  </table>
</div>



<p align="center">
  <img src="https://komarev.com/ghpvc/?username=LinkShareBot&style=flat-square" />
</p>

<h1 align="center">
  <img src="https://readme-typing-svg.herokuapp.com?color=FF69B4&width=500&lines=Welcome+to+LinkShareBot;Your+Ultimate+Telegram+Link+Sharing+Bot" />
</h1>

<p align="center">
  <a href="https://t.me/LinkShareBot">
    <img src="https://telegra.ph/file/86ee10d05289af41720e9-51ee4d6108f7131e02.jpg" width="600">
  </a>
</p>

<p align="center">
  <a href="https://t.me/LinkShareBot"><img src="https://img.shields.io/badge/Try%20Bot-@LinkShareBot-blue?style=for-the-badge&logo=telegram"/></a>
</p>

<p align="center">
  <a href="https://github.com/yourusername/LinkShareBot/stargazers"><img src="https://img.shields.io/github/stars/yourusername/LinkShareBot?style=flat-square"/></a>
  <a href="https://github.com/yourusername/LinkShareBot/network/members"><img src="https://img.shields.io/github/forks/yourusername/LinkShareBot?style=flat-square"/></a>
  <a href="https://github.com/yourusername/LinkShareBot/issues"><img src="https://img.shields.io/github/issues/yourusername/LinkShareBot?style=flat-square"/></a>
  <a href="https://github.com/yourusername/LinkShareBot/commits/main"><img src="https://img.shields.io/github/last-commit/yourusername/LinkShareBot?style=flat-square"/></a>
  <a href="https://github.com/yourusername/LinkShareBot/actions"><img src="https://img.shields.io/badge/CI-Status-grey?style=flat-square"/></a>
</p>

## 🌟 What is LinkShareBot?

**LinkShareBot** is a modern Telegram bot that allows you to share and manage unlimited Telegram channel links with automatic invite link generation and management. 

Powered by **Pyrogram**, it provides a seamless experience for users to join channels through secure, auto-expiring links. The bot includes advanced features like force subscription, bulk link generation, and request link management.

## 🚀 Features

<table>
<tr>
<td>
  <img src="https://telegra.ph/file/6478c4b60d9164beb39d2-14a358dcdc0a18b5a5.jpg" width="300" />
</td>
<td>

| 🌟 Feature                | 🔎 Description                              |
| ------------------------- | ------------------------------------------- |
| 📺 Unlimited Channels     | Add and manage unlimited Telegram channels  |
| 🔗 Auto Invite Links      | Generate secure, auto-expiring invite links |
| ⏱️ Auto Revoke            | Links automatically revoke after 5 minutes  |
| 📦 Bulk Generation        | Generate links for multiple channels at once |
| 📋 Pagination Support     | Navigate through large channel lists easily |
| 🔄 Request Links          | Support for join request links              |
| 🛡️ Force Subscription     | Require users to join specific channels     |
| 📊 Bot Statistics         | Monitor bot usage and user statistics       |

</td>
</tr>
</table>

## 🛠️ Commands

### Channel & Link Management (Owner/Admins)
- <b>`/addch <channel_id>`</b> — Add a channel to the bot (admin only)
- <b>`/delch <channel_id>`</b> — Remove a channel from the bot (admin only)
- <b>`/channels`</b> — Show all connected channels as buttons (paginated)
- <b>`/reqlink`</b> — Show all request links for channels (paginated)
- <b>`/links`</b> — Show all channel links as text (paginated)
- <b>`/bulklink <id1> <id2> ...`</b> — Generate links for multiple channel IDs at once
- <b>`/channels`</b> — Show all connected channel IDs and names (paginated, with next/prev buttons and auto-deleting "please wait..." status)

- <b>`/reqtime`</b> — Set the auto-approve request timer duration.
- <b>`/reqmode`</b> — Toggle auto request approval mode (ON/OFF).
- <b>`/approveon`</b> — Enable auto request approval for a specific channel.
- <b>`/approveoff`</b> — Disable auto request approval for a specific channel.
- <b>`/approveall`</b> — Approve all pending join requests in a channel using userbot (make sure to fill your session string in `approve.py`).

### Admin Commands
- <b>`/stats`</b> — Show bot stats (owner only)
- <b>`/status`</b> — Show bot status (admins)
- <b>`/broadcast`</b> — Broadcast a message to all users (admins)
- <b>`/cleanup`</b> — Remove inactive users from database (admins)

## 🔑 Environment Variables

Below are the required and optional environment variables for deployment.

```env
API_ID=              # Required - Get from https://my.telegram.org
API_HASH=            # Required - From https://my.telegram.org
TG_BOT_TOKEN=        # Required - Get from @BotFather
OWNER_ID=            # Required - Your Telegram user ID
ADMINS=              # Required - Admin user IDs (space separated)
DB_URL=              # Required - MongoDB connection string
DB_NAME=             # Optional - MongoDB database name (default: LinkShareBot)
DATABASE_CHANNEL=    # Required - Private channel ID for link storage
```

⚠️ **Never expose raw credentials or tokens in public repos.** Use safe paste services like [Pastebin](https://pastebin.com) or [Batbin](https://batbin.me).

## 

<details>
  <summary><b>Where do I get each key?</b></summary>



  <br/>

  <table>
    <thead>
      <tr>
        <th>Key</th>
        <th>Where to Get It</th>
        <th>Steps</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><code>API_ID</code> &amp; <code>API_HASH</code></td>
        <td><a href="https://my.telegram.org" target="_blank">my.telegram.org</a> → <i>API Development Tools</i></td>
        <td>
          1) Log in with Telegram →
          2) Open <b>API Development Tools</b> →
          3) Create app →
          4) Copy values
        </td>
        <td>Keep these private. Needed by both userbot &amp; bot client.</td>
      </tr>
      <tr>
        <td><code>TG_BOT_TOKEN</code></td>
        <td><a href="https://t.me/BotFather" target="_blank">@BotFather</a></td>
        <td>
          1) <b>/newbot</b> →
          2) Set name &amp; username →
          3) Copy the token
        </td>
        <td>Rotate if leaked. Store in <code>.env</code>.</td>
      </tr>
      <tr>
        <td><code>OWNER_ID</code></td>
        <td>Telegram <b>Profile</b> you own</td>
        <td>
          1) Use <b>@userinfobot</b> or <b>@getmyid_bot</b> →
          2) Send any message to get your ID →
          3) Copy the number
        </td>
        <td>Must be a single number (yours).</td>
      </tr>
      <tr>
        <td><code>ADMINS</code></td>
        <td>Telegram <b>Profiles</b> of admins</td>
        <td>
          1) Get IDs via <b>@userinfobot</b> →
          2) Add multiple IDs space-separated →
          3) Include OWNER_ID if needed
        </td>
        <td>Space-separated list of admin IDs.</td>
      </tr>
      <tr>
        <td><code>DB_URL</code></td>
        <td><a href="https://www.mongodb.com/atlas/database" target="_blank">MongoDB Atlas</a></td>
        <td>
          1) Create free cluster →
          2) Add database user &amp; IP allowlist →
          3) Copy connection string (<code>mongodb+srv://...</code>)
        </td>
        <td>Required for persistence (channels, users, etc.).</td>
      </tr>
      <tr>
        <td><code>DATABASE_CHANNEL</code></td>
        <td>Telegram <b>Channel</b> you own</td>
        <td>
          1) Create private channel →
          2) Add your bot as admin →
          3) Get ID via <code>@userinfobot</code> or <code>@getmyid_bot</code>
        </td>
        <td>Private channel for link storage.</td>
      </tr>
    </tbody>
  </table>

  <br/>
</details>

## 

### ☕ VPS Setup Guide

<img src="https://img.shields.io/badge/Show%20/Hide-VPS%20Steps-0ea5e9?style=for-the-badge" alt="Toggle VPS Steps"/>
<div align="left">
  <details>

```bash
🎵 Deploy LinkShareBot on VPS

# Step 1: Update & Install Dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl python3-pip python3-venv ffmpeg unzip tmux

# Step 2: Clone & Setup
git clone https://github.com/yourusername/LinkShareBot
cd LinkShareBot
tmux new -s LinkShareBot

# Inside tmux:
python3 -m venv venv
source venv/bin/activate
pip install -U pip && pip install -r requirements.txt

# Create .env file with your environment variables
nano .env

# Run the bot
python3 main.py

### Useful Commands
tmux detach                      # Use Ctrl+B, then D
tmux attach-session -t LinkShareBot       # Reattach session
tmux kill-session -t LinkShareBot         # Kill bot session
rm -rf LinkShareBot                # Uninstall bot
```

  </details>
</div>

## 

### 🐳 Docker Deployment

<img src="https://img.shields.io/badge/Show%20/Hide-Docker%20Steps-10b981?style=for-the-badge" alt="Toggle Docker Steps"/>

<div align="left">
  <details>

```bash
### Step 1: Clone Repo
git clone https://github.com/yourusername/LinkShareBot
cd LinkShareBot

### Step 2: Create .env File
nano .env
# Paste your environment variables here and save (Ctrl+O, Enter, Ctrl+X)

### Step 3: Build Image
docker build -t linksharebot .

### Step 4: Run Container
docker run -d --name linkshare --env-file .env --restart unless-stopped linksharebot

### Step 5: Manage Container
docker logs -f linkshare        # View logs (Ctrl+C to exit)
docker stop linkshare           # Stop container
docker start linkshare          # Start again
docker rm -f linkshare          # Remove container
docker rmi linksharebot         # Remove image
```

  </details>
</div>

## 

### ☁️ Quick Deploy

| Platform                | Deploy Link                                                                                                                                                                                               |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🌍 **Heroku Deploy**    | <a href="http://dashboard.heroku.com/new?template=https://github.com/codeflix-bots/LinkShareBot"><img src="https://img.shields.io/badge/Deploy%20to-Heroku-purple?style=for-the-badge&logo=heroku"/></a> |


## 💬 Community & Support

<p align="center">
  <a href="https://t.me/codeflixsupport">
    <img src="https://img.shields.io/badge/Support_Group-Telegram-0088cc?style=for-the-badge&logo=telegram&logoColor=white" />
  </a>
  <a href="https://t.me/codeflix_bots">
    <img src="https://img.shields.io/badge/Updates_Channel-Telegram-6A5ACD?style=for-the-badge&logo=telegram&logoColor=white" />
  </a>
  <a href="https://t.me/proyato">
    <img src="https://img.shields.io/badge/Contact_Owner-Telegram-4CAF50?style=for-the-badge&logo=telegram&logoColor=white" />
  </a>
  <a href="mailto:proyato.com">
    <img src="https://img.shields.io/badge/Contact-Email-0078D4?style=for-the-badge&logo=gmail&logoColor=white" />
  </a>
</p>

## 

### 🔖 Credits

* <b> *ᴄʀᴀғᴛᴇᴅ ᴡɪᴛʜ ᴘᴀssɪᴏɴ ʙʏ <a href="https://github.com/proyato">ʏᴀᴛᴏ</a>* </b>
