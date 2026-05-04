import os
from pyrogram import Client
from core.progress import ProgressUpdater


pyro_client = None

async def get_client(api_id, api_hash, bot_token):
    global pyro_client
    if pyro_client is None:

        pyro_client = Client(
            name="rgit_pyrogram",
            api_id=api_id,
            api_hash=api_hash,
            bot_token=bot_token
        )
        await pyro_client.start()
    return pyro_client

async def download_large_tg_file(
    api_id: int,
    api_hash: str,
    bot_token: str,
    message_id: int,
    chat_id: int,
    dest_path: str,
    updater: ProgressUpdater
) -> str:


    app = await get_client(api_id, api_hash, bot_token)

    msg = await app.get_messages(chat_id, message_id)

    def progress(current, total):
        if total:
            percent = (current / total) * 100
            updater.update_sync(percent, f"{current//1024//1024}MB", "Calc...")

    await app.download_media(msg, file_name=dest_path, progress=progress)

    return dest_path