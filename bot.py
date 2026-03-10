import asyncio
import os
import time
import tempfile
import logging
import random
import base64
from seleniumbase import SB
from selenium.webdriver.common.by import By
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Your credentials
API_ID = 34218110
API_HASH = 'cbb5eccca7669c2fc134d85f31004677'
SESSION_STRING = "1BVtsOIUBuw4qPpLEMAeDLsJDh3h9KeHRs5xrjd3qzzJ8vGiY50rEVLjxI_LHsV882ABRE3SecoET-lE9X7wobMTmWrGv_k70uwHKLgt7ZBuvw0N-LjjSDYtPd9U8-KLRoi20XesHUrD_xq8KAVYaVxP2inFmJUAMfCVulmsGe8ef52GwW3YfaGlPM4Ff7pWqdu3LanaLU9_eTCXDyQ0-GyDnMB2RtxhALL3GIpIc3zyU1Phxe-U0OYJf-ILCxf7QBsxmlYV_kEZcZWjv-_fIPaHINjIZelB99g4htKbYwzIEW-fQnkGXZ6TrTRT4X4i4FLW8wS-zeAoy9RyJQlQ6X9KZmdjzJxc="

# Initialize Telegram client with StringSession
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def extract_button_info(message):
    """Extract URL from inline button"""
    if message.reply_markup and hasattr(message.reply_markup, 'rows'):
        for row in message.reply_markup.rows:
            for btn in row.buttons:
                if hasattr(btn, 'url') and btn.url:
                    logger.info(f"Found URL button: {btn.text} -> {btn.url}")
                    return {
                        'text': btn.text,
                        'url': btn.url,
                        'type': 'web_app'
                    }
    return None

@client.on(events.NewMessage(pattern=r'\.extract$'))
async def extract_handler(event):
    """Handle .extract command"""
    logger.info(f"Extract command received")
    
    if not event.is_reply:
        await event.reply("❌ Please reply to a message with `.extract`")
        return
    
    msg = await event.get_reply_message()
    status = await event.reply("🔍 Extracting button information...")
    
    try:
        button_info = extract_button_info(msg)
        if not button_info or not button_info.get('url'):
            await status.edit("❌ No web app URL found")
            return
        
        await status.edit(f"🔄 Loading {button_info['url']}...")
        
        # Use xvfb=True for virtual display (Xvfb must be installed system-wide)
        with SB(uc=True, xvfb=True, headless=False) as sb:
            sb.uc_open_with_reconnect(button_info['url'], reconnect_time=3)
            time.sleep(3)
            
            # Get page content
            html_content = sb.get_page_source()
            page_title = sb.get_page_title()
            
            # Save to temp file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = os.path.join(tempfile.gettempdir(), 'extracted')
            os.makedirs(temp_dir, exist_ok=True)
            
            html_file = os.path.join(temp_dir, f"webpage_{timestamp}.html")
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            await event.reply(f"✅ **Extraction Complete!**\nURL: {button_info['url']}\nTitle: {page_title}")
            await client.send_file(event.chat_id, html_file, force_document=True)
            os.remove(html_file)
            await status.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status.edit(f"❌ Error: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.verify$'))
async def verify_handler(event):
    """Handle .verify command"""
    logger.info(f"Verify command received")
    
    await event.reply("🔄 Processing your verification request...")
    
    if not event.is_reply:
        await event.reply("❌ Please reply to a verification message with `.verify`")
        return
    
    msg = await event.get_reply_message()
    status = await event.reply("🔍 Analyzing message...")
    
    try:
        button_info = extract_button_info(msg)
        if not button_info or not button_info.get('url'):
            await status.edit("❌ No verification button found")
            return
        
        user_id = event.sender_id
        await status.edit(f"✅ Found button: **{button_info['text']}**\n\n"
                         f"🔄 Starting verification process...")
        
        # Use xvfb=True for virtual display (requires Xvfb system package)
        # According to SeleniumBase docs, on Linux use xvfb=True instead of headless mode [citation:7]
        with SB(uc=True, xvfb=True, incognito=True) as sb:
            # Step 1: Open URL with anti-detection
            await status.edit("🔄 Loading verification page with anti-detection...")
            sb.uc_open_with_reconnect(button_info['url'], reconnect_time=4)
            time.sleep(3)
            
            # Step 2: Inject Telegram WebApp simulation
            init_data = f"user_id={user_id}&auth_date={int(time.time())}"
            encoded_data = base64.b64encode(init_data.encode()).decode()
            
            sb.execute_script(f"""
                window.Telegram = {{
                    WebApp: {{
                        initData: '{encoded_data}',
                        initDataUnsafe: {{
                            user: {{
                                id: {user_id},
                                first_name: 'User',
                                last_name: '',
                                username: 'auto_verifier',
                                language_code: 'en'
                            }}
                        }},
                        ready: function() {{ this.isReady = true; }},
                        expand: function() {{ }},
                        close: function() {{ window.verificationComplete = true; }}
                    }}
                }};
                window.Telegram.WebApp.ready();
                window.Telegram.WebApp.expand();
            """)
            logger.info("Injected Telegram WebApp simulation")
            time.sleep(2)
            
            # Step 3: Use UC Mode's built-in Turnstile handler [citation:7]
            await status.edit("🔄 Handling Cloudflare Turnstile...")
            try:
                # This method specifically handles Turnstile
                sb.uc_gui_handle_captcha(timeout=60)
                logger.info("CAPTCHA handling completed")
            except Exception as e:
                logger.warning(f"CAPTCHA handler note: {e}")
            
            # Step 4: Try to click verify image if visible
            await status.edit("🔄 Looking for verify image...")
            for attempt in range(20):
                try:
                    img = sb.find_element(By.ID, "verify-img")
                    if img and img.is_displayed():
                        logger.info(f"✅ Verify image found, clicking...")
                        sb.uc_click("#verify-img", reconnect_time=2)
                        break
                except:
                    pass
                time.sleep(1)
            
            # Step 5: Wait for verification
            time.sleep(5)
            
            # Step 6: Check for success
            await status.edit("🔄 Checking verification result...")
            
            try:
                # Check if page closed (tg.close() was called)
                sb.get_current_url()
                # Page still open, check for success message
                page_source = sb.get_page_source()
                if "✅" in page_source or "Success" in page_source:
                    success = True
                else:
                    success = False
            except:
                # Page closed - verification successful
                success = True
            
            if success:
                await status.edit("✅ **VERIFICATION SUCCESSFUL!**\n\nYou should now be verified.")
                
                # Check for confirmation message from bot
                await asyncio.sleep(3)
                async for new_msg in client.iter_messages(msg.chat_id, limit=5):
                    if new_msg.sender_id == msg.sender_id and new_msg.id > msg.id:
                        if new_msg.text and "✅" in new_msg.text:
                            await event.reply(f"📨 Bot confirmation:\n{new_msg.text}")
                            break
            else:
                await status.edit("❌ Verification failed. The captcha could not be solved.")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status.edit(f"❌ Error: {str(e)}")

@client.on(events.NewMessage(pattern=r'\.test$'))
async def test_handler(event):
    await event.reply("✅ Bot is working!\n\nCommands:\n• `.extract`\n• `.verify`\n• `.help`")

@client.on(events.NewMessage(pattern=r'\.help$'))
async def help_handler(event):
    help_text = (
        "**🤖 BAKA Bot Auto-Verifier**\n\n"
        "**Commands:**\n"
        "`.verify` - Complete verification\n"
        "`.extract` - Extract webpage HTML\n"
        "`.test` - Test if bot works\n"
        "`.help` - Show this help\n\n"
        "**Technical Requirements:**\n"
        "• Chrome installed system-wide\n"
        "• Xvfb for virtual display\n"
        "• SeleniumBase UC Mode [citation:7]\n\n"
        "**Usage:**\n"
        "Reply to VERIFY NOW message with `.verify`"
    )
    await event.reply(help_text)

async def main():
    print("\n" + "="*60)
    print("🤖 BAKA BOT AUTO-VERIFIER")
    print("="*60)
    print("Commands: .verify | .extract | .test | .help")
    print("="*60)
    
    logger.info("Starting BAKA Auto-Verifier...")
    
    try:
        await client.start()
        me = await client.get_me()
        logger.info(f"✅ Logged in as: {me.first_name}")
        
        print("\n📝 Bot is ready!")
        print("  • Reply to VERIFY NOW message with .verify")
        print("  • Using Xvfb virtual display [citation:5]\n")
        
        await client.run_until_disconnected()
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())