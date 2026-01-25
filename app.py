import logging
import re
import requests
import urllib3
import json
import os
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)



# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client(
    "url_extractor_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

def extract_inshorturl(url):
    """Extract the real URL from InShortURL link."""
    try:
        match = re.search(r'inshorturl\.in/([a-zA-Z0-9]+)', url)
        if not match:
            return {'success': False, 'error': 'Invalid InShortURL format'}
        
        short_code = match.group(1)
        session = requests.Session()
        
        headers_get = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'referer': 'https://mahitimanch.in/',
            'upgrade-insecure-requests': '1',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'priority': 'u=0, i',
            'pragma': 'no-cache',
            'cache-control': 'no-cache'
        }
        
        response1 = session.get(f'https://inshorturl.in/{short_code}', headers=headers_get, verify=False)
        html = response1.text
        
        ad_form_match = re.search(r'name="ad_form_data"\s+value="([^"]+)"', html)
        if not ad_form_match:
            return {'success': False, 'error': 'Could not extract ad_form_data'}
        ad_form_data = ad_form_match.group(1)
        
        token_fields_match = re.search(r'name="_Token\[fields\]"[^>]+value="([^"]+)"', html)
        if not token_fields_match:
            return {'success': False, 'error': 'Could not extract token fields'}
        token_fields = token_fields_match.group(1)
        
        token_unlocked_match = re.search(r'name="_Token\[unlocked\]"[^>]+value="([^"]+)"', html)
        token_unlocked = token_unlocked_match.group(1) if token_unlocked_match else 'adcopy_challenge%7Cadcopy_response%7Cg-recaptcha-response%7Ch-captcha-response'
        
        csrf_token_match = re.search(r'name="_csrfToken"[^>]+value="([^"]+)"', html)
        if not csrf_token_match:
            return {'success': False, 'error': 'Could not extract CSRF token'}
        csrf_token = csrf_token_match.group(1)
        
        headers_post = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'x-requested-with': 'XMLHttpRequest',
            'origin': 'https://inshorturl.in',
            'referer': f'https://inshorturl.in/{short_code}',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'pragma': 'no-cache',
            'cache-control': 'no-cache'
        }
        
        post_data = {
            '_csrfToken': csrf_token,
            'ad_form_data': ad_form_data,
            '_Token[fields]': token_fields,
            '_Token[unlocked]': token_unlocked
        }
        
        response2 = session.post('https://inshorturl.in/links/go', 
                                headers=headers_post, 
                                data=post_data,
                                verify=False)
        
        return response2.json()
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def extract_softurl(url):
    """Extract the real URL from SoftURL link."""
    try:
        match = re.search(r'softurl\.in/([a-zA-Z0-9]+)', url)
        if not match:
            return {'success': False, 'error': 'Invalid SoftURL format'}
        
        short_code = match.group(1)
        session = requests.Session()
        
        # Step 1: Initial GET request to get the landing page
        headers_get = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'upgrade-insecure-requests': '1',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'priority': 'u=0, i',
            'te': 'trailers',
            'Cookie': 'lang=en_US'
        }
        
        response1 = session.get(f'https://softurl.in/{short_code}', headers=headers_get, verify=False)
        html = response1.text
        
        # Extract base64 encoded value from hidden input
        import base64
        go_value_match = re.search(r'name="go"\s+value="([^"]+)"', html)
        if not go_value_match:
            return {'success': False, 'error': 'Could not extract go value', 'html_snippet': html[:1000]}
        
        go_value = go_value_match.group(1)
        
        # Decode base64 to get the actual URL with token
        try:
            decoded_url = base64.b64decode(go_value).decode('utf-8')
        except Exception as e:
            return {'success': False, 'error': f'Could not decode base64: {str(e)}'}
        
        # Extract token from decoded URL
        token_match = re.search(r'\?([a-f0-9]{128})', decoded_url)
        if not token_match:
            return {'success': False, 'error': 'Could not extract token from decoded URL', 'decoded_url': decoded_url}
        
        token = token_match.group(1)
        
        # Step 2: GET request with token
        response2 = session.get(f'https://softurl.in/{short_code}?{token}', headers=headers_get, verify=False)
        html2 = response2.text
        
        # Extract ad_form_data
        ad_form_match = re.search(r'name="ad_form_data"\s+value="([^"]+)"', html2)
        if not ad_form_match:
            return {'success': False, 'error': 'Could not extract ad_form_data', 'html_snippet': html2[:1000]}
        ad_form_data = ad_form_match.group(1)
        
        # Extract _Token[fields]
        token_fields_match = re.search(r'name="_Token\[fields\]"[^>]+value="([^"]+)"', html2)
        if not token_fields_match:
            return {'success': False, 'error': 'Could not extract token fields'}
        token_fields = token_fields_match.group(1)
        
        # Extract _Token[unlocked]
        token_unlocked_match = re.search(r'name="_Token\[unlocked\]"[^>]+value="([^"]+)"', html2)
        token_unlocked = token_unlocked_match.group(1) if token_unlocked_match else 'adcopy_challenge%7Cadcopy_response%7Cg-recaptcha-response%7Ch-captcha-response'
        
        # Extract _csrfToken
        csrf_token_match = re.search(r'name="_csrfToken"[^>]+value="([^"]+)"', html2)
        if not csrf_token_match:
            return {'success': False, 'error': 'Could not extract CSRF token'}
        csrf_token = csrf_token_match.group(1)
        
        # Step 3: POST request
        headers_post = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'x-requested-with': 'XMLHttpRequest',
            'origin': 'https://softurl.in',
            'referer': f'https://softurl.in/{short_code}?{token}',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'pragma': 'no-cache',
            'cache-control': 'no-cache'
        }
        
        post_data = {
            '_csrfToken': csrf_token,
            'ad_form_data': ad_form_data,
            '_Token[fields]': token_fields,
            '_Token[unlocked]': token_unlocked
        }
        
        response3 = session.post('https://softurl.in/links/go', 
                                headers=headers_post, 
                                data=post_data,
                                verify=False)
        
        return response3.json()
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def extract_terabox(url):
    """Extract streaming info from Terabox URL."""
    try:
        session = requests.Session()
        
        # Step 1: GET request to playertera.com to get cookies
        headers_get = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'upgrade-insecure-requests': '1',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'sec-fetch-user': '?1',
            'priority': 'u=0, i',
            'te': 'trailers'
        }
        
        response1 = session.get('https://www.playertera.com', headers=headers_get, verify=False)
        
        # Extract XSRF-TOKEN and playertera_session from cookies
        xsrf_token = session.cookies.get('XSRF-TOKEN', '')
        playertera_session = session.cookies.get('playertera_session', '')
        
        if not xsrf_token or not playertera_session:
            return {'success': False, 'error': 'Could not retrieve required cookies'}
        
        # Decode XSRF token for the header (URL decode it)
        import urllib.parse
        xsrf_decoded = urllib.parse.unquote(xsrf_token)
        
        # Extract the actual token from the JSON structure
        import json as json_module
        try:
            xsrf_data = json_module.loads(xsrf_decoded)
            csrf_token = xsrf_data.get('value', xsrf_token)
        except:
            csrf_token = xsrf_token
        
        # Step 2: POST request to API with the Terabox URL
        headers_post = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'referer': 'https://www.playertera.com/',
            'x-csrf-token': csrf_token,
            'origin': 'https://www.playertera.com',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'priority': 'u=0',
            'te': 'trailers'
        }
        
        post_data = {
            'url': url
        }
        
        response2 = session.post('https://www.playertera.com/api/process-terabox',
                                headers=headers_post,
                                json=post_data,
                                verify=False)
        
        return response2.json()
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def extract_url(url):
    """Route to the appropriate extractor based on URL."""
    if 'inshorturl.in' in url.lower():
        return extract_inshorturl(url)
    elif 'softurl.in' in url.lower():
        return extract_softurl(url)
    elif 'tera' in url.lower():
        return extract_terabox(url)
    else:
        return {'success': False, 'error': 'Unsupported URL service. Supported: InShortURL, SoftURL, and Terabox.'}

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle /start command"""
    await message.reply_text(
        "👋 **Welcome to Multi-URL Extractor Bot!**\n\n"
        "I can extract real URLs from:\n"
        "• InShortURL (inshorturl.in)\n"
        "• SoftURL (softurl.in)\n"
        "• Terabox (teraboxurl.com)\n\n"
        "Just send me a link and I'll extract it for you!\n\n"
        "**Commands:**\n"
        "• /start - Show this message\n"
        "• /help - Show help message"
    )

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handle /help command"""
    await message.reply_text(
        "📖 **How to use:**\n\n"
        "1. Send me a shortened URL\n"
        "2. Wait a few seconds\n"
        "3. I'll send you the extracted URL and full JSON response\n\n"
        "**Supported services:**\n"
        "• InShortURL: `https://inshorturl.in/wUkoUP`\n"
        "• SoftURL: `https://softurl.in/EtlG2`\n"
        "• Terabox: `https://teraboxurl.com/s/133mEB-nn0-4vkXdnQeItyQ`"
    )

@app.on_message(filters.text & filters.private)
async def handle_message(client: Client, message: Message):
    """Handle incoming messages with URLs"""
    text = message.text
    
    # Check if message contains a supported URL
    if any(service in text.lower() for service in ['inshorturl.in', 'softurl.in', 'terabox', 'terasharefile.com']):
        # Send processing message
        processing_msg = await message.reply_text("🔄 Processing your link, please wait...")
        
        try:
            # Extract the URL
            result = extract_url(text)
            
            # Delete processing message
            await processing_msg.delete()
            
            # Special handling for Terabox responses - send full JSON
            if any(service in text.lower() for service in ['terabox', 'terasharefile.com']):
                # Convert to JSON string without markdown formatting to avoid HTML entity issues
                json_str = json.dumps(result, indent=2, ensure_ascii=False)
                json_str = str(json_str).replace('×tamp=', '&timestamp=')
                # Send as plain text without markdown to preserve & characters
                response_text = f"📋 Full JSON Response:\n\n{json_str}"
                await message.reply_text(json_str, parse_mode=ParseMode.DISABLED)
            else:
                # Standard response for other services
                json_str = json.dumps(result, indent=2, ensure_ascii=False)
                json_str = json_str.replace('×tamp=', '&timestamp=')
                response_text = f"📋 Full JSON Response:\n\n{json_str}"
                
                # Check if response has a URL field and show it prominently
                if 1==1:
                    response_text = (
                        f"✅ Success!\n\n"
                        f"🔗 Extracted URL:\n{result.get('url')}\n\n"
                        f"📋 Full JSON Response:\n\n{json_str}"
                    )
                
                await message.reply_text(response_text, disable_web_page_preview=True)
                
        except Exception as e:
            await processing_msg.delete()
            await message.reply_text(f"❌ An error occurred: {str(e)}")
    else:
        await message.reply_text(
            "⚠️ Please send a valid shortened URL.\n\n"
            "**Supported services:**\n"
            "• InShortURL: `https://inshorturl.in/wUkoUP`\n"
            "• SoftURL: `https://softurl.in/EtlG2`\n"
            "• Terabox: `https://teraboxurl.com/s/...` or `https://terasharefile.com/s/...`"
        )

if __name__ == "__main__":
    logger.info("Bot is starting...")
    app.run()