# -*- coding: utf-8 -*-
"""
插件名称: 回复转发到收藏
功能: 回复消息并输入 -r，将消息转发到“我的收藏”
"""

from pagermaid.listener import listener

# 收藏聊天目标，Telegram 私人收藏可以用 "me"
FAVORITE_CHAT_ID = "me"

@listener(
    is_plugin=True,
    outgoing=True,
    command="r",
    description="回复任意消息并输入 -r，将其转发到我的收藏。",
    parameters=""
)
async def reply_forward_to_fav(context):
    if not context.reply_to_msg_id:
        await context.edit("请先回复一条消息再使用 `-r`。")
        return

    try:
        reply_msg = await context.get_reply_message()
        # 转发到“我的收藏”
        await reply_msg.forward_to(FAVORITE_CHAT_ID)
        # 删除你发的 -r
        await context.delete()
    except Exception as e:
        await context.edit(f"转发失败：{e}")
