import os
from pyrogram import Client
from core.progress import ProgressUpdater

async def download_large_tg_file(
    api_id: int,
    api_hash: str,
    bot_token: str,
    message_id: int,
    chat_id: int,
    dest_path: str,
    updater: ProgressUpdater
) -> str:

    async with Client(
        name="rgit_bot_session",
        api_id=api_id,
        api_hash=api_hash,
        bot_token=bot_token,
        in_memory=True
    ) as app:
        msg = await app.get_messages(chat_id, message_id)

        def progress(current, total):
            if total:
                percent = (current / total) * 100
                updater.update_sync(percent, f"{current//1024//1024}MB", "Calc...")

        await app.download_media(msg, file_name=dest_path, progress=progress)

    return dest_path