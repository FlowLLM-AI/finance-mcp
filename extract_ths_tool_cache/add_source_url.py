import json
from pathlib import Path
import re


def extract_tag_from_filename(filename: str) -> str:
    """从文件名中提取tag。
    
    文件名格式: crawl_ths_{tag}_{序号}.json
    例如: crawl_ths_company_02.json -> company
          crawl_ths_position_01.json -> position
    """
    pattern = r'crawl_ths_(.+?)_\d+\.json'
    match = re.match(pattern, filename)
    if match:
        return match.group(1)
    return ""


def add_source_url_to_records(tool_cache_dir: str):
    """遍历tool_cache目录下所有JSON文件，在每条记录的tool_result前添加来源URL。
    
    Args:
        tool_cache_dir: tool_cache目录的路径
    """
    cache_path = Path(tool_cache_dir)
    
    if not cache_path.exists():
        print(f"错误: 目录不存在 {tool_cache_dir}")
        return
    
    # 获取所有一级目录下的JSON文件
    json_files = list(cache_path.glob("*.json"))
    
    if not json_files:
        print(f"警告: 在 {tool_cache_dir} 下未找到JSON文件")
        return
    
    print(f"找到 {len(json_files)} 个JSON文件")
    
    for json_file in json_files:
        print(f"\n处理文件: {json_file.name}")
        
        # 从文件名中提取tag
        tag = extract_tag_from_filename(json_file.name)
        if not tag:
            print(f"  跳过: 无法从文件名 {json_file.name} 中提取tag")
            continue
        
        print(f"  提取的tag: {tag}")
        
        # 读取JSON文件
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  错误: 读取文件失败 - {e}")
            continue
        
        if not isinstance(data, list):
            print(f"  跳过: 文件内容不是列表格式")
            continue
        
        # 处理每条记录
        modified_count = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # 检查必要字段
            if 'tool_args' not in item or 'tool_result' not in item:
                continue
            
            tool_args = item['tool_args']
            if 'code' not in tool_args:
                continue
            
            code = tool_args['code']
            tool_result = item['tool_result']
            
            # 构造来源URL
            source_url = f"https://basic.10jqka.com.cn/{code}/{tag}.html#stockpage"
            source_prefix = f"> 以下内容来自：{source_url}\n\n"
            
            # 检查是否已经添加过来源信息
            if not tool_result.startswith("> 以下内容来自："):
                item['tool_result'] = source_prefix + tool_result
                modified_count += 1
        
        print(f"  修改了 {modified_count} 条记录")
        
        # 写回文件
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 成功保存文件")
        except Exception as e:
            print(f"  错误: 保存文件失败 - {e}")


def main():
    # 设置tool_cache目录路径
    tool_cache_dir = "/mnt/data_cpfs/taoshuchang.tsc/deepresearch/finance-mcp/tool_cache"
    
    print("开始处理tool_cache目录下的JSON文件...")
    print(f"目标目录: {tool_cache_dir}\n")
    
    add_source_url_to_records(tool_cache_dir)
    
    print("\n处理完成！")


if __name__ == "__main__":
    main()
