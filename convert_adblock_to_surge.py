import requests
import os
import re
from datetime import datetime
import pytz

# 配置变量（可通过环境变量覆盖）
ADBLOCK_URL = os.getenv('ADBLOCK_SOURCE_URL')
OUTPUT_DIR = "Rule"
OUTPUT_FILE = "Adblocker.list"
MY_URL = "https://raw.githubusercontent.com/beggerlove/proxy/master/Rule/Adblocker.list"

# Telegram Bot 配置（仅通过环境变量获取）
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def fetch_adblock_rules(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text.splitlines()

def extract_upstream_date(rules):
    """从上游规则中提取日期信息"""
    for line in rules:
        line = line.strip()
        if line.startswith('#!date='):
            # 提取日期信息，格式如 #!date=2025/06/29 08:36:36
            date_match = re.search(r'#!date=(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})', line)
            if date_match:
                # 将 YYYY/MM/DD HH:MM:SS 格式转换为 YYYY-MM-DD HH:MM:SS
                year, month, day, hour, minute, second = date_match.groups()
                return f"{year}-{month}-{day} {hour}:{minute}:{second}"
    return None

def send_telegram_notification(message):
    """发送 Telegram 通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram 配置未设置，跳过通知")
        return
        
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        print("Telegram 通知发送成功")
    except Exception as e:
        print(f"Telegram 通知发送失败: {e}")

def get_existing_rules_count():
    """获取现有规则数量"""
    try:
        file_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 计算规则行数（排除头部注释）
                lines = content.split('\n')
                rule_count = 0
                for line in lines:
                    if line.strip() and not line.startswith('#') and not line.startswith('!'):
                        rule_count += 1
                return rule_count
    except:
        pass
    return 0

def convert_and_save():
    rules = fetch_adblock_rules(ADBLOCK_URL)
    
    # 提取上游日期信息
    upstream_date = extract_upstream_date(rules)
    
    surge_rules = []
    
    for line in rules:
        line = line.strip()
        # 跳过空行和注释行
        if not line or line.startswith('#'):
            continue
        # 直接使用规则，因为它们已经是 Surge 格式
        surge_rules.append(line)
    
    # 获取现有规则数量
    old_rule_count = get_existing_rules_count()
    new_rule_count = len(surge_rules)
    added_rules = new_rule_count - old_rule_count
    
    # 获取中国时间
    china_tz = pytz.timezone('Asia/Shanghai')
    china_time = datetime.now(china_tz)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, OUTPUT_FILE), "w", encoding="utf-8") as f:
        # 添加文件信息头部
        f.write("#########################################\n")
        f.write("# 广告拦截规则列表\n")
        f.write("# 用于 Surge 等代理工具的广告拦截配置\n")
        f.write("# 自动同步更新，请勿手动修改\n")
        if upstream_date:
            f.write(f"# Upstream Date: {upstream_date}\n")
        f.write(f"# Local Sync: {china_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total Rules: {new_rule_count}\n")
        f.write(f"# Source: {ADBLOCK_URL}\n")
        f.write(f"# My URL: {MY_URL}\n")
        f.write("#########################################\n")
        for rule in surge_rules:
            f.write(rule + "\n")
    
    # 发送 Telegram 通知
    if added_rules >= 0:
        message = f"✅ <b>Surge 规则同步成功</b>\n\n"
        message += f"📅 更新时间: {china_time.strftime('%Y-%m-%d %H:%M:%S')} (中国时间)\n"
        message += f"📊 总规则数: {new_rule_count} 条\n"
        if added_rules > 0:
            message += f"🆕 新增规则: +{added_rules} 条\n"
        elif added_rules < 0:
            message += f"📉 减少规则: {added_rules} 条\n"
        else:
            message += f"🔄 规则数量无变化\n"
        message += f"🔗 源地址: {MY_URL}"
        
        send_telegram_notification(message)

if __name__ == "__main__":
    convert_and_save() 
