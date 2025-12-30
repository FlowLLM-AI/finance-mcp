#!/usr/bin/env python3
"""
同步 progress 文件和缓存文件的 completed_codes。

功能：
1. 遍历 progress 目录中的所有进度文件
2. 对于每个进度文件，找到对应的缓存文件（可能有多个，如 _01.json, _02.json）
3. 加载所有缓存文件，提取所有的 code
4. 对比 progress 中的 completed_codes 和缓存文件中的 codes
5. 如果不一致，打印出来并更新 progress 文件
6. 删除 time_records
7. 统计每个工具的爬取进度
"""

import csv
import json
import os
import glob
import re
from pathlib import Path


def get_tool_name_from_progress(progress_file: str) -> str:
    """从 progress 文件名提取工具名称。
    
    例如: crawl_ths_bonus_progress.json -> crawl_ths_bonus
    """
    filename = os.path.basename(progress_file)
    # 去掉 _progress.json 后缀
    return filename.replace("_progress.json", "")


def find_cache_files(tool_name: str, cache_dir: str) -> list[str]:
    """找到工具对应的所有缓存文件。
    
    例如: crawl_ths_bonus -> [crawl_ths_bonus_01.json, crawl_ths_bonus_02.json, ...]
    """
    pattern = os.path.join(cache_dir, f"{tool_name}_*.json")
    cache_files = glob.glob(pattern)
    # 排序确保顺序一致
    return sorted(cache_files)


def load_cache_codes(cache_files: list[str]) -> set[str]:
    """从所有缓存文件中加载 codes。"""
    codes = set()
    for cache_file in cache_files:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                if "tool_args" in item and "code" in item["tool_args"]:
                    codes.add(item["tool_args"]["code"])
        except Exception as e:
            print(f"  [错误] 加载缓存文件失败 {cache_file}: {e}")
    return codes


def load_progress(progress_file: str) -> dict:
    """加载 progress 文件。"""
    with open(progress_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(progress_file: str, data: dict):
    """保存 progress 文件。"""
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_tool_name_from_cache(cache_file: str) -> str | None:
    """从缓存文件名提取工具名称。
    
    例如: crawl_ths_bonus_01.json -> crawl_ths_bonus
    """
    filename = os.path.basename(cache_file)
    # 去掉 _01.json, _02.json 等后缀
    match = re.match(r"(.+)_\d+\.json$", filename)
    if match:
        return match.group(1)
    return None


def find_all_tool_names(cache_dir: str) -> set[str]:
    """找到所有工具名称（从缓存文件中提取）。"""
    cache_files = glob.glob(os.path.join(cache_dir, "crawl_ths_*_*.json"))
    tool_names = set()
    for cache_file in cache_files:
        tool_name = get_tool_name_from_cache(cache_file)
        if tool_name:
            tool_names.add(tool_name)
    return tool_names


def load_all_stock_codes(csv_file: str) -> set[str]:
    """从 CSV 文件加载所有股票代码。"""
    codes = set()
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            codes.add(row["symbol"])
    return codes


def sync_progress_with_cache():
    """主函数：同步 progress 和 cache。"""
    # 配置路径
    base_dir = Path(__file__).parent.parent
    cache_dir = base_dir / "tool_cache"
    progress_dir = cache_dir / "progress"
    stock_csv = base_dir / "tushare_stock_basic_20251226104714.csv"
    
    print(f"缓存目录: {cache_dir}")
    print(f"进度目录: {progress_dir}")
    print(f"股票代码文件: {stock_csv}")
    print("=" * 80)
    
    # 加载所有股票代码
    all_stock_codes = load_all_stock_codes(str(stock_csv))
    total_stocks = len(all_stock_codes)
    print(f"总股票代码数量: {total_stocks}")
    print("=" * 80)
    
    # 从缓存文件中找到所有工具名称
    all_tool_names = find_all_tool_names(str(cache_dir))
    print(f"发现 {len(all_tool_names)} 个工具: {sorted(all_tool_names)}")
    
    total_updated = 0
    total_created = 0
    
    # 统计信息
    stats = []
    
    for tool_name in sorted(all_tool_names):
        print(f"\n处理工具: {tool_name}")
        
        # 找到对应的缓存文件
        cache_files = find_cache_files(tool_name, str(cache_dir))
        
        if not cache_files:
            print(f"  [警告] 没有找到对应的缓存文件，跳过")
            stats.append({
                "tool_name": tool_name,
                "completed": 0,
                "remaining": total_stocks,
                "progress": 0.0
            })
            continue
        
        print(f"  缓存文件: {[os.path.basename(f) for f in cache_files]}")
        
        # 加载缓存中的 codes
        cache_codes = load_cache_codes(cache_files)
        print(f"  缓存中的 codes 数量: {len(cache_codes)}")
        
        # 检查进度文件是否存在
        progress_file = str(progress_dir / f"{tool_name}_progress.json")
        progress_exists = os.path.exists(progress_file)
        
        if progress_exists:
            print(f"  进度文件: {os.path.basename(progress_file)}")
            # 加载 progress
            progress_data = load_progress(progress_file)
            progress_codes = set(progress_data.get("completed_codes", []))
            print(f"  进度中的 completed_codes 数量: {len(progress_codes)}")
            
            # 检查是否有 time_records
            has_time_records = "time_records" in progress_data
            if has_time_records:
                print(f"  进度中存在 time_records，将被删除")
        else:
            print(f"  [新建] 进度文件不存在，将创建: {os.path.basename(progress_file)}")
            progress_codes = set()
            has_time_records = False
        
        # 对比差异
        only_in_progress = progress_codes - cache_codes
        only_in_cache = cache_codes - progress_codes
        
        if only_in_progress:
            print(f"  [不一致] 进度中有但缓存中没有的 codes ({len(only_in_progress)}个):")
            # 打印前10个
            sample = sorted(only_in_progress)[:10]
            print(f"    示例: {sample}")
            if len(only_in_progress) > 10:
                print(f"    ... 还有 {len(only_in_progress) - 10} 个")
        
        if only_in_cache:
            print(f"  [不一致] 缓存中有但进度中没有的 codes ({len(only_in_cache)}个):")
            # 打印前10个
            sample = sorted(only_in_cache)[:10]
            print(f"    示例: {sample}")
            if len(only_in_cache) > 10:
                print(f"    ... 还有 {len(only_in_cache) - 10} 个")
        
        # 判断是否需要更新
        needs_update = (only_in_progress or only_in_cache or has_time_records or not progress_exists)
        
        if needs_update:
            # 更新/创建 progress
            new_progress_data = {
                "completed_codes": sorted(list(cache_codes))
            }
            save_progress(progress_file, new_progress_data)
            if progress_exists:
                print(f"  [更新] 已更新进度文件，新的 completed_codes 数量: {len(cache_codes)}")
                total_updated += 1
            else:
                print(f"  [创建] 已创建进度文件，completed_codes 数量: {len(cache_codes)}")
                total_created += 1
        else:
            print(f"  [一致] 无需更新")
        
        # 统计爬取进度
        completed = len(cache_codes)
        remaining = total_stocks - completed
        progress_pct = (completed / total_stocks) * 100 if total_stocks > 0 else 0
        stats.append({
            "tool_name": tool_name,
            "completed": completed,
            "remaining": remaining,
            "progress": progress_pct
        })
    
    # 打印统计汇总
    print("\n" + "=" * 80)
    print(f"总计更新了 {total_updated} 个进度文件，创建了 {total_created} 个新进度文件")
    
    print("\n" + "=" * 80)
    print("爬取进度统计（总股票数: {})".format(total_stocks))
    print("=" * 80)
    print(f"{'工具名称':<25} {'已完成':>10} {'剩余':>10} {'进度':>10}")
    print("-" * 60)
    
    incomplete_tools = []
    for stat in stats:
        status = "✓" if stat["remaining"] == 0 else ""
        print(f"{stat['tool_name']:<25} {stat['completed']:>10} {stat['remaining']:>10} {stat['progress']:>9.1f}% {status}")
        if stat["remaining"] > 0:
            incomplete_tools.append(stat)
    
    print("-" * 60)
    
    # 汇总未完成的工具
    if incomplete_tools:
        print(f"\n未完成的工具数量: {len(incomplete_tools)}/{len(stats)}")
        total_remaining = sum(t["remaining"] for t in incomplete_tools)
        print(f"总剩余爬取记录数: {total_remaining}")
        print("\n未完成工具详情:")
        for stat in sorted(incomplete_tools, key=lambda x: x["remaining"], reverse=True):
            print(f"  - {stat['tool_name']}: 剩余 {stat['remaining']} 条，已完成 {stat['progress']:.1f}%")
    else:
        print("\n所有工具均已爬取完成！")


if __name__ == "__main__":
    sync_progress_with_cache()
