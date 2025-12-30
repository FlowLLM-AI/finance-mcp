#!/bin/bash

# 1. 定义变量
TARGET_DIR="tool_cache"
INPUT_PATTERN="extract_ths_tool_cache/tool_cache.tar.gz.part_[a-z][a-z]"

# 2. 检查分卷是否存在
FILES=$(ls ${INPUT_PATTERN} 2>/dev/null)
if [ -z "$FILES" ]; then
    echo "错误：未发现符合命名规则的分卷文件 (aa, ab, ac...)"
    exit 1
fi

echo "正在合并并解压文件（过滤 macOS 冗余文件）..."

# 3. 执行解压
# --exclude='._*'：排除所有以 ._ 开头的元数据文件
# --exclude='.DS_Store'：排除 Mac 的文件夹索引文件
cat $(ls ${INPUT_PATTERN} | sort) | tar --warning=no-unknown-keyword --exclude='._*' --exclude='.DS_Store' -xzf -

# 4. 检查并进行二次清理
if [ -d "$TARGET_DIR" ]; then
    # 强制清理：以防有些特殊路径的隐藏文件没被 tar 过滤掉
    find "$TARGET_DIR" -name "._*" -delete
    find "$TARGET_DIR" -name ".DS_Store" -delete
    
    echo "解压完成！文件夹 '$TARGET_DIR' 已还原，垃圾文件已清理。"
else
    echo "错误：解压已运行，但在当前目录下未找到 '$TARGET_DIR'。"
fi