import os
import re
import json
import base64
import logging
from urllib.parse import urlparse, quote
import asyncio

import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")  # Your server URL

# Terabox API endpoints
TERABOX_API_BASE = "https://terabox.hnn.workers.dev/api"
INFO_ENDPOINT = f"{TERABOX_API_BASE}/get-info-new"
DOWNLOAD_ENDPOINT = f"{TERABOX_API_BASE}/get-downloadp"

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://terabox.hnn.workers.dev/',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-storage-access': 'active'
}

# Initialize bot
app = Client(
    "terabox_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)


def extract_shorturl(url: str) -> tuple:
    """Extract shorturl and password from Terabox link"""
    try:
        # Pattern to match Terabox links
        # Examples: https://teraboxapp.com/s/1xYh6AbpepR48IAMQJPqvHg
        #           https://terabox.com/s/1xYh6AbpepR48IAMQJPqvHg
        #           https://1024terabox.com/s/1xYh6AbpepR48IAMQJPqvHg
        
        pattern = r'/s/([a-zA-Z0-9_-]+)'
        match = re.search(pattern, url)
        
        if match:
            shorturl = match.group(1)
            # Check if there's a password parameter
            pwd_match = re.search(r'[?&]pwd=([^&]+)', url)
            pwd = pwd_match.group(1) if pwd_match else ''
            return shorturl, pwd
        return None, None
    except Exception as e:
        logger.error(f"Error extracting shorturl: {e}")
        return None, None


def get_terabox_info(shorturl: str, pwd: str = '') -> dict:
    """Get file info from Terabox API"""
    try:
        params = {
            'shorturl': shorturl,
            'pwd': pwd
        }
        
        response = requests.get(INFO_ENDPOINT, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('ok'):
            return data
        else:
            logger.error(f"API returned not ok: {data}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting Terabox info: {e}")
        return None


def get_download_link(shareid: int, uk: int, sign: str, timestamp: int, fs_id: str) -> dict:
    """Get download link from Terabox API"""
    try:
        payload = {
            'shareid': shareid,
            'uk': uk,
            'sign': sign,
            'timestamp': timestamp,
            'fs_id': fs_id
        }
        
        headers = HEADERS.copy()
        headers['Content-Type'] = 'application/json'
        headers['origin'] = 'https://terabox.hnn.workers.dev'
        
        response = requests.post(
            DOWNLOAD_ENDPOINT, 
            json=payload, 
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('ok'):
            return data
        else:
            logger.error(f"Download API returned not ok: {data}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting download link: {e}")
        return None


def encode_url(url: str) -> str:
    """Encode URL for safe transmission"""
    return base64.urlsafe_b64encode(url.encode()).decode()


def format_size(bytes_size: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    await message.reply_text(
        "👋 **Welcome to Terabox Downloader Bot!**\n\n"
        "📤 Send me a Terabox link and I'll get you the download link!\n\n"
        "**Supported formats:**\n"
        "• `https://teraboxapp.com/s/xxxxx`\n"
        "• `https://terabox.com/s/xxxxx`\n"
        "• `https://1024terabox.com/s/xxxxx`\n"
        "• Any Terabox share link\n\n"
        "**Commands:**\n"
        "/start - Start the bot\n"
        "/help - Get help"
    )


@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    await message.reply_text(
        "**How to use this bot:**\n\n"
        "1️⃣ Copy a Terabox share link\n"
        "2️⃣ Send it to me\n"
        "3️⃣ I'll fetch the file info and provide a player link\n\n"
        "**Example:**\n"
        "`https://teraboxapp.com/s/1xYh6AbpepR48IAMQJPqvHg`\n\n"
        "**Note:** Only video files can be played in the browser. "
        "Other files will show a download link."
    )


@app.on_message(filters.text & filters.private)
async def handle_message(client: Client, message: Message):
    """Handle incoming messages with Terabox links"""
    text = message.text
    
    # Check if message contains a Terabox link
    if not any(domain in text.lower() for domain in ['terabox', '1024tera', 'nephobox']):
        return
    
    # Send processing message
    status_msg = await message.reply_text("🔄 **Processing your link...**")
    
    try:
        # Extract shorturl and password
        shorturl, pwd = extract_shorturl(text)
        
        if not shorturl:
            await status_msg.edit_text(
                "❌ **Invalid Terabox link!**\n\n"
                "Please send a valid Terabox share link."
            )
            return
        
        await status_msg.edit_text("📥 **Fetching file information...**")
        
        # Get file info
        info_data = get_terabox_info(shorturl, pwd)
        
        if not info_data:
            await status_msg.edit_text(
                "❌ **Failed to fetch file information!**\n\n"
                "The link might be invalid or expired."
            )
            return
        
        # Extract file list
        file_list = info_data.get('list', [])
        
        if not file_list:
            await status_msg.edit_text(
                "❌ **No files found in this link!**"
            )
            return
        
        # Process first file (you can extend this to handle multiple files)
        file_info = file_list[0]
        filename = file_info.get('filename', 'Unknown')
        file_size = int(file_info.get('size', 0))
        fs_id = file_info.get('fs_id')
        category = file_info.get('category', '0')
        
        await status_msg.edit_text("🔗 **Getting download link...**")
        
        # Get download link
        download_data = get_download_link(
            shareid=info_data.get('shareid'),
            uk=info_data.get('uk'),
            sign=info_data.get('sign'),
            timestamp=info_data.get('timestamp'),
            fs_id=fs_id
        )
        
        if not download_data:
            await status_msg.edit_text(
                "❌ **Failed to get download link!**\n\n"
                "Please try again later."
            )
            return
        
        download_link = download_data.get('downloadLink')
        
        if not download_link:
            await status_msg.edit_text(
                "❌ **Download link not available!**"
            )
            return
        
        # Encode the download link
        encoded_link = encode_url(download_link)
        
        # Create player URL
        player_url = f"{BASE_URL}/player?v={encoded_link}&name={quote(filename)}"
        
        # Determine if it's a video file
        is_video = category == '1' or any(
            filename.lower().endswith(ext) 
            for ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv']
        )
        
        # Create response message
        response = f"✅ **File Information**\n\n"
        response += f"📁 **Name:** `{filename}`\n"
        response += f"📦 **Size:** `{format_size(file_size)}`\n"
        response += f"🎬 **Type:** {'Video' if is_video else 'File'}\n\n"
        
        # Create inline keyboard
        keyboard = []
        
        if is_video:
            keyboard.append([
                InlineKeyboardButton("▶️ Play Online", url=player_url)
            ])
        
        keyboard.append([
            InlineKeyboardButton("📥 Direct Download", url=download_link)
        ])
        
        await status_msg.edit_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await status_msg.edit_text(
            "❌ **An error occurred while processing your request!**\n\n"
            f"Error: `{str(e)}`"
        )


if __name__ == "__main__":
    logger.info("Starting Terabox Bot...")
    app.run()
