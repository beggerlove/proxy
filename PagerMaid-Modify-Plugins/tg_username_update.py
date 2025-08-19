#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Module to automate username update. """

import traceback
import asyncio
from datetime import datetime, timedelta, timezone

from pagermaid.dependence import scheduler
from pagermaid.services import bot
from pagermaid.utils import pip_install, logs
from telethon import functions

pip_install("emoji")

from emoji import emojize


auto_change_name_init = False

@scheduler.scheduled_job(
    "cron",
    second="0,30",
    id="autochangename",
    coalesce=True,
    max_instances=1,
    misfire_grace_time=15,
)
async def change_name_auto():
    try:
        # 获取北京时间 (UTC+8)
        now = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
        hour = now.hour
        minute = now.minute
        
        # 确定时间段描述和表情符号
        if 0 <= hour < 6:
            time_desc = "凌晨"
            emoji = emojize(":crescent_moon:", language="alias")  # 🌛
        elif 6 <= hour < 12:
            time_desc = "上午"
            emoji = emojize(":sun:", language="alias")  # 🌞
        elif 12 <= hour < 18:
            time_desc = "下午"
            emoji = emojize(":sun:", language="alias")  # 🌞
        else:  # 18-23
            time_desc = "晚上"
            emoji = emojize(":crescent_moon:", language="alias")  # 🌛
        
        # 格式化时间 (小时:分钟)
        time_str = f"{hour:02d}:{minute:02d}"
        
        # 创建新的last_name
        _last_name = f"{time_desc} {time_str} {emoji}"
        
        # 使用 Telethon 的 UpdateProfileRequest 更新用户名
        await bot(functions.account.UpdateProfileRequest(last_name=_last_name))
        
        # 尝试验证更新
        try:
            me = await bot.get_me()
            if getattr(me, "last_name", None) != _last_name:
                if logs and hasattr(logs, "info") and callable(getattr(logs, "info", None)):
                    logs.info("last_name 更新已提交，可能存在轻微延迟")
                else:
                    print("last_name 更新已提交，可能存在轻微延迟", flush=True)
        except Exception:
            pass  # 忽略验证错误
        
        # 记录更新日志
        try:
            if logs and hasattr(logs, 'info') and callable(getattr(logs, 'info', None)):
                logs.info(f"用户名已更新: {_last_name}")
            else:
                print(f"用户名已更新: {_last_name}", flush=True)
        except Exception as log_error:
            print(f"日志记录失败: {log_error}", flush=True)
            print(f"用户名已更新: {_last_name}", flush=True)
            
    except Exception as e:
        if isinstance(e, asyncio.CancelledError):
            return  # 关停中被取消，静默退出
        
        trac = "\n".join(traceback.format_exception(e))
        try:
            if logs and hasattr(logs, 'info') and callable(getattr(logs, 'info', None)):
                logs.info(f"更新失败! \n{trac}")
            else:
                print(f"更新失败! \n{trac}", flush=True)
        except Exception as log_error:
            print(f"错误日志记录失败: {log_error}", flush=True)
            print(f"更新失败! \n{trac}", flush=True)