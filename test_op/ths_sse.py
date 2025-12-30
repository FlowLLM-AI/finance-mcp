"""同花顺数据全量爬取脚本（集成服务启动）

该脚本整合了服务启动和数据爬取功能，无需手动在两个终端中分别启动服务和脚本。
使用 FinanceMcpServiceRunner 自动启动和管理 finance-mcp 服务，并在同一进程中执行批量爬取任务。

功能特性：
1. 自动启动 finance-mcp 服务（SSE模式）
2. 支持断点续传（基于进度文件）
3. 并发控制（信号量）
4. 批量保存结果到 JSON 文件
5. 自动文件切分（50MB）
6. 智能等待策略（无输出时长等待，正常时短等待）
"""

import asyncio
import json
import os
import random
import uuid
import pandas as pd
from datetime import datetime
from fastmcp.client.client import CallToolResult
from loguru import logger

from finance_mcp.core.utils.fastmcp_client import FastMcpClient
from finance_mcp.core.utils.service_runner import FinanceMcpServiceRunner

# --- 服务配置 ---
SERVICE_ARGS = [
    "finance-mcp",
    "config=default,ths",
    'disabled_flows=["tavily_search","mock_search","react_agent"]',
    "mcp.transport=sse",
]
HOST = "localhost"
PORT = 8050
os.environ.setdefault("NO_PROXY", "*")
# --- 数据配置 ---
CSV_PATH = "tushare_stock_basic_20251226104714.csv"
BASE_CACHE_DIR = "tool_cache"
PROGRESS_DIR = os.path.join(BASE_CACHE_DIR, "progress")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SAVE_BATCH_SIZE = 1               # 每1个保存一次
MAX_CONCURRENCY = 5              # 最大并发数（信号量控制）
PROGRESS_REPORT_INTERVAL = 10    # 每处理N条记录显示一次进度汇总
MIN_WAIT_ON_EMPTY = 60            # 无输出时最小等待秒数
MAX_WAIT_ON_EMPTY = 120           # 无输出时最大等待秒数
NORMAL_WAIT_SECONDS = 3           # 正常请求间隔秒数

# 无效结果标识（这些结果需要重新爬取）
INVALID_RESULTS = [
    "No relevant content found matching the query.",
    "未找到与查询匹配的相关内容",
]

# 针对每个页面结构设计的全量提取 Query
TOOLS_CONFIG = [
    # ("crawl_ths_company", "提取公司的完整资料：1.基本信息（行业、产品、主营、办公地址）；2.高管介绍（所有高管的姓名、职务、薪资、详细个人简历）；3.发行相关（上市日期、首日表现、募资额）；4.所有参控股公司的名称、持股比例、业务、盈亏情况。"),
    # ("crawl_ths_holder", "提取股东研究全量数据：1.历年股东人数及户均持股数；2.前十大股东及流通股东名单（含持股数、性质、变动情况）；3.实际控制人详情及控股层级关系描述；4.股权质押、冻结的详细明细表。"),
    # ("crawl_ths_operate", "提取经营分析数据：1.主营构成分析表（按行业、产品、区域划分的营业收入、利润、毛利率及同比变化）；2.经营评述（公司对业务、核心竞争力的详细自我评估）。"),
    # ("crawl_ths_equity", "提取股本结构信息：1.历次股本变动原因、日期及变动后的总股本；2.限售股份解禁的时间表、解禁数量及占总股本比例。"),
    # ("crawl_ths_capital", "提取资本运作详情：1.资产重组、收购、合并的详细历史记录；2.对外投资明细及进展情况。"),
    # ("crawl_ths_worth", "提取盈利预测信息：1.各机构最新评级汇总（买入/增持次数）；2.未来三年的营收预测、净利润预测及EPS预测均值。"),
    # ("crawl_ths_news", "提取最新新闻公告：1.公司最新重要公告标题及日期；2.媒体报道的新闻摘要及舆情评价。"),
    # ("crawl_ths_concept", "提取所有概念题材：列出公司所属的所有概念板块，并详细提取每个概念对应的具体入选理由和业务关联性。"),
    # ("crawl_ths_position", "提取主力持仓情况：1.各类机构（基金、保险、QFII等）持仓总数及占比；2.前十大具体机构持仓名单及变动。"),
    ("crawl_ths_finance", "提取财务分析详情：1.主要财务指标（盈利、成长、偿债等）；2.资产负债表、利润表、现金流量表的核心科目及审计意见。"),
    # ("crawl_ths_bonus", "提取分红融资记录：1.历年现金分红、送转股份方案及实施日期；2.历次增发、配股等融资详情。"),
    ("crawl_ths_event", "提取公司大事记录：1.股东及高管持股变动明细；2.对外担保记录、违规处理、机构调研及投资者互动记录。"),
    # ("crawl_ths_field", "提取行业对比数据：1.公司在所属行业内的规模、成长、盈利各项排名；2.与行业均值及同类竞品的关键财务指标对比。")
]

# 创建必要的目录
if not os.path.exists(BASE_CACHE_DIR):
    os.makedirs(BASE_CACHE_DIR, exist_ok=True)
os.makedirs(PROGRESS_DIR, exist_ok=True)


class BatchResultSaver:
    """批量结果保存器，支持自动文件切分"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.buffer = []
        self.file_index = 1
        
    def _get_file_path(self) -> str:
        """获取当前保存文件路径"""
        return os.path.join(BASE_CACHE_DIR, f"{self.tool_name}_{self.file_index:02d}.json")

    def add_record(self, tool_args: dict, result_text: str):
        """添加一条记录到缓冲区"""
        now = datetime.now()
        record = {
            "_id": str(uuid.uuid4()),
            "cache_key": f"{self.tool_name}::{json.dumps(tool_args, ensure_ascii=False)}",
            "created_at": now.isoformat(),
            "metadata": {"task_id": "comprehensive_crawl", "timestamp": now.isoformat()},
            "tool_args": tool_args,
            "tool_name": self.tool_name,
            "tool_result": result_text,
            "updated_at": now.isoformat()
        }
        self.buffer.append(record)
        if len(self.buffer) >= SAVE_BATCH_SIZE:
            self.flush()

    def flush(self):
        """将缓冲区数据写入文件"""
        if not self.buffer:
            return
            
        file_path = self._get_file_path()
        
        # 自动切分：如果文件超过 50MB，切换到新文件
        if os.path.exists(file_path) and os.path.getsize(file_path) > MAX_FILE_SIZE:
            self.file_index += 1
            file_path = self._get_file_path()

        # 读取现有数据
        data = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except:
                    data = []
        
        # 追加新数据并保存
        data.extend(self.buffer)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"保存文件: {file_path} | 总记录数: {len(data)}")
        self.buffer = []


class ProgressTracker:
    """进度跟踪器，支持断点继续"""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self.progress_file = os.path.join(PROGRESS_DIR, f"{tool_name}_progress.json")
        self.completed_codes = set()
        self.time_records = {}  # 记录每个code的处理时间
        self.load_progress()
    
    def load_progress(self):
        """加载已有的进度数据"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_codes = set(data.get("completed_codes", []))
                    self.time_records = data.get("time_records", {})
                logger.info(f"加载进度文件: {self.progress_file}，已完成 {len(self.completed_codes)} 个")
            except Exception as e:
                logger.warning(f"加载进度文件失败 {self.progress_file}: {e}")
                self.completed_codes = set()
                self.time_records = {}
    
    def save_progress(self):
        """保存当前进度"""
        try:
            data = {
                "completed_codes": list(self.completed_codes),
                "time_records": self.time_records
            }
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存进度文件失败 {self.progress_file}: {e}")
    
    def mark_completed(self, code: str, elapsed_time: float | None = None):
        """标记某个代码为已完成"""
        self.completed_codes.add(code)
        if elapsed_time is not None:
            self.time_records[code] = {
                "elapsed_seconds": round(elapsed_time, 2),
                "completed_at": datetime.now().isoformat()
            }
    
    def is_completed(self, code: str) -> bool:
        """检查某个代码是否已完成"""
        return code in self.completed_codes
    
    def get_remaining_codes(self, all_codes: list) -> list:
        """获取剩余需要处理的代码列表"""
        return [code for code in all_codes if not self.is_completed(code)]


MAX_RETRIES = 1  # 最大重试次数


# 全局计数器，用于追踪处理进度
class GlobalProgressCounter:
    def __init__(self):
        self.processed_count = 0
        self.lock = asyncio.Lock()
    
    async def increment(self):
        async with self.lock:
            self.processed_count += 1
            return self.processed_count

global_counter = GlobalProgressCounter()


async def process_single_stock(
    client: FastMcpClient,
    tool_name: str,
    code: str,
    deep_query: str,
    saver: BatchResultSaver,
    progress_tracker: ProgressTracker,
    semaphore: asyncio.Semaphore,
    index: int,
    total: int,
    total_all_tools: int = 0
):
    """处理单个股票的异步任务"""
    async with semaphore:  # 信号量控制并发数
        args = {"code": code, "query": deep_query}
        
        for attempt in range(1, MAX_RETRIES + 1):
            start_time = datetime.now()
            
            try:
                logger.info(f"[{index}/{total}] 调用 {tool_name} 处理股票 {code} (尝试 {attempt}/{MAX_RETRIES})")
                result: CallToolResult = await client.call_tool(tool_name, args)
                elapsed_time = (datetime.now() - start_time).total_seconds()
                
                if not result.is_error:
                    content = result.content[0].text if result.content else ""
                    
                    # 检查内容是否为空、太短或是无效结果
                    is_invalid = (
                        not content 
                        or len(content.strip()) < 10 
                        or content.strip() in INVALID_RESULTS
                    )
                    
                    if is_invalid:
                        if attempt < MAX_RETRIES:
                            wait_seconds = random.randint(MIN_WAIT_ON_EMPTY, MAX_WAIT_ON_EMPTY)
                            logger.warning(
                                f"工具 {tool_name} 处理 {code} 无效结果: '{content[:50]}...', "
                                f"耗时 {elapsed_time:.2f}秒, 等待 {wait_seconds} 秒后重试 ({attempt}/{MAX_RETRIES})..."
                            )
                            await asyncio.sleep(wait_seconds)
                            continue  # 重试
                        else:
                            logger.error(
                                f"工具 {tool_name} 处理 {code} 达到最大重试次数 {MAX_RETRIES}, "
                                f"仍为无效结果: '{content[:50]}...', 跳过"
                            )
                            return  # 达到最大重试次数，放弃
                    else:
                        # 有正常输出，保存记录
                        saver.add_record(args, content)
                        # 标记该代码已完成，记录耗时
                        progress_tracker.mark_completed(code, elapsed_time)
                        # 定期保存进度
                        if index % SAVE_BATCH_SIZE == 0:
                            progress_tracker.save_progress()
                        
                        # 更新全局计数并显示剩余数量
                        global_processed = await global_counter.increment()
                        remaining_this_tool = total - index
                        remaining_all = total_all_tools - global_processed
                        
                        # 正常等待间隔，显示剩余数量
                        logger.info(
                            f"✓ 成功处理 {code}, 耗时 {elapsed_time:.2f}秒 | "
                            f"当前工具剩余: {remaining_this_tool}/{total} | "
                            f"总剩余: {remaining_all}"
                        )
                        
                        # 每隔一定数量显示详细进度汇总
                        if global_processed % PROGRESS_REPORT_INTERVAL == 0:
                            logger.info(
                                f"\n{'─'*40}\n"
                                f"📊 进度汇总: 已处理 {global_processed} 条, 总剩余 {remaining_all} 条\n"
                                f"{'─'*40}"
                            )
                        
                        await asyncio.sleep(NORMAL_WAIT_SECONDS)
                        return  # 成功，退出重试循环
                else:
                    error_msg = result.content[0].text[:100] if result.content else "No error message"
                    if attempt < MAX_RETRIES:
                        wait_seconds = random.randint(MIN_WAIT_ON_EMPTY, MAX_WAIT_ON_EMPTY)
                        logger.warning(f"✗ 错误 {code}: {error_msg}, 等待 {wait_seconds} 秒后重试 ({attempt}/{MAX_RETRIES})...")
                        await asyncio.sleep(wait_seconds)
                        continue  # 重试
                    else:
                        logger.error(f"✗ 错误 {code}: {error_msg}, 达到最大重试次数 {MAX_RETRIES}, 跳过")
                        return
                    
            except Exception as e:
                import traceback
                elapsed_time = (datetime.now() - start_time).total_seconds()
                error_str = str(e)
                
                # 检查是否是“不当内容”错误，这种情况不需要重试
                if "inappropriate content" in error_str:
                    logger.warning(f"⚠ {code}: 返回不当内容错误，跳过不重试")
                    return
                
                if attempt < MAX_RETRIES:
                    wait_seconds = random.randint(MIN_WAIT_ON_EMPTY, MAX_WAIT_ON_EMPTY)
                    logger.warning(f"✗ 失败 {code}: {e}, 等待 {wait_seconds} 秒后重试 ({attempt}/{MAX_RETRIES})...")
                    await asyncio.sleep(wait_seconds)
                    continue  # 重试
                else:
                    logger.error(f"✗ 失败 {code}: {e}, 达到最大重试次数 {MAX_RETRIES}, 跳过")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    return


async def run_crawl_task():
    """执行爬取任务的主函数"""
    # 读取股票代码列表
    logger.info(f"读取股票代码列表: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, dtype={'symbol': str})
    stock_codes = df['symbol'].dropna().apply(lambda x: str(x).zfill(6)).tolist()
    logger.info(f"共加载 {len(stock_codes)} 个股票代码")
    
    # MCP 客户端配置
    mcp_config = {"type": "sse", "url": f"http://{HOST}:{PORT}/sse"}
    
    # 信号量控制并发数
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    # 【第二步】汇总统计各工具待爬取数量
    logger.info(f"\n{'='*60}")
    logger.info("【第二步】统计各工具待爬取数量...")
    logger.info(f"{'='*60}")
    
    total_tasks = 0
    tool_stats = []
    for tool_name, deep_query in TOOLS_CONFIG:
        progress_tracker = ProgressTracker(tool_name)
        remaining_codes = progress_tracker.get_remaining_codes(stock_codes)
        total_remaining = len(remaining_codes)
        completed_count = len(stock_codes) - total_remaining
        total_tasks += total_remaining
        tool_stats.append((tool_name, completed_count, total_remaining))
        # 只列出还需要爬取的工具
        if total_remaining > 0:
            logger.info(
                f"  {tool_name}: 已完成 {completed_count}, 待爬取 {total_remaining}"
            )
    
    logger.info(f"{'='*60}")
    logger.info(f"汇总: 共 {len(TOOLS_CONFIG)} 个工具, 总计待爬取 {total_tasks} 条记录")
    logger.info(f"{'='*60}\n")
    
    if total_tasks == 0:
        logger.info("所有工具已完成爬取，无需继续")
        return
    # return
    
    # 重置全局计数器
    global global_counter
    global_counter = GlobalProgressCounter()
    
    # 【第三步】开始爬取任务
    logger.info(f"\n{'='*60}")
    logger.info("【第三步】开始爬取任务...")
    logger.info(f"{'='*60}\n")
    
    async with FastMcpClient(name="full-info-crawler", config=mcp_config) as client:
        # 外层循环：遍历所有工具
        for tool_name, deep_query in TOOLS_CONFIG:
            logger.info(f"\n{'-'*60}")
            logger.info(f"开始爬取工具: {tool_name}")
            logger.info(f"查询内容: {deep_query}")
            logger.info(f"{'-'*60}")
            
            saver = BatchResultSaver(tool_name)
            progress_tracker = ProgressTracker(tool_name)
            
            # 获取剩余需要处理的股票代码
            remaining_codes = progress_tracker.get_remaining_codes(stock_codes)
            total_remaining = len(remaining_codes)
            completed_count = len(stock_codes) - total_remaining
            
            logger.info(
                f"工具 {tool_name}: 总计 {len(stock_codes)} 个股票, "
                f"已完成 {completed_count} 个, 剩余 {total_remaining} 个"
            )
            
            if total_remaining == 0:
                logger.info(f"工具 {tool_name} 所有股票已处理完成，跳过")
                continue
            
            # 创建所有并发任务
            tasks = []
            for i, code in enumerate(remaining_codes, start=1):
                task = process_single_stock(
                    client=client,
                    tool_name=tool_name,
                    code=code,
                    deep_query=deep_query,
                    saver=saver,
                    progress_tracker=progress_tracker,
                    semaphore=semaphore,
                    index=i,
                    total=total_remaining,
                    total_all_tools=total_tasks
                )
                tasks.append(task)
            
            # 并发执行所有任务，信号量控制最多 MAX_CONCURRENCY 个同时运行
            logger.info(f"启动 {len(tasks)} 个并发任务，最大并发数: {MAX_CONCURRENCY}")
            await asyncio.gather(*tasks)
            
            # 保存最后的进度
            progress_tracker.save_progress()
            saver.flush()
            logger.info(f"\n{'='*80}")
            logger.info(f"✓ 工具 {tool_name} 完成!")
            logger.info(f"{'='*80}\n")


def main():
    """主函数：启动服务并运行爬取任务"""
    logger.info("="*80)
    logger.info("开始启动 finance-mcp 服务...")
    logger.info(f"服务参数: {SERVICE_ARGS}")
    logger.info(f"监听地址: {HOST}:{PORT}")
    logger.info("="*80)
    
    # 使用 FinanceMcpServiceRunner 启动服务
    with FinanceMcpServiceRunner(
        SERVICE_ARGS,
        host=HOST,
        port=PORT,
    ) as service:
        logger.info(f"✓ 服务已启动，监听端口: {service.port}")
        logger.info("开始执行爬取任务...\n")
        
        # 运行爬取任务
        asyncio.run(run_crawl_task())
        
        logger.info("\n" + "="*80)
        logger.info("✓ 所有任务已完成")
        logger.info("="*80)


if __name__ == "__main__":
    main()
