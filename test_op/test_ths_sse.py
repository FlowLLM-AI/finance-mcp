import asyncio
import json
import os
import random
import uuid

# 禁用代理，避免 httpx 读取系统代理配置导致连接失败
os.environ.setdefault("NO_PROXY", "*")
import pandas as pd
from datetime import datetime
from fastmcp.client.client import CallToolResult
from loguru import logger

from finance_mcp.core.utils.fastmcp_client import FastMcpClient

# --- 配置区 ---
HOST = "127.0.0.1"  # 使用 IPv4 地址，避免 IPv6 连接问题
PORT = 8050
CSV_PATH = "tushare_stock_basic_20251226104714.csv"
BASE_CACHE_DIR = "tool_cache"
PROGRESS_DIR = os.path.join(BASE_CACHE_DIR, "progress")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
SAVE_BATCH_SIZE = 1               # 每1个保存一次
MAX_CONCURRENCY = 5               # 最大并发数（信号量控制，设为1即串行）
MIN_WAIT_ON_EMPTY = 60            # 无输出时最小等待秒数
MAX_WAIT_ON_EMPTY = 120           # 无输出时最大等待秒数
NORMAL_WAIT_SECONDS = 2          # 正常请求间隔秒数

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
    # ("crawl_ths_finance", "提取财务分析详情：1.主要财务指标（盈利、成长、偿债等）；2.资产负债表、利润表、现金流量表的核心科目及审计意见。"),
    # ("crawl_ths_bonus", "提取分红融资记录：1.历年现金分红、送转股份方案及实施日期；2.历次增发、配股等融资详情。"),
    # ("crawl_ths_event", "提取公司大事记录：1.股东及高管持股变动明细；2.对外担保记录、违规处理、机构调研及投资者互动记录。"),
    ("crawl_ths_field", "提取行业对比数据：1.公司在所属行业内的规模、成长、盈利各项排名；2.与行业均值及同类竞品的关键财务指标对比。")
]

if not os.path.exists(BASE_CACHE_DIR):
    os.makedirs(BASE_CACHE_DIR, exist_ok=True)
os.makedirs(PROGRESS_DIR, exist_ok=True)

class BatchResultSaver:
    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.buffer = []
        self.file_index = 1
        
    def _get_file_path(self):
        return os.path.join(BASE_CACHE_DIR, f"{self.tool_name}_{self.file_index:02d}.json")

    def add_record(self, tool_args, result_text):
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
        if not self.buffer: return
        file_path = self._get_file_path()
        
        # 自动切分 50MB
        if os.path.exists(file_path) and os.path.getsize(file_path) > MAX_FILE_SIZE:
            self.file_index += 1
            file_path = self._get_file_path()

        data = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try: data = json.load(f)
                except: data = []
        
        data.extend(self.buffer)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Save: {file_path} | Count: {len(data)}")
        self.buffer = []

class ProgressTracker:
    """进度跟踪器，支持断点继续"""
    def __init__(self, tool_name):
        self.tool_name = tool_name
        self.progress_file = os.path.join(PROGRESS_DIR, f"{tool_name}_progress.json")
        self.completed_codes = set()
        self.time_records = {}  # 记录每个code的处理时间
        self.load_progress()
    
    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_codes = set(data.get("completed_codes", []))
                    self.time_records = data.get("time_records", {})
            except Exception as e:
                logger.warning(f"加载进度文件失败 {self.progress_file}: {e}")
                self.completed_codes = set()
                self.time_records = {}
    
    def save_progress(self):
        try:
            data = {
                "completed_codes": list(self.completed_codes),
                "time_records": self.time_records
            }
            with open(self.progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存进度文件失败 {self.progress_file}: {e}")
    
    def mark_completed(self, code, elapsed_time=None):
        self.completed_codes.add(code)
        if elapsed_time is not None:
            self.time_records[code] = {
                "elapsed_seconds": round(elapsed_time, 2),
                "completed_at": datetime.now().isoformat()
            }
    
    def is_completed(self, code):
        return code in self.completed_codes
    
    def get_remaining_codes(self, all_codes):
        return [code for code in all_codes if not self.is_completed(code)]

async def process_single_stock(client, tool_name, code, deep_query, saver, progress_tracker, semaphore, index, total):
    """处理单个股票的异步任务"""
    async with semaphore:  # 信号量控制并发数
        args = {"code": code, "query": deep_query}
        start_time = datetime.now()  # 记录开始时间
        try:
            logger.info(f"Calling {tool_name} for {code} ({index}/{total})")
            result: CallToolResult = await client.call_tool(tool_name, args)
            elapsed_time = (datetime.now() - start_time).total_seconds()  # 计算耗时
            
            if not result.is_error:
                content = result.content[0].text if result.content else ""
                
                # 检查内容是否包含不当内容警告,直接跳过不保存
                if "Input data may contain inappropriate content" in content:
                    logger.warning(f"工具 {tool_name} 处理 {code} 返回不当内容警告, 跳过该记录")
                    return
                
                # 检查内容是否为空或太短,如果是则等待50-100秒
                if not content or len(content.strip()) < 10:
                    wait_seconds = random.randint(MIN_WAIT_ON_EMPTY, MAX_WAIT_ON_EMPTY)
                    logger.warning(
                        f"工具 {tool_name} 处理 {code} 无输出或输出过短, "
                        f"耗时 {elapsed_time:.2f}秒, 等待 {wait_seconds} 秒..."
                    )
                    await asyncio.sleep(wait_seconds)
                else:
                    # 有正常输出,保存记录
                    saver.add_record(args, content)
                    # 标记该代码已完成,记录耗时
                    progress_tracker.mark_completed(code, elapsed_time)
                    # 定期保存进度
                    if index % SAVE_BATCH_SIZE == 0:
                        progress_tracker.save_progress()
                    # 正常等待间隔
                    logger.info(f"成功处理 {code}, 耗时 {elapsed_time:.2f}秒, 等待 {NORMAL_WAIT_SECONDS} 秒...")
                    await asyncio.sleep(NORMAL_WAIT_SECONDS)
            else:
                error_msg = result.content[0].text[:100] if result.content else "No error message"
                logger.error(f"Error {code}: {error_msg}, 耗时 {elapsed_time:.2f}秒")
        except Exception as e:
            import traceback
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Failed {code}: {e}, 耗时 {elapsed_time:.2f}秒")
            logger.error(f"Traceback: {traceback.format_exc()}")

async def test_mcp_service():
    df = pd.read_csv(CSV_PATH, dtype={'symbol': str})
    stock_codes = df['symbol'].dropna().apply(lambda x: str(x).zfill(6)).tolist()
    
    mcp_config = {"type": "sse", "url": f"http://{HOST}:{PORT}/sse"}
    
    # 信号量控制并发数
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async with FastMcpClient(name="full-info-crawler", config=mcp_config) as client:
        # 外层循环:工具 (及设计好的深度 Query)
        for tool_name, deep_query in TOOLS_CONFIG:
            logger.info(f"### 开始爬取工具: {tool_name}")
            saver = BatchResultSaver(tool_name)
            progress_tracker = ProgressTracker(tool_name)
            
            # 获取剩余需要处理的股票代码
            remaining_codes = progress_tracker.get_remaining_codes(stock_codes)
            total_remaining = len(remaining_codes)
            logger.info(f"### 工具 {tool_name} 剩余 {total_remaining} 个股票代码待处理")
            
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
                    total=total_remaining
                )
                tasks.append(task)
            
            # 并发执行所有任务,信号量控制最多10个同时运行
            logger.info(f"启动 {len(tasks)} 个并发任务,信号量限制为 {MAX_CONCURRENCY}")
            await asyncio.gather(*tasks)
            
            # 保存最后的进度
            progress_tracker.save_progress()
            saver.flush()  # 一个工具所有代码跑完,冲刷最后的数据
            logger.info(f"### 工具 {tool_name} 完成!")

if __name__ == "__main__":
    asyncio.run(test_mcp_service())