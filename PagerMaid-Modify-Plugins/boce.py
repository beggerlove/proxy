# -*- coding: utf-8 -*-
# boce 域名 IP 解析插件（增强进度提示版）
# 支持 /bping <域名> 或 回复消息自动检测域名
# 支持单条消息中多个域名依次解析
# 作者: ChatGPT

import re
import os
import json
import aiohttp
import asyncio
from pagermaid.listener import listener
from pagermaid.utils import alias_command
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl

KEY_FILE = "boce_key.txt"
DEFAULT_NODES = "19,24,26"
POLL_INTERVAL = 2      # 秒
MAX_POLL = 15          # 最多轮询次数
ERROR_DELETE = 5       # 错误消息删除秒数
SUCCESS_DELETE = 30    # 正确消息删除秒数
MAX_DOMAINS = 10       # 单次最大解析域名数量

def save_key(key: str):
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(key.strip())

def load_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def extract_domains(text: str) -> list:
    """从文本中提取所有域名"""
    domains = set()
    
    # 匹配标准域名格式
    domain_pattern = r"\b((?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})\b"
    for match in re.finditer(domain_pattern, text):
        domains.add(match.group(1).lower())
    
    # 匹配带协议前缀的URL
    url_pattern = r"https?://([a-zA-Z0-9-]+\.[a-zA-Z]{2,})"
    for match in re.finditer(url_pattern, text):
        domains.add(match.group(1).lower())
    
    return list(domains)

async def delete_later(msg, delay):
    """延迟删除消息"""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except:
        pass

@listener(is_plugin=True, outgoing=True, command=alias_command("setbocekey"),
          description="设置 boce API Key", parameters="<key>")
async def set_boce_key(message):
    args = message.arguments
    if not args:
        temp = await message.edit("❌ 请输入要设置的 API Key。")
        await delete_later(temp, ERROR_DELETE)
        return
    save_key(args)
    temp = await message.edit("✅ boce API Key 已保存到本地。")
    await delete_later(temp, SUCCESS_DELETE)

async def resolve_domain(session, key, domain, progress_callback=None):
    """解析单个域名的核心函数"""
    create_url = f"https://api.boce.com/v3/task/create/ping?key={key}&node_ids={DEFAULT_NODES}&host={domain}"
    
    # 创建任务
    try:
        async with session.get(create_url) as resp:
            create_data = await resp.json()
    except Exception as e:
        return {"domain": domain, "error": f"创建任务失败: {str(e)}", "ips": []}

    if create_data.get("error_code") != 0:
        error_msg = create_data.get("error", "未知错误")
        return {"domain": domain, "error": f"创建任务失败: {error_msg}", "ips": []}

    task_id = create_data["data"]["id"]
    result_url = f"https://api.boce.com/v3/task/result/{task_id}?key={key}"
    ip_set = set()
    ip_list = []

    for i in range(MAX_POLL):
        await asyncio.sleep(POLL_INTERVAL)
        try:
            async with session.get(result_url) as resp:
                result_data = await resp.json()
        except Exception as e:
            return {"domain": domain, "error": f"获取结果失败: {str(e)}", "ips": []}

        # 更新进度回调
        if progress_callback:
            await progress_callback(i+1, MAX_POLL, domain)
            
        if result_data.get("done", False):
            nodes = result_data.get("list", [])
            for node in nodes:
                ip = node.get("ip")
                isp_raw = node.get("isp") or node.get("node_name") or ""
                isp = None
                for op in ["移动", "电信", "联通"]:
                    if op in isp_raw:
                        isp = op
                        break
                if not isp:
                    isp = "未知"
                if ip and ip not in ip_set:
                    ip_set.add(ip)
                    ip_list.append(f"{ip} ({isp})")
            break

    if not ip_list:
        return {"domain": domain, "error": "任务完成但未获取到任何IP", "ips": []}
    
    return {"domain": domain, "error": None, "ips": ip_list}

@listener(is_plugin=True, outgoing=True, command=alias_command("bping"),
          description="解析域名 IP", parameters="<domain>")
async def boce_ping(message):
    key = load_key()
    if not key:
        temp = await message.edit("❌ 请先使用 `/setbocekey` 设置 boce API Key。")
        await delete_later(temp, ERROR_DELETE)
        return

    domains = []
    reply_msg = await message.get_reply_message()
    
    # 情况1: 回复消息中检测域名
    if reply_msg:
        # 获取回复消息的文本内容
        text = reply_msg.text or reply_msg.raw_text or ""
        domains = extract_domains(text)
        
        # 检查消息中的URL实体
        if not domains and reply_msg.entities:
            for entity in reply_msg.entities:
                if isinstance(entity, (MessageEntityUrl, MessageEntityTextUrl)):
                    url = entity.url if hasattr(entity, 'url') else text[entity.offset:entity.offset+entity.length]
                    found_domains = extract_domains(url)
                    if found_domains:
                        domains.extend(found_domains)
    
    # 情况2: 从命令参数中提取域名
    if not domains and message.arguments:
        domains = extract_domains(message.arguments)
    
    # 去重并限制最大数量
    domains = list(set(domains))[:MAX_DOMAINS]
    total_domains = len(domains)
    
    # 情况3: 没有找到域名
    if not domains:
        temp = await message.edit("❌ 未找到有效的域名，请确保回复的消息中包含域名或在命令后指定域名。")
        await delete_later(temp, ERROR_DELETE)
        return

    # 显示解析开始消息
    if total_domains > 1:
        temp = await message.edit(f"🔍 开始解析 {total_domains} 个域名: {', '.join(domains)}")
    else:
        temp = await message.edit(f"🔍 正在解析域名: `{domains[0]}`")
    
    # 创建进度更新函数
    async def update_progress(current, total, domain):
        """更新进度回调函数"""
        if total_domains > 1:
            # 计算当前域名索引
            domain_index = domains.index(domain) + 1
            progress = f"⏳ 解析进度: {domain_index}/{total_domains} (域名: {domain})\n"
            progress += f"轮询中: {current}/{MAX_POLL}"
        else:
            progress = f"⏳ 正在获取解析结果 ({current}/{MAX_POLL})"
        await temp.edit(progress)

    # 创建HTTP会话
    async with aiohttp.ClientSession() as session:
        results = []
        
        # 依次解析每个域名
        for index, domain in enumerate(domains, 1):
            # 更新当前域名状态
            if total_domains > 1:
                await temp.edit(f"⏳ 开始解析第 {index}/{total_domains} 个域名: {domain}")
            
            result = await resolve_domain(session, key, domain, update_progress)
            results.append(result)
            
            # 更新完成状态
            if result['error']:
                status = f"❌ 解析失败: {result['error']}"
            elif result['ips']:
                status = f"✅ 解析成功: {len(result['ips'])} 个IP"
            else:
                status = "⚠️ 未获取到解析结果"
            
            if total_domains > 1:
                await temp.edit(f"⏳ 完成解析第 {index}/{total_domains} 个域名: {domain}\n{status}")
                await asyncio.sleep(1)  # 短暂显示完成状态
        
        # 构建结果消息
        result_message = "🌐 域名解析结果汇总:\n\n"
        for result in results:
            result_message += f"• **{result['domain']}**:\n"
            if result['error']:
                result_message += f"  ❌ {result['error']}\n"
            elif result['ips']:
                for ip in result['ips']:
                    result_message += f"  - {ip}\n"
            else:
                result_message += "  ⚠️ 未获取到解析结果\n"
            result_message += "\n"
        
        # 添加统计信息
        success_count = sum(1 for r in results if r['ips'])
        error_count = total_domains - success_count
        result_message += f"✅ 成功解析: {success_count} 个域名\n"
        result_message += f"❌ 解析失败: {error_count} 个域名"
        
        # 发送结果并设置自动删除
        temp2 = await temp.edit(result_message)
        await delete_later(temp2, SUCCESS_DELETE)

@listener(is_plugin=True, outgoing=True, command=alias_command("bocehelp"),
          description="显示 boce 插件帮助")
async def boce_help(message):
    help_text = (
        "📖 **boce 插件使用方法**\n\n"
        "1. 设置 API Key:\n"
        "   /setbocekey <你的APIKey>\n\n"
        "2. 解析域名 IP:\n"
        "   • 直接使用: /bping <域名>\n"
        "   • 回复包含域名的消息: /bping (无需参数)\n"
        "   • 支持单条消息中多个域名自动解析\n\n"
        "增强功能:\n"
        f"- 一次最多解析 {MAX_DOMAINS} 个域名\n"
        "- 实时显示解析进度 (当前域名/总数)\n"
        "- 显示每个域名的轮询状态\n"
        "- 结果汇总统计\n\n"
        "注意：\n"
        "- 输出结果仅显示 IP 和运营商（移动/电信/联通）\n"
        "- 错误消息 5 秒后删除，正确输出 30 秒后删除。"
    )
    temp = await message.edit(help_text)
    await delete_later(temp, SUCCESS_DELETE)