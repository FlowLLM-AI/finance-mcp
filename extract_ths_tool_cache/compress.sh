#!/bin/bash

# 定义目标文件夹和输出文件名前缀
TARGET_DIR="tool_cache"
OUTPUT_PREFIX="extract_ths_tool_cache/tool_cache.tar.gz.part_"
SIZE_LIMIT="50m"

echo "正在压缩并切分 $TARGET_DIR ..."

# tar -c: 创建
# -z: gzip压缩
# -f -: 将结果输出到标准输出流
# split -b: 按大小切分
# -: 从标准输入流读取
tar -czf - "$TARGET_DIR" --exclude='.DS_Store' | split -b $SIZE_LIMIT - "$OUTPUT_PREFIX"

echo "压缩完成！生成的切分文件如下："
ls -lh ${OUTPUT_PREFIX}*