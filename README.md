<p align="center">
  <strong>Finance MCP · 面向金融研究的智能代理与 MCP 服务</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/finance-mcp/"><img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python 版本"></a>
  <a href="https://pypi.org/project/finance-mcp/"><img src="https://img.shields.io/pypi/v/finance-mcp.svg?logo=pypi" alt="PyPI 版本"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-black" alt="许可证"></a>
  <a href="https://github.com/flowllm-ai/finance-mcp"><img src="https://img.shields.io/github/stars/flowllm-ai/finance-mcp?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <em><sub>如果 Finance MCP 对你有帮助，欢迎点一个 ⭐ Star，你的支持是我们持续改进的动力。</sub></em>
</p>

<p align="center">
  <a href="https://flowllm-ai.github.io/finance-mcp/">English Docs</a> | 简体中文
</p>

---

Finance MCP 是一个面向金融研究场景的智能体工具包与 MCP 服务器，基于
[FlowLLM](https://github.com/flowllm-ai/flowllm)、网络搜索工具和
[Crawl4AI](https://github.com/unclecode/crawl4ai) 等组件，帮助你快速搭建：

- **金融研究 / 深度研报型智能体**
- **面向 IDE / 客户端的 MCP Server**
- **可编排的金融数据抓取与信息抽取流水线**

你可以把它理解为：

```text
Finance MCP = LLM Agents + Web Search + Crawl4AI + 金融实体与文本抽取
```

---

## 📰 项目概览

- **MCP Server 支持**：默认后端为 MCP，可直接通过 `stdio` 集成到 IDE / 客户端。
- **HTTP 服务模式**：也可通过 HTTP 暴露服务，方便外部系统调用。
- **金融研究 Agent**：内置 `ConductResearchOp`、`DashscopeDeepResearchOp` 等算子，支持深度研究与多轮检索。
- **网页抓取与长文本处理**：基于 `Crawl4aiOp` / `Crawl4aiLongTextOp` 和 `ExtractLongTextOp`，对网页进行抓取与段落级抽取。
- **金融实体识别与代码补全**：`ExtractEntitiesCodeOp` 可从自然语言中抽取股票 / 基金实体，并补全证券代码。
- **可组合的 Flow 编排**：通过配置文件（如 `config/default.yaml`）组合多个算子，快速构建你的研究流。

---

## ✨ 架构与核心组件

Finance MCP 基于 FlowLLM 的 Application 框架，对外提供统一的应用入口
`FinanceMcpApp`（见 `finance_mcp/main.py`），其核心能力集中在 `finance_mcp/core` 中：

### 🧠 Agent 与研究流程（`finance_mcp.core.agent`）

负责高层次的研究与 ReAct 风格工作流调度，包括：

- **`ConductResearchOp`**：组合搜索与思考工具，实现「研究主题 → 结构化结论」的完整流程。
- **`DashscopeDeepResearchOp`**：基于 Dashscope 搜索与 LLM 的深度研究算子。
- **`LangchainDeepResearchOp`**：基于 LangChain 的深度研究算子。
- **`ReactAgentOp` / `ReactSearchOp`**：ReAct 风格智能体与搜索工具。
- **`ThinkToolOp`**：通用思考工具，可与搜索 / 抓取等算子组合使用。

### 🌐 抓取与内容构建（`finance_mcp.core.crawl`）

基于 Crawl4AI 和自定义工具的网页抓取模块：

- **`Crawl4aiOp` / `Crawl4aiLongTextOp`**：抓取网页并生成 Markdown/长文本，便于下游 LLM 消费。
- **`ThsUrlOp`**：构造 THS（同花顺 10jqka）等数据源的标准化 URL。

### 🔍 文本与实体抽取（`finance_mcp.core.extract`）

面向金融场景的文本抽取与结构化处理：

- **`ExtractEntitiesCodeOp`**：从用户查询中抽取股票 / 基金等实体，并补全证券代码。
- **`ExtractLongTextOp`**：在长文本中抽取与查询相关的关键内容片段。

### 🔧 搜索与工具（`finance_mcp.core.search` & `finance_mcp.core.utils`）

- 集成 Dashscope / Tavily 等搜索后端，提供统一的搜索算子（如 `DashscopeSearchOp`）。
- `run_stream_op` 等工具帮助你以流式方式执行算子并打印中间结果。

### ⚙️ 配置与 Flow 编排（`finance_mcp/config/default.yaml`）

默认配置文件中预置了若干常用 Flow：

- **`flow.crawl_url`**：`Crawl4aiLongTextOp() >> ExtractLongTextOp()`，抓取网页并抽取重点内容。
- **`flow.extract_entities_code`**：`ExtractEntitiesCodeOp() << DashscopeSearchOp()`，抽取实体并补全代码。
- **`flow.react_agent`**：组合 `HistoryCalculateOp`、`ExtractEntitiesCodeOp` 与 `DashscopeSearchOp`，再交给 `ReactAgentOp` 调度。
- **通用工具 Flow**：`execute_code`、`execute_shell`、`dashscope_search`、`tavily_search` 等。

---

## 🛠️ 安装

### 通过 PyPI 安装（推荐）

```bash
pip install finance-mcp
```

### 从源码安装

```bash
git clone https://github.com/flowllm-ai/finance-mcp.git
cd finance-mcp
pip install .
```

---

## 🔑 环境变量配置

参考仓库中的 `example.env`，你至少需要配置：

```bash
FLOW_LLM_API_KEY=xxx
FLOW_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 可选：按需启用的其他 key
# DASHSCOPE_API_KEY=xxx
# TUSHARE_API_TOKEN=xxx
# TAVILY_API_KEY=xxx
# BAILIAN_MCP_API_KEY=xxx
```

建议将上述内容复制为 `.env` 文件，并在运行环境中加载。

---

## 🚀 快速开始

### 1. 作为 MCP Server 运行

`config/default.yaml` 中默认：

```yaml
backend: mcp

mcp:
  transport: stdio
  host: "0.0.0.0"
  port: 8001
```

你可以直接通过命令行启动：

```bash
finance-mcp \
  backend=mcp \
  mcp.transport=stdio
```

或者在需要 TCP 方式时：

```bash
finance-mcp \
  backend=mcp \
  mcp.host=0.0.0.0 \
  mcp.port=8001
```

之后即可在支持 MCP 的客户端中，将 Finance MCP 配置为一个工具服务器。

### 2. 以 HTTP 服务方式运行

`default.yaml` 中同时给出了 HTTP 服务配置：

```yaml
http:
  host: "0.0.0.0"
  port: 8002
```

启动命令示例：

```bash
finance-mcp \
  backend=http \
  http.host=0.0.0.0 \
  http.port=8002
```

随后即可通过 HTTP 接口访问由 Flow 定义的各类算子能力。

---

## 💻 示例：运行研究工作流

仓库下的 `test_op/` 目录中包含若干端到端示例脚本，可作为你的参考实现。

### 1. 高层研究流程：`test_conduct_research.py`

```python
from finance_mcp import FinanceMcpApp
from finance_mcp.core.agent import ConductResearchOp, ThinkToolOp
from finance_mcp.core.search import DashscopeSearchOp
from finance_mcp.core.utils import run_stream_op

async with FinanceMcpApp():
    op = ConductResearchOp()
    op.ops.search_op = DashscopeSearchOp()
    op.ops.think_op = ThinkToolOp()

    research_topic = "茅台公司未来业绩"
    async for _ in run_stream_op(op, enable_print=True, research_topic=research_topic):
        pass
```

该脚本展示了：

- 如何在 `FinanceMcpApp` 上下文中构建研究算子。
- 如何为研究算子注入具体的搜索与思考工具。
- 如何以「流式」方式打印中间结果，方便调试和人工检查。

### 2. Dashscope 深度研究：`test_dashscope_deep_research.py`

```python
from finance_mcp.core.agent import DashscopeDeepResearchOp
from finance_mcp.core.utils import run_stream_op

query = "茅台公司未来业绩"
op = DashscopeDeepResearchOp()

async for _ in run_stream_op(op, enable_print=True, query=query):
    pass
```

这个脚本聚焦于 `DashscopeDeepResearchOp` 本身，适合快速验证深度研究链路是否正常工作。

---

## 📚 文档与资源

- **在线文档**：<https://flowllm-ai.github.io/finance-mcp/>
- **配置示例**：`finance_mcp/config/default.yaml`
- **核心模块**：`finance_mcp/core/{agent,crawl,extract,search,utils}`
- **示例脚本**：`test_op/` 下的若干 `*_op.py` 文件
- **相关项目**：
  - FlowLLM：<https://github.com/flowllm-ai/flowllm>
  - Crawl4AI：<https://github.com/unclecode/crawl4ai>

---

## 🤝 参与贡献

我们非常欢迎社区同学参与共建 Finance MCP，包括但不限于：

- **新增金融场景算子 / Flow**：例如特定行业研究模板、量化指标分析等。
- **接入更多数据源 / 搜索后端**：如新增券商研报源、宏观数据服务等。
- **改进文档与示例**：补充从零搭建金融研究 Agent 的完整教程。

你可以通过提交 Issue 或 Pull Request 的方式参与，也可以在讨论区分享你的使用经验与最佳实践。

---

## ⚖️ 许可证

本项目基于 Apache License 2.0 开源，详情参见 [LICENSE](./LICENSE) 文件。

---

## ⭐ Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=flowllm-ai/finance-mcp&type=Date)](https://www.star-history.com/#flowllm-ai/finance-mcp&Date)