#!/bin/bash

# 1. 定义变量
TARGET_DIR="tool_cache"
OUTPUT_DIR="extract_ths_tool_cache"
OUTPUT_PREFIX="${OUTPUT_DIR}/tool_cache.tar.gz.part_"
SIZE_LIMIT="50m"

# 确保输出目录存在
mkdir -p "$OUTPUT_DIR"

# 2. 检查目标文件夹是否存在
if [ ! -d "$TARGET_DIR" ]; then
    echo "错误：未发现目标文件夹 '$TARGET_DIR'"
    exit 1
fi

echo "正在压缩并切分 $TARGET_DIR (已过滤 macOS 冗余文件) ..."

# 3. 清理旧的分卷文件，防止新旧文件混淆
rm -f ${OUTPUT_PREFIX}*

# 4. 执行核心压缩与切分
# COPYFILE_DISABLE=1: 禁止 macOS tar 产生新的 AppleDouble (._) 文件
# --exclude='._*': 显式排除磁盘上已有的 ._ 开头的元数据文件
# --exclude='.DS_Store': 排除文件夹索引文件
COPYFILE_DISABLE=1 tar -czf - \
    --exclude='._*' \
    --exclude='.DS_Store' \
    --exclude='__MACOSX' \
    "$TARGET_DIR" | split -b $SIZE_LIMIT - "$OUTPUT_PREFIX"

# 5. 验证结果
if [ $? -eq 0 ]; then
    echo "压缩完成！生成的切分文件如下："
    ls -lh ${OUTPUT_PREFIX}*
else
    echo "错误：压缩过程中出现问题。"
    exit 1
fi