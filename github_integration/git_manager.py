import os
import shutil
import asyncio
import urllib.parse
from datetime import datetime, timedelta
from database.models import User
from core.progress import ProgressUpdater

async def push_to_github(user_id: int, user: User, file_paths: list, updater: ProgressUpdater):
    updater.action_text = "🚀 Uploading to GitHub"
    updater.update_sync(10, "Connecting...", "Wait")

    repo = user.github_repo
    token = user.github_token

    safe_token = urllib.parse.quote(token)
    auth_url = f"https://{safe_token}@github.com/{repo}.git"
    repo_dir = f"tmp_downloads/repo_{user_id}"

    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

    updater.update_sync(30, "Cloning...", "Wait")
    clone_cmd = f"git clone --depth 1 {auth_url} {repo_dir}"
    proc = await asyncio.create_subprocess_shell(clone_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode('utf-8', 'ignore').strip()
        raise Exception(f"Failed to clone repository. Check Token/Repo.\nLog: {error_msg}")

    updater.update_sync(60, "Copying...", "Wait")
    dl_dir = os.path.join(repo_dir, "dl")
    os.makedirs(dl_dir, exist_ok=True)

    uploaded_filenames = []
    for fp in file_paths:
        shutil.copy(fp, dl_dir)
        uploaded_filenames.append(os.path.basename(fp))

    links_md_path = os.path.join(repo_dir, "Links.md")
    tehran_time = (datetime.utcnow() + timedelta(hours=3, minutes=30)).strftime("%Y-%m-%d %H:%M")
    header = "## 🔗 Direct Download Links\n Click on any link below to start downloading directly.\n\n"

    new_links_content = f"### 📅 {tehran_time} (IR Time)\n"
    links = []

    for fname in uploaded_filenames:
        encoded_name = urllib.parse.quote(fname)

        raw_url = f"https://github.com/{repo}/raw/main/dl/{encoded_name}"
        links.append(f"📥 **[{fname}]({raw_url})**")
        new_links_content += f"- 📥 **[{fname}]({raw_url})**\n"

    new_links_content += "\n"

    if os.path.exists(links_md_path):
        with open(links_md_path, "r", encoding="utf-8") as f:
            old_content = f.read()
            if old_content.startswith(header):
                old_content = old_content[len(header):]
    else:
        old_content = ""

    with open(links_md_path, "w", encoding="utf-8") as f:
        f.write(header + new_links_content + old_content)

    updater.update_sync(80, "Pushing...", "Wait")


    commands = [
        f"cd {repo_dir}",
        "git config user.name 'RGit uploader'",
        "git config user.email 'bot@rgit.local'",
        "git checkout -B main",
        "git add -f dl/ Links.md",
        "git commit -m '✨ Add new downloads [skip ci]' || true",
        "git push -u origin main"
    ]

    push_cmd = " && ".join(commands)
    proc = await asyncio.create_subprocess_shell(push_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode('utf-8', 'ignore').strip()
        if not error_msg:
            error_msg = stdout.decode('utf-8', 'ignore').strip()
        shutil.rmtree(repo_dir, ignore_errors=True)
        raise Exception(f"Git push failed! GitHub rejected the files.\nLog: {error_msg}")

    shutil.rmtree(repo_dir, ignore_errors=True)
    return links