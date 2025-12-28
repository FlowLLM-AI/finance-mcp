"""清理无效爬取结果脚本

该脚本用于清理 tool_cache 目录中 tool_result 为 "No relevant content found matching the query." 的条目，
并同步删除 progress 目录中相应的进度记录。
"""

import json
import os
from loguru import logger

# 配置
BASE_CACHE_DIR = "tool_cache"
PROGRESS_DIR = os.path.join(BASE_CACHE_DIR, "progress")
INVALID_RESULT = "No relevant content found matching the query."


def clean_cache_files():
    """清理 tool_cache 目录中的无效条目"""
    
    # 统计信息
    total_removed = 0
    removed_codes_by_tool = {}  # {tool_name: set(codes)}
    
    # 遍历 tool_cache 目录下的所有 JSON 文件（不包括 progress 子目录）
    for filename in os.listdir(BASE_CACHE_DIR):
        file_path = os.path.join(BASE_CACHE_DIR, filename)
        
        # 跳过目录和非 JSON 文件
        if os.path.isdir(file_path) or not filename.endswith(".json"):
            continue
        
        logger.info(f"处理文件: {filename}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"读取文件失败 {filename}: {e}")
            continue
        
        if not isinstance(data, list):
            logger.warning(f"文件格式不正确，跳过: {filename}")
            continue
        
        # 过滤无效条目
        original_count = len(data)
        valid_records = []
        removed_codes = set()
        
        for record in data:
            tool_result = record.get("tool_result", "")
            if tool_result == INVALID_RESULT:
                # 记录被移除的 code
                tool_args = record.get("tool_args", {})
                code = tool_args.get("code", "")
                tool_name = record.get("tool_name", "")
                if code:
                    removed_codes.add(code)
                    if tool_name not in removed_codes_by_tool:
                        removed_codes_by_tool[tool_name] = set()
                    removed_codes_by_tool[tool_name].add(code)
                logger.debug(f"  移除无效条目: tool={tool_name}, code={code}")
            else:
                valid_records.append(record)
        
        removed_count = original_count - len(valid_records)
        total_removed += removed_count
        
        if removed_count > 0:
            # 保存清理后的文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(valid_records, f, ensure_ascii=False, indent=2)
            logger.info(f"  清理完成: 移除 {removed_count} 条，剩余 {len(valid_records)} 条")
        else:
            logger.info(f"  无需清理: 共 {original_count} 条，均有效")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"缓存文件清理完成，共移除 {total_removed} 条无效记录")
    
    return removed_codes_by_tool


def clean_progress_files(removed_codes_by_tool: dict):
    """清理 progress 目录中的相应条目"""
    
    if not os.path.exists(PROGRESS_DIR):
        logger.warning(f"进度目录不存在: {PROGRESS_DIR}")
        return
    
    total_removed = 0
    
    for tool_name, codes_to_remove in removed_codes_by_tool.items():
        progress_file = os.path.join(PROGRESS_DIR, f"{tool_name}_progress.json")
        
        if not os.path.exists(progress_file):
            logger.warning(f"进度文件不存在: {progress_file}")
            continue
        
        logger.info(f"处理进度文件: {tool_name}_progress.json")
        
        try:
            with open(progress_file, "r", encoding="utf-8") as f:
                progress_data = json.load(f)
        except Exception as e:
            logger.error(f"读取进度文件失败 {progress_file}: {e}")
            continue
        
        completed_codes = set(progress_data.get("completed_codes", []))
        time_records = progress_data.get("time_records", {})
        
        original_count = len(completed_codes)
        
        # 移除无效的 codes
        for code in codes_to_remove:
            if code in completed_codes:
                completed_codes.remove(code)
            if code in time_records:
                del time_records[code]
        
        removed_count = original_count - len(completed_codes)
        total_removed += removed_count
        
        if removed_count > 0:
            # 保存更新后的进度文件
            progress_data["completed_codes"] = list(completed_codes)
            progress_data["time_records"] = time_records
            
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
            logger.info(f"  清理完成: 移除 {removed_count} 条，剩余 {len(completed_codes)} 条")
        else:
            logger.info(f"  无需清理")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"进度文件清理完成，共移除 {total_removed} 条记录")


def main():
    """主函数"""
    logger.info("="*60)
    logger.info("开始清理无效爬取结果...")
    logger.info(f"缓存目录: {BASE_CACHE_DIR}")
    logger.info(f"进度目录: {PROGRESS_DIR}")
    logger.info(f"无效结果标识: {INVALID_RESULT}")
    logger.info("="*60 + "\n")
    
    # 第一步：清理缓存文件
    logger.info("【第一步】清理缓存文件中的无效条目...")
    removed_codes_by_tool = clean_cache_files()
    
    # 第二步：清理进度文件
    logger.info("\n【第二步】清理进度文件中的相应条目...")
    clean_progress_files(removed_codes_by_tool)
    
    logger.info("\n" + "="*60)
    logger.info("✓ 所有清理任务完成!")
    logger.info("="*60)
    
    # 打印汇总
    if removed_codes_by_tool:
        logger.info("\n清理汇总:")
        for tool_name, codes in removed_codes_by_tool.items():
            logger.info(f"  {tool_name}: 移除 {len(codes)} 个股票代码")


if __name__ == "__main__":
    main()
