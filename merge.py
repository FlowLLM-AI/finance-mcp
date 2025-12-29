import os
import json
import shutil

# 配置路径（Python 字符串不需要反斜杠转义空格）
SRC_ROOT_BASE = "/Users/tsc/研究工作/金融ASIO/代码/finance-mcp_3"
DST_ROOT_BASE = "/Users/tsc/研究工作/金融ASIO/代码/finance-mcp"

# 需要合并的根文件夹
TARGET_FOLDERS = ["tool_cache", "cache"]

def load_json_data(file_path):
    """加载 JSON 数据，支持列表或单个对象"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
    except Exception as e:
        print(f"  [跳过] 无法解析 JSON: {file_path}. 错误: {e}")
        return None

def save_json_data(file_path, data):
    """保存 JSON 数据"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_code(sample):
    """根据你提供的结构提取 code"""
    try:
        # 路径: sample -> tool_args -> code
        return sample.get("tool_args", {}).get("code")
    except:
        return None

def merge_json_files(src_file, dst_file):
    """核心逻辑：合并两个文件中的 samples，按 code 去重"""
    src_data = load_json_data(src_file)
    dst_data = load_json_data(dst_file)

    if src_data is None or dst_data is None:
        return False # 读取出错，不执行合并

    # 获取目标文件中已有的所有 code
    existing_codes = {get_code(s) for s in dst_data if get_code(s) is not None}
    
    initial_count = len(dst_data)
    for sample in src_data:
        code = get_code(sample)
        if code and code not in existing_codes:
            dst_data.append(sample)
            existing_codes.add(code)
    
    new_added = len(dst_data) - initial_count
    if new_added > 0:
        save_json_data(dst_file, dst_data)
        print(f"  [合并完成] {os.path.basename(dst_file)}: 新增了 {new_added} 条 code 样本")
    else:
        print(f"  [无需合并] {os.path.basename(dst_file)}: 未发现新 code")
    return True

def start_recursive_merge():
    for target in TARGET_FOLDERS:
        src_folder = os.path.join(SRC_ROOT_BASE, target)
        dst_folder = os.path.join(DST_ROOT_BASE, target)

        if not os.path.exists(src_folder):
            print(f"源文件夹不存在，跳过: {src_folder}")
            continue

        print(f"\n>>> 正在扫描目录: {target}")

        # 使用 os.walk 递归遍历所有子文件夹
        for root, dirs, files in os.walk(src_folder):
            # 计算当前子目录相对于源根目录的路径
            rel_path = os.path.relpath(root, src_folder)
            # 对应的目标子目录路径
            target_dst_dir = os.path.join(dst_folder, rel_path)

            # 1. 如果目标子目录不存在，直接创建
            if not os.path.exists(target_dst_dir):
                os.makedirs(target_dst_dir)
                print(f"创建新目录: {target_dst_dir}")

            # 2. 处理当前目录下的所有文件
            for filename in files:
                # 隐藏文件跳过 (如 .DS_Store)
                if filename.startswith('.'): continue
                
                src_file_path = os.path.join(root, filename)
                dst_file_path = os.path.join(target_dst_dir, filename)

                if not os.path.exists(dst_file_path):
                    # 如果目标位置没有这个文件，直接整体复制
                    shutil.copy2(src_file_path, dst_file_path)
                    print(f"  [新文件] 已复制: {rel_path}/{filename}")
                else:
                    # 如果目标位置有重名文件，执行深度合并
                    merge_json_files(src_file_path, dst_file_path)

if __name__ == "__main__":
    print("开始深度合并任务...")
    start_recursive_merge()
    print("\n所有任务已结束。")