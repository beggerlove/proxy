from urllib.parse import quote
import asyncio
import re
import json
from pagermaid.utils import alias_command, logs
from pagermaid.listener import listener
from pagermaid.services import sqlite
from pagermaid.enums import Client, Message, AsyncClient
from urllib.parse import urlencode
import datetime

cmd = alias_command('ssm')
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Content-Type": "application/json; charset=utf-8"
}

def flowTransfer(flow, unit='B'):
    unitList = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    unitIndex = unitList.index(unit)

    if flow < 1024:
        return {'value': format(flow, '.1f'), 'unit': unit}
    else:
        return flowTransfer(flow / 1024, unitList[unitIndex + 1])

def mask_url(string):
    result = ''
    index = 0
    while index < len(string):
        # 每隔7位替换接下来的3位为***
        result += string[index:index+7] + '***'
        index += 10
    return result

async def check_env(request, ssm_api):
    path = "/api/utils/env"
    url = f"{ssm_api}{path}"
    masked_url = f"{mask_url(ssm_api)}{path}"
    response = await request.get(url, headers=headers, timeout=5)
    if response.status_code != 200:
        raise Exception(f"请求 `{masked_url}` 异常: {response.status_code}")
    data = None
    try:
        data = response.json()
    except Exception:
        raise Exception(f"解析 `{masked_url}` 响应 JSON 出错")
    try:
        backend = data["data"]["backend"]
        version = data["data"]["version"]
        return backend, version
    except Exception:
        raise Exception(f"接口 `{masked_url}` 异常, 应正常返回 `backend` 和 `version` 字段 ")

async def fetchFlow(request, ssm_api, subName):
    encodedName = quote(subName)
    path = f"/api/sub/flow/{encodedName}"
    url = f"{ssm_api}{path}"
    masked_url = f"{mask_url(ssm_api)}{path}"
    response = await request.get(url, headers=headers, timeout=5)
    if response.status_code != 200:
        raise Exception(f"请求 `{masked_url}` 异常: {response.status_code}")
    data = None
    try:
        data = response.json()
    except Exception:
        raise Exception(f"解析 `{masked_url}` 响应 JSON 出错")
    try:
        data = data["data"]
        total = data["total"]
        return data
    except Exception:
        raise Exception(f"接口 `{masked_url}` 异常, 应正常返回 `total` 字段 ")

async def fetchSubs(request, ssm_api):
    path = "/api/subs"
    url = f"{ssm_api}{path}"
    masked_url = f"{mask_url(ssm_api)}{path}"
    response = await request.get(url, headers=headers, timeout=5)
    if response.status_code != 200:
        raise Exception(f"请求 `{masked_url}` 异常: {response.status_code}")
    data = None
    try:
        data = response.json()
    except Exception:
        raise Exception(f"解析 `{masked_url}` 响应 JSON 出错")
    try:
        data = data["data"]
        return data
    except Exception:
        raise Exception(f"接口 `{masked_url}` 异常, 应正常返回 `data` 字段 ")

async def fetchNodes(request, ssm_api, subName, type):
    encodedName = quote(subName)
    path = f"/download{'/collection' if type == 'collection' else '' }/{encodedName}?target=JSON&noCache=true"
    url = f"{ssm_api}{path}"
    masked_url = f"{mask_url(ssm_api)}{path}"
    response = await request.get(url, headers=headers, timeout=300)
    if response.status_code != 200:
        raise Exception(f"请求 `{masked_url}` 异常: {response.status_code}")
    data = None
    try:
        data = response.json()
    except Exception:
        raise Exception(f"解析 `{masked_url}` 响应 JSON 出错")
    if isinstance(data, list):
        return data
    else:
        raise Exception(f"接口 `{masked_url}` 异常, 应正常返回数组")

async def fetchCollections(request, ssm_api):
    path = "/api/collections"
    url = f"{ssm_api}{path}"
    masked_url = f"{mask_url(ssm_api)}{path}"
    response = await request.get(url, headers=headers, timeout=5)
    if response.status_code != 200:
        raise Exception(f"请求 `{masked_url}` 异常: {response.status_code}")
    data = None
    try:
        data = response.json()
    except Exception:
        raise Exception(f"解析 `{masked_url}` 响应 JSON 出错")
    try:
        data = data["data"]
        return data
    except Exception:
        raise Exception(f"接口 `{masked_url}` 异常, 应正常返回 `data` 字段 ")

def generate_sub_links(ssm_api, name, is_collection=False):
    """生成订阅链接"""
    encodedName = quote(name)
    base_url = f"{ssm_api}/download/{'collection/' if is_collection else ''}{encodedName}"
    
    formats = [
        {"name": "QX", "url": f"{base_url}?target=QX"},
        {"name": "Surge", "url": f"{base_url}?target=Surge"},
        {"name": "Loon", "url": f"{base_url}?target=Loon"},
        {"name": "ShadowRocket", "url": f"{base_url}?target=ShadowRocket"},
        {"name": "Stash", "url": f"{base_url}?target=Stash"},
        {"name": "ClashMeta", "url": f"{base_url}?target=ClashMeta"},
        {"name": "Clash", "url": f"{base_url}?target=Clash"},
        {"name": "V2Ray", "url": f"{base_url}?target=V2Ray"}
    ]
    
    sub_output = "订阅地址:\n"
    for fmt in formats:
        sub_output += f"- [{fmt['name']}]({fmt['url']}) `{fmt['url']}`\n"
    
    return sub_output

async def get_sub_flow_info(request, ssm_api, sub_name):
    """获取订阅的流量信息和到期时间"""
    try:
        flow_data = await fetchFlow(request, ssm_api, sub_name)
        
        expires = flow_data.get("expires")
        total = flow_data["total"]
        upload = flow_data["usage"]["upload"]
        download = flow_data["usage"]["download"]
        
        # 计算已用流量
        used = upload + download
        
        # 格式化已用流量和总流量
        usedT = flowTransfer(used)
        totalT = flowTransfer(total)
        
        # 格式化到期时间
        date = datetime.datetime.fromtimestamp(expires).strftime('%Y-%m-%d') if expires else '无'
        
        # 返回格式化后的流量信息和到期时间
        return f"{usedT['value']} {usedT['unit']} / {totalT['value']} {totalT['unit']}", date
    except Exception as e:
        logs.error(f"获取订阅 {sub_name} 流量信息失败: {e}")
        return "已用流量未知", "到期时间未知"

@listener(
    command="ssm",
    description="管理服务器版 Sub-Store",
    parameters=f"设置接口:\n,{cmd} api http://127.0.0.1:3000\n\n查看已设置接口: ,{cmd} api\n\n查看单条订阅列表: ,{cmd} subs\n\n查看单条订阅: ,{cmd} sub 1(为方便小白 从 1 开始, 与 subs 列表对应)\n\n查看组合订阅列表: ,{cmd} collections\n\n查看组合订阅: ,{cmd} collection 1(为方便小白 从 1 开始, 与 collections 列表对应)\n\n自动删除消息: ,{cmd} auto_del True\n\n显示订阅链接: ,{cmd} show_links True\n\n",
)
async def ssm(client: Client, message: Message, request: AsyncClient):
    info = None
    auto_del = sqlite.get('ssm_auto_del', False)
    show_links = sqlite.get('ssm_show_links', 'False')  # 默认为不显示链接

    try:
        if len(message.parameter) > 0:
            if message.parameter[0] == "api":
                if len(message.parameter) == 1:
                    ssm_api = sqlite.get('ssm_api', "")
                    ssm_api_msg = await message.edit(f"当前已设置接口: `{mask_url(ssm_api)}`" if ssm_api else "未设置接口")
                    if ssm_api:
                        try:
                            backend, version = await check_env(request, ssm_api)
                            await ssm_api_msg.edit(f"当前已设置接口: `{mask_url(ssm_api)}`\n接口信息: `{backend}` `{version}`")
                        except Exception as e:
                            await ssm_api_msg.edit(f"接口验证失败: {str(e)}")
                    await asyncio.sleep(30)
                    await ssm_api_msg.safe_delete()
                    await message.safe_delete()
                    return
                else:
                    ssm_api = " ".join(message.parameter[1:])
                    if not re.match(r'^https?:\/\/', ssm_api):
                        raise Exception(f"接口 `{mask_url(ssm_api)}` 不合法")
                    try:
                        backend, version = await check_env(request, ssm_api)
                        sqlite["ssm_api"] = ssm_api
                        ssm_api_msg = await message.edit(f"接口设置成功: `{mask_url(ssm_api)}`\n接口信息: `{backend}` `{version}`")
                    except Exception as e:
                        await message.edit(f"接口验证失败: {str(e)}")
                        return
                    await asyncio.sleep(30)
                    await ssm_api_msg.safe_delete()
                    await message.safe_delete()
                    return
            elif message.parameter[0] == "subs":
                ssm_api = sqlite.get('ssm_api', "")
                if not ssm_api:
                    raise Exception("请先设置接口")
                
                try:
                    backend, version = await check_env(request, ssm_api)
                    subs = await fetchSubs(request, ssm_api)

                    # 获取所有订阅的流量信息
                    flow_tasks = []
                    for sub in subs:
                        flow_tasks.append(get_sub_flow_info(request, ssm_api, sub['name']))
                    
                    flow_results = await asyncio.gather(*flow_tasks, return_exceptions=True)

                    output = f"单条订阅({len(subs)}):\n\n"
                    max_index = len(str(len(subs)))  # 找到序号的最大位数
                    max_name_length = max(len(sub.get('displayName', sub['name'])) for sub in subs) if subs else 0

                    for index, sub in enumerate(subs, start=1):
                        flow_info = flow_results[index-1]
                        
                        if isinstance(flow_info, Exception):
                            flow_text = "已用流量未知"
                            expire_text = "到期时间未知"
                        else:
                            flow_text, expire_text = flow_info
                        
                        name = sub.get('displayName') or sub['name']
                        # 对齐显示名称
                        padded_name = name.ljust(max_name_length + 2)
                        
                        # 使用新的流量格式
                        output += f"`{str(index).zfill(max_index)}` {padded_name} 已用/总流量: {flow_text}\n到期时间: {expire_text}\n"

                    ssm_msg = await message.edit(f"{output}")
                    if auto_del == 'True':
                        await asyncio.sleep(30)
                        await ssm_msg.safe_delete()
                        await message.safe_delete()
                except Exception as e:
                    await message.edit(f"获取订阅列表失败: {str(e)}")

            elif message.parameter[0] == "collections":
                ssm_api = sqlite.get('ssm_api', "")
                if not ssm_api:
                    raise Exception("请先设置接口")
                
                try:
                    backend, version = await check_env(request, ssm_api)
                    collections = await fetchCollections(request, ssm_api)

                    output = "组合订阅({}):\n\n".format(len(collections))
                    max_index = len(str(len(collections)))  # 找到序号的最大位数

                    for index, collection in enumerate(collections, start=1):
                        if "displayName" in collection and collection["displayName"]:
                            output += "`{0}` {1}\n".format(str(index).zfill(max_index), collection["displayName"])
                        else:
                            output += "`{0}` {1}\n".format(str(index).zfill(max_index), collection["name"])

                    ssm_msg = await message.edit(f"{output}")
                    if auto_del == 'True':
                        await asyncio.sleep(30)
                        await ssm_msg.safe_delete()
                        await message.safe_delete()
                except Exception as e:
                    await message.edit(f"获取组合订阅列表失败: {str(e)}")
                    
            elif message.parameter[0] == "sub":
                if len(message.parameter) != 2:
                    raise Exception("请提供单条订阅序号")
                
                ssm_api = sqlite.get('ssm_api', "")
                if not ssm_api:
                    raise Exception("请先设置接口")
                
                try:
                    backend, version = await check_env(request, ssm_api)
                    subs = await fetchSubs(request, ssm_api)
                    sub_index = int(message.parameter[1]) - 1
                    
                    if sub_index < 0 or sub_index >= len(subs):
                        raise Exception("订阅序号超出范围")
                    
                    sub = subs[sub_index]

                    # 获取节点信息
                    try:
                        nodesData = await fetchNodes(request, ssm_api, sub['name'], 'sub')
                        nodes = "节点({}):\n\n".format(len(nodesData))
                        max_index = len(str(len(nodesData)))
                        
                        for i, node in enumerate(nodesData, start=1):
                            index = str(i).zfill(max_index)
                            nodes += "`{}` [{}] {}\n".format(index, node["type"], node["name"])
                    except Exception as e:
                        logs.error(e)
                        nodes = "未获取到节点信息\n错误: " + str(e)

                    # 获取流量信息
                    flow = ""
                    try:
                        flowData = await fetchFlow(request, ssm_api, sub['name'])
                        expires = flowData.get("expires")
                        total = flowData["total"]
                        upload = flowData["usage"]["upload"]
                        download = flowData["usage"]["download"]

                        date = datetime.datetime.fromtimestamp(expires).strftime('%Y-%m-%d') if expires else '无'
                        current = upload + download

                        currT = flowTransfer(abs(current))
                        currT['value'] = '-' + currT['value'] if current < 0 else currT['value']
                        totalT = flowTransfer(total)

                        flow = f"`已用/总流量` {currT['value']} {currT['unit']} / {totalT['value']} {totalT['unit']}\n`到期时间` {date}"
                    except Exception as e:
                        logs.error(e)
                        flow = "未获取到流量信息\n错误: " + str(e)

                    # 构建消息
                    message_text = (
                        f"单条订阅 {sub['displayName'] if 'displayName' in sub and sub['displayName'] else sub['name']}\n\n"
                        f"{flow}\n\n"
                        f"{nodes}"
                    )
                    
                    # 如果启用了显示链接，则添加订阅链接
                    if show_links == 'True':
                        links = generate_sub_links(ssm_api, sub['name'], is_collection=False)
                        message_text += f"\n\n{links}"
                    
                    ssm_msg = await message.edit(message_text)
                    
                    if auto_del == 'True':
                        await asyncio.sleep(30)
                        await ssm_msg.safe_delete()
                        await message.safe_delete()
                except Exception as e:
                    raise Exception(f"查看单条订阅失败: {str(e)}")
                    
            elif message.parameter[0] == "collection":
                if len(message.parameter) != 2:
                    raise Exception("请提供组合订阅序号")
                
                ssm_api = sqlite.get('ssm_api', "")
                if not ssm_api:
                    raise Exception("请先设置接口")
                
                try:
                    backend, version = await check_env(request, ssm_api)
                    collections = await fetchCollections(request, ssm_api)
                    collection_index = int(message.parameter[1]) - 1
                    
                    if collection_index < 0 or collection_index >= len(collections):
                        raise Exception("组合订阅序号超出范围")
                    
                    collection = collections[collection_index]

                    # 获取节点信息
                    try:
                        nodesData = await fetchNodes(request, ssm_api, collection['name'], 'collection')
                        nodes = "节点({}):\n\n".format(len(nodesData))
                        max_index = len(str(len(nodesData)))
                        
                        for i, node in enumerate(nodesData, start=1):
                            index = str(i).zfill(max_index)
                            nodes += "`{}` [{}] {}\n".format(index, node["type"], node["name"])
                    except Exception as e:
                        logs.error(e)
                        nodes = "未获取到节点信息\n错误: " + str(e)

                    # 构建消息
                    message_text = (
                        f"组合订阅 {collection['displayName'] if 'displayName' in collection and collection['displayName'] else collection['name']}\n\n"
                        f"{nodes}"
                    )
                    
                    # 如果启用了显示链接，则添加订阅链接
                    if show_links == 'True':
                        links = generate_sub_links(ssm_api, collection['name'], is_collection=True)
                        message_text += f"\n\n{links}"
                    
                    ssm_msg = await message.edit(message_text)
                    
                    if auto_del == 'True':
                        await asyncio.sleep(30)
                        await ssm_msg.safe_delete()
                        await message.safe_delete()
                except Exception as e:
                    raise Exception(f"查看组合订阅失败: {str(e)}")
                    
            elif message.parameter[0] == "auto_del":
                if len(message.parameter) < 2:
                    raise Exception("请提供设置值 (True/False)")
                
                setting = message.parameter[1].strip()
                if setting not in ['True', 'False']:
                    raise Exception("值必须是 True 或 False")
                
                sqlite["ssm_auto_del"] = setting
                m = await message.edit(f"已设置自动删除: `{setting}`")
                await asyncio.sleep(5)
                await m.safe_delete()
                await message.safe_delete()
                return
                
            elif message.parameter[0] == "show_links":
                if len(message.parameter) < 2:
                    raise Exception("请提供设置值 (True/False)")
                
                setting = message.parameter[1].strip()
                if setting not in ['True', 'False']:
                    raise Exception("值必须是 True 或 False")
                
                sqlite["ssm_show_links"] = setting
                m = await message.edit(f"已设置显示订阅链接: `{setting}`")
                await asyncio.sleep(5)
                await m.safe_delete()
                await message.safe_delete()
                return

        ssm_api = sqlite.get('ssm_api', "")
        if not ssm_api:
            raise Exception("请先设置接口")
            
        if auto_del == 'True':
            await asyncio.sleep(30)
            await message.safe_delete()
            if info:
                await info.safe_delete()
    except Exception as e:
        logs.error(f"{e}")
        if info:
            await info.safe_delete()
        await message.safe_delete()
        m = await message.reply(f"错误\n\n{e}")
        await asyncio.sleep(30)
        await m.safe_delete()