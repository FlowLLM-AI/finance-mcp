#!/bin/bash

# 定义切分文件的前缀
TARGET_DIR="tool_cache"
INPUT_PREFIX="extract_ths_tool_cache/tool_cache.tar.gz.part_"

# 检查是否有分卷文件
if ! ls ${INPUT_PREFIX}* 1> /dev/null 2>&1; then
    echo "错误：未发现分卷文件 ${INPUT_PREFIX}*"
    exit 1
fi

echo "正在合并并解压文件..."

# cat: 合并所有分卷
# tar -x: 解压
cat ${INPUT_PREFIX}* | tar -xzf -

echo "解压完成！文件夹 '$TARGET_DIR' 已还原。"