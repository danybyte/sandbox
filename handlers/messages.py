import os
import aiohttp
import uuid
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database.crud import get_user
from handlers.callbacks import prepare_download_task
from core.progress import ProgressUpdater
from config import TG_API_ID, TG_API_HASH, BOT_TOKEN
from core.tg_downloader import download_large_tg_file

router = Router()

async def download_tg_file(bot, file_path: str, dest_path: str, updater: ProgressUpdater):
    url = f"https://api.telegram.org/file/bot{bot.token}/{file_path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            with open(dest_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        updater.update_sync(percent, "TG Server", "Calc...")

@router.message(F.text.regexp(r'https?://[^\s]+'))
async def handle_url(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not user.github_token:
        await message.answer("⚠️ Please set your token via /set_token first.")
        return

    url = message.text.strip()
    await state.update_data(target_url=url)
    media_domains =["youtube.com", "youtu.be", "twitch.tv", "reddit.com", "vimeo.com", "soundcloud.com"]
    is_media = any(domain in url for domain in media_domains)

    if is_media:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌟 Best Quality", callback_data="qual_best")],[InlineKeyboardButton(text="📺 720p", callback_data="qual_720p"), InlineKeyboardButton(text="📱 480p", callback_data="qual_480p")],[InlineKeyboardButton(text="📉 360p", callback_data="qual_360p"), InlineKeyboardButton(text="🎵 Audio", callback_data="qual_audio")]
        ])
        await message.answer("🎬 **Media link detected!**\nPlease select the desired quality:", reply_markup=keyboard, parse_mode="Markdown")
    else:
        await state.update_data(quality="best")
        await ask_compression(message)

@router.message(F.document | F.video | F.photo | F.audio)
async def handle_file(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not user.github_token:
        await message.answer("⚠️ Please set your token via /set_token first.")
        return


    if message.document:
        file_name = message.document.file_name or f"Document_{message.message_id}"
        file_id = message.document.file_id
        file_size = message.document.file_size or 0
    elif message.video:
        file_name = message.video.file_name or f"Video_{message.message_id}.mp4"
        file_id = message.video.file_id
        file_size = message.video.file_size or 0
    elif message.audio:
        file_name = message.audio.file_name or f"Audio_{message.message_id}.mp3"
        file_id = message.audio.file_id
        file_size = message.audio.file_size or 0
    else:
        file_name = f"Photo_{message.message_id}.jpg"
        file_id = message.photo[-1].file_id
        file_size = message.photo[-1].file_size or 0

    status_msg = await message.answer("⬇️ **Downloading from Telegram...**", parse_mode="Markdown")
    updater = ProgressUpdater(status_msg, action_text="Fetching File")

    dl_dir = os.path.join("tmp_downloads", uuid.uuid4().hex[:8])
    os.makedirs(dl_dir, exist_ok=True)
    file_path = os.path.join(dl_dir, file_name)

    try:
        if file_size > 20 * 1024 * 1024:
            if not TG_API_ID or not TG_API_HASH:
                await status_msg.edit_text("❌ **File too large!**\n\nAdd `TG_API_ID` and `TG_API_HASH` to `.env` to enable large file support.", parse_mode="Markdown")
                return

            await download_large_tg_file(
                api_id=TG_API_ID, api_hash=TG_API_HASH, bot_token=BOT_TOKEN,
                message_id=message.message_id, chat_id=message.chat.id,
                dest_path=file_path, updater=updater
            )
        else:
            file_info = await message.bot.get_file(file_id)
            await download_tg_file(message.bot, file_info.file_path, file_path, updater)
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error downloading: {str(e)}")
        return

    await state.update_data(target_url=file_path, quality="raw", is_local_file=True)
    await ask_compression(message)

async def ask_compression(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📄 Raw (No Zip)", callback_data="comp_raw")],[InlineKeyboardButton(text="📦 Zip (Max Compression)", callback_data="comp_zip")],[InlineKeyboardButton(text="🔐 Zip with Password", callback_data="comp_pass")]])
    await message.answer("📥 **File ready!**\nHow should I process it?", reply_markup=keyboard, parse_mode="Markdown")