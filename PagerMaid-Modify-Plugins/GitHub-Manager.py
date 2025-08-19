#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" GitHub仓库管理插件 - 简化命令版 """

import os
import re
import json
import base64
import asyncio
import requests
from datetime import datetime
from pagermaid import version
from pagermaid.listener import listener
from pagermaid.utils import alias_command, lang
from pagermaid.services import bot, scheduler
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto
from telethon.errors.rpcerrorlist import FilePartMissingError

# GitHub API配置
GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
TOKEN_FILE = "github_token.txt"
CACHE_FILE = "github_repos_cache.json"
CACHE_EXPIRY = 3600  # 1小时缓存

# 自动删除消息的时间配置
DELETE_DELAY = 15  # 普通消息15秒后删除
HELP_DELAY = 30    # 帮助消息30秒后删除

# 从环境变量或文件获取GitHub Token
def get_github_token():
    if "GITHUB_TOKEN" in os.environ:
        return os.environ["GITHUB_TOKEN"]
    
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token = f.read().strip()
                if token:
                    return token
        except:
            pass
    
    return None

# 保存GitHub Token到文件
def save_github_token(token):
    try:
        with open(TOKEN_FILE, "w") as f:
            f.write(token)
        return True
    except:
        return False

# 获取GitHub用户信息
def get_github_user_info(token):
    headers = {"Authorization": f"token {token}"}
    response = requests.get(f"{GITHUB_API}/user", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# 获取仓库默认分支
def get_repo_default_branch(token, repo):
    headers = {"Authorization": f"token {token}"} if token else {}
    owner, repo_name = repo.split("/") if "/" in repo else (get_github_user_info(token)["login"], repo)
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("default_branch", "main")
    return "main"

# 获取用户仓库列表
def get_user_repos(token, refresh=False):
    if not refresh and os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache = json.load(f)
                if datetime.now().timestamp() - cache["timestamp"] < CACHE_EXPIRY:
                    return cache["repos"]
        except:
            pass
    
    headers = {"Authorization": f"token {token}"}
    response = requests.get(f"{GITHUB_API}/user/repos?per_page=100", headers=headers)
    
    if response.status_code == 200:
        repos = response.json()
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({
                    "timestamp": datetime.now().timestamp(),
                    "repos": repos
                }, f)
        except:
            pass
        return repos
    
    return []

# 获取仓库文件列表
def get_repo_contents(token, repo, path=""):
    headers = {"Authorization": f"token {token}"}
    owner, repo_name = repo.split("/") if "/" in repo else (get_github_user_info(token)["login"], repo)
    default_branch = get_repo_default_branch(token, repo)
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}/contents/{path}?ref={default_branch}" if path else f"{GITHUB_API}/repos/{owner}/{repo_name}/contents?ref={default_branch}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# 上传文件到GitHub - 支持自动创建目录
def upload_to_github(token, repo, path, content, message="Uploaded by Pagermaid"):
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    
    owner, repo_name = repo.split("/") if "/" in repo else (get_github_user_info(token)["login"], repo)
    default_branch = get_repo_default_branch(token, repo)
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}/contents/{path}"
    
    # 检查文件是否存在以获取SHA
    sha = None
    params = {"ref": default_branch}
    existing = requests.get(url, headers=headers, params=params)
    if existing.status_code == 200:
        sha = existing.json().get("sha")
    
    data = {
        "message": message,
        "content": base64.b64encode(content).decode("utf-8"),
        "branch": default_branch
    }
    
    if sha:
        data["sha"] = sha
    
    response = requests.put(url, headers=headers, json=data)
    return response.json()

# 删除GitHub文件
def delete_github_file(token, repo, path, message="Deleted by Pagermaid"):
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json"
    }
    
    owner, repo_name = repo.split("/") if "/" in repo else (get_github_user_info(token)["login"], repo)
    default_branch = get_repo_default_branch(token, repo)
    url = f"{GITHUB_API}/repos/{owner}/{repo_name}/contents/{path}"
    
    # 获取文件SHA
    params = {"ref": default_branch}
    existing = requests.get(url, headers=headers, params=params)
    if existing.status_code != 200:
        return {"message": "File not found"}
    
    data = existing.json()
    if isinstance(data, list):
        return {"message": "Path is a directory, not a file"}
    
    sha = data.get("sha")
    if not sha:
        return {"message": "Failed to get file SHA"}
    
    data = {
        "message": message,
        "sha": sha,
        "branch": default_branch
    }
    
    response = requests.delete(url, headers=headers, json=data)
    return response.json()

# 下载GitHub文件
def download_github_file(token, repo, path):
    headers = {"Authorization": f"token {token}"} if token else {}
    owner, repo_name = repo.split("/") if "/" in repo else (get_github_user_info(token)["login"], repo)
    default_branch = get_repo_default_branch(token, repo)
    url = f"{GITHUB_RAW}/{owner}/{repo_name}/{default_branch}/{path}"
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    return None

# 获取文件raw地址
def get_raw_url(repo, path):
    token = get_github_token()
    owner, repo_name = repo.split("/") if "/" in repo else (get_github_user_info(token)["login"] if token else "", repo)
    default_branch = get_repo_default_branch(token, repo) if token else "main"
    return f"{GITHUB_RAW}/{owner}/{repo_name}/{default_branch}/{path}"

# 设置GitHub Token命令
@listener(
    command="git_t",
    description="设置GitHub Token",
    parameters="<token>"
)
async def git_token(message):
    token = message.arguments.strip()
    if not token:
        msg = await message.edit("❌ 请提供GitHub个人访问令牌")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    if save_github_token(token):
        msg = await message.edit("✅ GitHub Token已保存")
    else:
        msg = await message.edit("❌ 保存GitHub Token失败")
    
    await auto_delete(msg, DELETE_DELAY)

# 查看仓库命令
@listener(
    command="git_r",
    description="查看仓库列表",
    parameters="[refresh]"
)
async def git_repos(message):
    token = get_github_token()
    if not token:
        msg = await message.edit("❌ 未设置Token，请先使用,git_t设置")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    refresh = "refresh" in message.arguments.lower()
    repos = get_user_repos(token, refresh)
    
    if not repos:
        msg = await message.edit("❌ 获取仓库列表失败")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    user_info = get_github_user_info(token)
    username = user_info["login"] if user_info else "Unknown"
    
    response = f"📦 **{username}的GitHub仓库**\n\n"
    for repo in repos[:15]:
        branch = repo["default_branch"]
        response += f"• [{repo['name']}]({repo['html_url']}) - 分支: `{branch}`\n"
    
    if len(repos) > 15:
        response += f"\n...共 {len(repos)} 个仓库 (显示前15个)"
    
    msg = await message.edit(response, link_preview=False)
    await auto_delete(msg, DELETE_DELAY)

# 查看仓库内容命令
@listener(
    command="git_l",
    description="查看仓库内容",
    parameters="<仓库名> [路径]"
)
async def git_ls(message):
    token = get_github_token()
    if not token:
        msg = await message.edit("❌ 未设置Token")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    args = message.arguments.split(maxsplit=1)
    if not args:
        msg = await message.edit("❌ 请指定仓库名")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    repo = args[0]
    path = args[1] if len(args) > 1 else ""
    
    contents = get_repo_contents(token, repo, path)
    if not contents:
        msg = await message.edit("❌ 获取仓库内容失败")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    default_branch = get_repo_default_branch(token, repo)
    response = f"📂 **{repo} 内容 (分支: {default_branch})**\n\n"
    if isinstance(contents, list):
        for item in contents:
            icon = "📄" if item["type"] == "file" else "📁"
            response += f"{icon} [{item['name']}]({item['html_url']})\n"
    else:
        # 如果是单个文件
        item = contents
        icon = "📄"
        response += f"{icon} [{item['name']}]({item['html_url']})\n"
    
    msg = await message.edit(response, link_preview=False)
    await auto_delete(msg, DELETE_DELAY)

# 上传文件命令 - 支持自动创建目录和可选提交信息
@listener(
    command="git_u",
    description="上传文件到仓库",
    parameters="<仓库名> <路径> [提交信息]"
)
async def git_upload(message):
    token = get_github_token()
    if not token:
        msg = await message.edit("❌ 未设置Token")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    reply = await message.get_reply_message()
    if not reply or not (reply.document or reply.photo):
        msg = await message.edit("❌ 请回复文件消息")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    # 解析参数（支持可选提交信息）
    args = message.arguments.split(maxsplit=2)
    if len(args) < 2:
        msg = await message.edit("❌ 格式: <仓库名> <路径> [提交信息]")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    repo = args[0]
    path = args[1]
    commit_message = args[2] if len(args) > 2 else f"上传 {os.path.basename(path)}"
    
    default_branch = get_repo_default_branch(token, repo)
    msg = await message.edit(f"⬇️ 下载中... (分支: {default_branch})")
    
    try:
        file_bytes = await download_telegram_file(reply)
        if not file_bytes:
            msg = await message.edit("❌ 下载失败")
            await auto_delete(msg, DELETE_DELAY)
            return
        
        msg = await message.edit("⬆️ 上传中...")
        
        # 上传到GitHub（自动创建目录）
        result = upload_to_github(token, repo, path, file_bytes, commit_message)
        if "content" in result:
            file_url = result["content"]["html_url"]
            msg = await message.edit(f"✅ 上传成功!\n\n🔗 [{path}]({file_url})\n分支: `{default_branch}`", link_preview=False)
        else:
            error = result.get("message", "未知错误")
            msg = await message.edit(f"❌ 失败: {error}")
    
    except Exception as e:
        msg = await message.edit(f"❌ 失败: {str(e)}")
    
    await auto_delete(msg, DELETE_DELAY)

# 删除文件命令
@listener(
    command="git_d",
    description="删除仓库文件",
    parameters="<仓库名> <文件路径> [提交信息]"
)
async def git_rm(message):
    token = get_github_token()
    if not token:
        msg = await message.edit("❌ 未设置Token")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    args = message.arguments.split(maxsplit=2)
    if len(args) < 2:
        msg = await message.edit("❌ 格式: <仓库名> <文件路径> [提交信息]")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    repo = args[0]
    path = args[1]
    commit_message = args[2] if len(args) > 2 else f"删除 {os.path.basename(path)}"
    
    default_branch = get_repo_default_branch(token, repo)
    msg = await message.edit(f"🗑️ 删除中... (分支: {default_branch})")
    
    try:
        result = delete_github_file(token, repo, path, commit_message)
        if result.get("commit"):
            msg = await message.edit(f"✅ 删除成功!\n\n路径: `{path}`\n分支: `{default_branch}`")
        else:
            error = result.get("message", "未知错误")
            msg = await message.edit(f"❌ 失败: {error}")
    
    except Exception as e:
        msg = await message.edit(f"❌ 失败: {str(e)}")
    
    await auto_delete(msg, DELETE_DELAY)

# 下载文件命令
@listener(
    command="git_dl",
    description="下载仓库文件",
    parameters="<仓库名> <文件路径>"
)
async def git_download(message):
    token = get_github_token()
    args = message.arguments.split(maxsplit=1)
    
    if len(args) < 2:
        msg = await message.edit("❌ 格式: <仓库名> <文件路径>")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    repo = args[0]
    path = args[1]
    
    default_branch = get_repo_default_branch(token, repo)
    msg = await message.edit(f"⬇️ 下载中... (分支: {default_branch})")
    
    try:
        file_content = download_github_file(token, repo, path)
        if not file_content:
            msg = await message.edit("❌ 下载失败")
            await auto_delete(msg, DELETE_DELAY)
            return
        
        filename = os.path.basename(path)
        
        with open(filename, "wb") as f:
            f.write(file_content)
        
        # 发送文件并保留（不自动删除）
        await message.reply(file=filename)
        
        # 删除原始消息和临时文件
        await message.delete()
        os.remove(filename)
    
    except Exception as e:
        msg = await message.edit(f"❌ 失败: {str(e)}")
        await auto_delete(msg, DELETE_DELAY)

# 获取raw地址命令
@listener(
    command="git_raw",
    description="获取Raw地址",
    parameters="<仓库名> <文件路径>"
)
async def git_raw(message):
    args = message.arguments.split(maxsplit=1)
    
    if len(args) < 2:
        msg = await message.edit("❌ 格式: <仓库名> <文件路径>")
        await auto_delete(msg, DELETE_DELAY)
        return
    
    repo = args[0]
    path = args[1]
    
    token = get_github_token()
    default_branch = get_repo_default_branch(token, repo) if token else "main"
    raw_url = get_raw_url(repo, path)
    
    msg = await message.edit(f"🔗 **Raw地址**\n\n分支: `{default_branch}`\n\n{raw_url}\n\n[点击下载]({raw_url})", link_preview=True)
    await auto_delete(msg, DELETE_DELAY)

# 帮助命令
@listener(
    command="git_h",
    description="显示帮助信息"
)
async def git_help(message):
    help_text = """
📘 **GitHub仓库管理插件 - 简化命令版**

1. 设置GitHub Token
   `,git_t <token>`

2. 查看仓库列表
   `,git_r [refresh]`

3. 查看仓库内容
   `,git_l <仓库名> [路径]`

4. 上传文件到仓库
   回复文件消息并执行:
   `,git_u <仓库名> <路径> [提交信息]`

5. 删除仓库文件
   `,git_d <仓库名> <文件路径> [提交信息]`

6. 下载仓库文件
   `,git_dl <仓库名> <文件路径>`

7. 获取文件Raw地址
   `,git_raw <仓库名> <文件路径>`

8. 显示帮助
   `,git_h`

🕒 本消息将在30秒后自动删除
"""
    msg = await message.edit(help_text)
    await auto_delete(msg, HELP_DELAY)

# 辅助函数：下载Telegram文件
async def download_telegram_file(message):
    if message.document:
        file_size = message.document.size
        if file_size > 10 * 1024 * 1024:  # 10MB限制
            return None
        try:
            return await message.download_media(bytes)
        except (FilePartMissingError, Exception):
            return None
    
    elif message.photo:
        try:
            return await message.download_media(bytes)
        except (FilePartMissingError, Exception):
            return None
    
    return None

# 自动删除消息函数
async def auto_delete(message, delay):
    """自动删除消息"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception as e:
        print(f"自动删除消息失败: {str(e)}")