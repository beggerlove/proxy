#!/bin/bash

# Git 提交历史清理脚本
# 使用 shell 命令直接操作，更可靠

echo "开始清理 Git 提交历史..."

# 检查是否在 Git 仓库中
if [ ! -d ".git" ]; then
    echo "错误: 当前目录不是 Git 仓库"
    exit 1
fi

# 获取当前分支
CURRENT_BRANCH=$(git branch --show-current)
if [ -z "$CURRENT_BRANCH" ]; then
    echo "错误: 无法获取当前分支"
    exit 1
fi

echo "当前分支: $CURRENT_BRANCH"

# 获取所有提交数量（包括所有分支）
COMMIT_COUNT=$(git rev-list --all --count)
if [ -z "$COMMIT_COUNT" ]; then
    echo "错误: 无法获取提交数量"
    exit 1
fi

echo "仓库总提交数量: $COMMIT_COUNT"

# 获取当前分支提交数量
CURRENT_BRANCH_COUNT=$(git rev-list --count HEAD)
echo "当前分支提交数量: $CURRENT_BRANCH_COUNT"

# 检查是否需要强制清理
FORCE_CLEAN=${FORCE_CLEAN:-false}
echo "强制清理模式: $FORCE_CLEAN"

# 如果只有1个提交且不是强制清理模式，则无需清理
if [ "$COMMIT_COUNT" -le 1 ] && [ "$FORCE_CLEAN" != "true" ]; then
    echo "提交历史已经是最新的，无需清理"
    echo "如需强制清理，请设置 FORCE_CLEAN=true"
    exit 0
fi

# 如果是强制清理模式，显示提示
if [ "$FORCE_CLEAN" = "true" ]; then
    echo "强制清理模式已启用，将执行清理操作"
fi

# 获取中国时间
CHINA_TIME=$(TZ='Asia/Shanghai' date '+%Y-%m-%d %H:%M:%S')

echo "开始清理过程..."

# 方法1: 完全重新初始化仓库
echo "尝试方法1: 完全重新初始化仓库..."

# 保存当前文件到临时目录
TEMP_DIR=$(mktemp -d)
echo "保存文件到临时目录: $TEMP_DIR"

# 复制所有文件（除了.git目录）
find . -maxdepth 1 -not -name '.' -not -name '.git' -exec cp -r {} "$TEMP_DIR/" \; 2>/dev/null || true

# 删除.git目录
rm -rf .git

# 重新初始化Git仓库
git init

# 配置Git用户信息
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# 恢复文件
echo "恢复文件..."
cp -r "$TEMP_DIR"/* . 2>/dev/null || true
rm -rf "$TEMP_DIR"

# 添加所有文件
git add -A

# 创建初始提交
if git commit -m "Initial commit - Cleaned history"; then
    echo "新提交创建成功"
    
    # 添加远程仓库（使用token认证）
    git remote add origin "https://x-access-token:${GITHUB_TOKEN}@github.com/beggerlove/proxy.git"
    
    # 强制推送到远程仓库
    if git push -f origin "$CURRENT_BRANCH"; then
        echo "✅ 清理完成！"
        
        # 发送 Telegram 通知
        if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
            MESSAGE="🧹 <b>Git 提交历史清理完成</b>

📅 清理时间: $CHINA_TIME (中国时间)
📊 清理前提交数: $COMMIT_COUNT 条
📊 清理后提交数: 1 条
🗑️ 删除提交: $((COMMIT_COUNT - 1)) 条
🔗 仓库: $CURRENT_BRANCH 分支
🛠️ 使用: 重新初始化方法"

            curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                -d "chat_id=$TELEGRAM_CHAT_ID" \
                -d "text=$MESSAGE" \
                -d "parse_mode=HTML"
            echo "Telegram 通知发送成功"
        fi
        
        exit 0
    else
        echo "错误: 推送失败"
    fi
else
    echo "错误: 创建新提交失败"
fi

echo "方法1失败，尝试方法2..."

# 方法2: 使用 git checkout --orphan
echo "尝试方法2: git checkout --orphan..."
if git checkout --orphan temp_branch; then
    echo "孤立分支创建成功"
    
    # 添加所有文件
    git add -A
    
    # 创建新提交
    if git commit -m "Initial commit - Cleaned history"; then
        echo "新提交创建成功"
        
        # 删除原分支
        git branch -D "$CURRENT_BRANCH"
        
        # 重命名分支
        git branch -m "$CURRENT_BRANCH"
        
        # 强制推送（使用token认证）
        if git push -f origin "$CURRENT_BRANCH"; then
            echo "✅ 清理完成！"
            
            # 发送 Telegram 通知
            if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
                MESSAGE="🧹 <b>Git 提交历史清理完成</b>

📅 清理时间: $CHINA_TIME (中国时间)
📊 清理前提交数: $COMMIT_COUNT 条
📊 清理后提交数: 1 条
🗑️ 删除提交: $((COMMIT_COUNT - 1)) 条
🔗 仓库: $CURRENT_BRANCH 分支
🛠️ 使用: orphan 方法"

                curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                    -d "chat_id=$TELEGRAM_CHAT_ID" \
                    -d "text=$MESSAGE" \
                    -d "parse_mode=HTML"
                echo "Telegram 通知发送成功"
            fi
            
            exit 0
        else
            echo "错误: 推送失败"
        fi
    else
        echo "错误: 创建新提交失败"
    fi
else
    echo "错误: 创建孤立分支失败"
fi

echo "❌ 所有方法都失败了"
exit 1 