# <img src="docs/figure/logo.png" alt="Finance MCP Logo" width="4%" style="vertical-align: middle;"> Finance-MCP

<p>
  <a href="https://pypi.org/project/finance-mcp/"><img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python 版本"></a>
  <a href="https://pypi.org/project/finance-mcp/"><img src="https://img.shields.io/pypi/v/finance-mcp.svg?logo=pypi" alt="PyPI 版本"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-black" alt="许可证"></a>
  <a href="https://github.com/flowllm-ai/finance-mcp"><img src="https://img.shields.io/github/stars/flowllm-ai/finance-mcp?style=social" alt="GitHub Stars"></a>
  [![English](https://img.shields.io/badge/English-Click-yellow)](README.md)
  [![简体中文](https://img.shields.io/badge/简体中文-点击查看-orange)](README_ZH.md)
</p>

---

## 📖 项目概览

Finance MCP 是一个面向金融研究场景的智能体工具包和 MCP（Model Context Protocol）服务器。基于 [FlowLLM](https://github.com/flowllm-ai/flowllm) 框架构建，集成了 [Crawl4AI](https://github.com/unclecode/crawl4ai)、[Tushare](https://tushare.pro/)、[Tavily](https://www.tavily.com/) / [DashScope](https://help.aliyun.com/zh/model-studio/web-search) 搜索等组件，帮助您快速搭建专业的金融研究智能体系统。

### 💡 为什么选择 Finance MCP？

- ✅ **零代码配置**：通过 YAML 配置文件组合算子，无需编写服务端代码  
- ✅ **开箱即用**：预置 20+ 个金融研究相关工作流，覆盖常见研究场景  
- ✅ **多协议支持**：同时支持 MCP（stdio/SSE/HTTP）和 HTTP RESTful API  
- ✅ **智能缓存**：内置多级缓存机制，提升效率并降低成本  
- ✅ **模块化设计**：每个功能模块均可独立配置，按需启用或禁用  

---

## 📰 最新动态

- **[2025-12]** 🎉 发布 finance-mcp v0.1.x

---

## 🚀 快速开始

### 安装

使用 pip 安装 Finance MCP：

```bash
pip install finance-mcp
```

或使用 uv：

```bash
uv pip install finance-mcp
```

---

### Stdio 模式

该模式通过 `uvx` 直接运行 Finance MCP，通过标准输入/输出进行通信，适用于本地 MCP 客户端。

```json
{
  "mcpServers": {
    "finance-mcp": {
      "command": "uvx",
      "args": [
        "finance-mcp",
        "config=default,ths",
        "mcp.transport=stdio",
        "llm.default.model_name=qwen3-30b-a3b-thinking-2507",
        "disabled_flows='[\"tavily_search\",\"mock_search\",\"react_agent\"]'"
      ],
      "env": {
        "FLOW_LLM_API_KEY": "xxx",
        "FLOW_LLM_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "DASHSCOPE_API_KEY": "xxx",
        "TUSHARE_API_TOKEN": "xxx",
        "TAVILY_API_KEY": "xxx",
        "BAILIAN_MCP_API_KEY": "xxx"
      }
    }
  }
}
```

---

#### 服务模式（HTTP/SSE 服务器）

此模式将 Finance MCP 启动为独立的 HTTP/SSE 服务器，可远程访问。

**步骤 1**：配置环境变量

复制 `example.env` 到 `.env` 并填写您的 API 密钥：

```bash
cp example.env .env
# 编辑 .env 文件并填入您的 API 密钥
```

**步骤 2**：启动服务器

使用 SSE 传输方式启动 Finance MCP 服务器：

```bash
finance-mcp \
  config=default,ths \
  mcp.transport=sse \
  mcp.host=0.0.0.0 \
  mcp.port=8001 \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  disabled_flows='["tavily_search","mock_search","react_agent"]'
```

服务将在以下地址可用：`http://0.0.0.0:8001/sse`

**步骤 3**：从 MCP 客户端连接

在您的 MCP 客户端中添加以下配置以连接远程 SSE 服务器：

```json
{
  "mcpServers": {
    "finance-mcp": {
      "type": "sse",
      "url": "http://0.0.0.0:8001/sse"
    }
  }
}
```

**步骤 4**：与 FastMCP 客户端配合使用

在服务模式下，您也可以使用 [FastMCP](https://gofastmcp.com/getting-started/welcome) Python 客户端直接访问服务器：

```python
import asyncio
from fastmcp import Client


async def main():
    async with Client("http://0.0.0.0:8001/sse") as client:
        for tool in client.list_tools():
            print(tool)

        result = await client.call_tool(
            name="dashscope_search",
            arguments={"query": "紫金矿业最近的新闻"}
        )
    print(result)


asyncio.run(main())
```

#### 一键测试命令

```bash
python test_op/test_project_sse.py
```

该命令将自动启动服务器、通过 FastMCP 客户端连接，并测试所有可用工具。

---

## 🚀 MCP 工具列表

#### 默认工具

| 工具名称                 | 描述                                                                                                   | 依赖项              | 输入参数                                                                           |
|--------------------------|--------------------------------------------------------------------------------------------------------|---------------------|------------------------------------------------------------------------------------|
| **history_calculate**    | 基于 Tushare A 股历史数据的价格成交量分析                                                             | `TUSHARE_API_TOKEN` | `code`: `601899`<br>`query`: 过去一周涨了多少？有没有 MACD 金叉？                  |
| **crawl_url**            | 抓取并解析网页内容                                                                                    | `crawl4ai`          | `url`: `https://example.com`                                                       |
| **extract_entities_code**| 从文本中识别金融实体并补全股票代码（当前使用 dashscope_search，可替换）                               | `DASHSCOPE_API_KEY` | `query`: 我想了解贵州茅台股票                                                     |
| **execute_code**         | 执行任意 Python 代码                                                                                  | -                   | `code`: `print(1+1)`                                                               |
| **execute_shell**        | 执行 Shell 命令                                                                                       | -                   | `command`: `ls`                                                                    |
| **dashscope_search**     | 基于 DashScope 的网络搜索                                                                             | `DASHSCOPE_API_KEY` | `query`: 紫金矿业最近的新闻                                                        |
| **tavily_search**        | 基于 Tavily 的网络搜索                                                                                | `TAVILY_API_KEY`    | `query`: 财经新闻                                                                  |
| **mock_search**          | 用于 LLM 模拟的模拟搜索                                                                               | -                   | `query`: 测试查询                                                                  |
| **react_agent**          | 结合多个工具回答复杂问题的 ReAct 智能体                                                               | -                   | `query`: 帮我分析紫金矿业下周走势                                                  |

#### 同花顺（TongHuaShun）工具

> **注意**：这些工具通过 crawl4ai 实现。高并发可能导致 IP 被封禁。

| 工具名称               | 描述                                                                                                                                                                                                         | 依赖项       | 输入参数                                                                                               |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|--------------------------------------------------------------------------------------------------------|
| **crawl_ths_company**  | 根据 A 股股票代码获取公司概况信息，包括详情、高管介绍、发行相关信息、子公司等，并返回与查询相关的信息                                                                                                         | `crawl4ai`   | `code`: 600519<br>`query`: 公司主营业务和高管情况如何？                                               |
| **crawl_ths_holder**   | 根据 A 股股票代码获取股东研究信息，包括股东人数、前十大流通股东、前十大股东、债券持有人、控制权结构等                                                                                                          | `crawl4ai`   | `code`: 600519<br>`query`: 股东人数和主要股东结构近期有何变化？                                       |
| **crawl_ths_operate**  | 根据 A 股股票代码获取经营分析信息，包括主营业务介绍、经营数据、主营业务构成、客户与供应商、业务回顾、产品价格等                                                                                                | `crawl4ai`   | `code`: 600519<br>`query`: 公司主营业务构成和经营状况如何？                                           |
| **crawl_ths_equity**   | 根据 A 股股票代码获取股权结构信息，包括解禁安排、总股本结构、A 股结构图、历史股权变动等                                                                                                                       | `crawl4ai`   | `code`: 600519<br>`query`: 下一年有哪些限售股将解禁？                                                 |
| **crawl_ths_capital**  | 根据 A 股股票代码获取资本运作信息，包括资金来源、项目投资、并购重组、股权投资、IPO 参与、股权转让、质押/解冻等                                                                                                | `crawl4ai`   | `code`: 600519<br>`query`: 公司近期有哪些并购或资本运作？                                             |
| **crawl_ths_worth**    | 根据 A 股股票代码获取盈利预测信息，包括业绩预测、详细预测表、研报评级等                                                                                                                                       | `crawl4ai`   | `code`: 600519<br>`query`: 未来三年的盈利预测和机构评级如何？                                         |
| **crawl_ths_news**     | 根据 A 股股票代码获取新闻公告信息，包括新闻股价关联、公告列表、热点新闻、研报列表等                                                                                                                           | `crawl4ai`   | `code`: 600519<br>`query`: 近期有哪些重要公告或新闻？                                                 |
| **crawl_ths_concept**  | 根据 A 股股票代码获取概念题材信息，包括常规概念、其他概念、题材亮点、概念对比等                                                                                                                               | `crawl4ai`   | `code`: 600519<br>`query`: 该股票涉及哪些概念题材？                                                   |
| **crawl_ths_position** | 根据 A 股股票代码获取主力持仓信息，包括机构持仓汇总、持仓明细、举牌情况、IPO 配售机构等                                                                                                                       | `crawl4ai`   | `code`: 600519<br>`query`: 机构持仓趋势和主要机构持仓情况如何？                                       |
| **crawl_ths_finance**  | 根据 A 股股票代码获取财务分析信息，包括财务诊断、财务指标、指标变动说明、资产负债构成、财务报表、杜邦分析等                                                                                                   | `crawl4ai`   | `code`: 600519<br>`query`: 公司的盈利能力和财务结构如何？                                             |
| **crawl_ths_bonus**    | 根据 A 股股票代码获取分红融资信息，包括分红诊断、分红历史、增发配售明细、增发概览、配股概览等                                                                                                                 | `crawl4ai`   | `code`: 600519<br>`query`: 历史分红情况和近期融资安排如何？                                           |
| **crawl_ths_event**    | 根据 A 股股票代码获取公司事件信息，包括高管持股变动、股东持股变动、担保明细、违规记录、机构调研、投资者互动等                                                                                                | `crawl4ai`   | `code`: 600519<br>`query`: 近期有哪些重大事件或高管持股变动？                                         |
| **crawl_ths_field**    | 根据 A 股股票代码获取行业对比信息，包括行业地位、行业新闻等                                                                                                                                                   | `crawl4ai`   | `code`: 600519<br>`query`: 公司在行业中的地位如何？                                                   |

#### 外部 MCP 服务

> **注意**：外部 MCP 服务通过 SSE（Server-Sent Events）调用。您需要在 `.env` 中配置 `BAILIAN_MCP_API_KEY` 环境变量。

| 服务名称         | 描述                             | 依赖项                | 输入参数                        |
|------------------|----------------------------------|-----------------------|---------------------------------|
| **tongyi_search**| 基于 DashScope 的 WebSearch 服务 | `BAILIAN_MCP_API_KEY` | `query`: 紫金矿业最近的新闻     |
| **bochaai_search**| 基于 DashScope 的博查 AI 搜索服务| `BAILIAN_MCP_API_KEY` | `query`: 财经新闻               |

---

## 服务器配置参数

| 参数                     | 描述                                                                                                                                                                                         | 示例                                              |
|--------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| `config`                 | 要加载的配置文件（逗号分隔）。可选项：`default`（核心流程）、`ths`（同花顺股票数据）、`stream_agent`（流式智能体）、`external_mcp`（外部 MCP 服务）                                        | `config=default,ths`                              |
| `mcp.transport`          | 传输模式：`stdio`（Claude Desktop）、`sse`（Web 应用）、`http`（RESTful）、`streamable-http`                                                                                                | `mcp.transport=stdio`                             |
| `mcp.host`               | 主机地址（仅用于 sse/http 传输）                                                                                                                                                             | `mcp.host=0.0.0.0`                                |
| `mcp.port`               | 端口号（仅用于 sse/http 传输）                                                                                                                                                               | `mcp.port=8001`                                   |
| `llm.default.model_name` | 默认 LLM 模型名称（会覆盖配置文件中的设置）                                                                                                                                                  | `llm.default.model_name=qwen3-30b-a3b-thinking-2507` |
| `disabled_flows`         | 要禁用的流程名称 JSON 数组。<br>**提示**：如果您没有某些 API 密钥（如 `tavily_search` 需要 `TAVILY_API_KEY`），请禁用对应流程                                                              | `disabled_flows='["react_agent"]'`                |

完整配置选项及默认值，请参阅 [default.yaml](./finance_mcp/config/default.yaml)。

#### 环境变量

| 变量名                   | 是否必需 | 描述                                     |
|--------------------------|----------|------------------------------------------|
| `FLOW_LLM_API_KEY`       | ✅ 是     | OpenAI 兼容 LLM 服务的 API 密钥          |
| `FLOW_LLM_BASE_URL`      | ✅ 是     | OpenAI 兼容 LLM 服务的基础 URL           |
| `DASHSCOPE_API_KEY`      | ⚠️ 可选   | 用于 DashScope 搜索和实体提取            |
| `TUSHARE_API_TOKEN`      | ⚠️ 可选   | 用于历史数据分析                         |
| `TAVILY_API_KEY`         | ⚠️ 可选   | 用于 Tavily 网络搜索                     |
| `BAILIAN_MCP_API_KEY`    | ⚠️ 可选   | 用于外部 MCP 服务                        |

---

## 支持流式的 HTTP RESTful API

Finance MCP 还支持带有流式能力的 HTTP RESTful API 模式。这使您不仅能通过 MCP 协议，还能直接通过 HTTP 端点访问工作流。

#### 步骤 1：启动 HTTP 服务器

使用 HTTP 后端启动 Finance MCP 服务器：

```bash
finance-mcp \
  config=default,stream_agent \
  backend=http \
  http.host=0.0.0.0 \
  http.port=8002 \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507
```

#### 步骤 2：发起流式 HTTP 请求

所有配置了 `stream: true` 的工作流将作为流式 HTTP 端点暴露。响应将以 Server-Sent Events (SSE) 格式实时流式返回。

示例：请求流式深度研究（灵感来自 [open_deep_research](https://github.com/langchain-ai/open_deep_research)）：

```bash
curl -X POST http://0.0.0.0:8002/langchain_deep_research \
  -H "Content-Type: application/json" \
  -d '{"query": "我想了解贵州茅台股票"}'
```

响应将实时流式返回，包含：
- 思考过程与推理逻辑
- 工具调用与中间结果
- 最终综合答案

**注意**：默认使用 DashScope 搜索，但您可以通过修改 `stream_agent.yaml` 配置文件替换为其他搜索后端（例如 Tavily）。

---

## 🤝 贡献指南

我们欢迎社区贡献！开始贡献的步骤如下：

1. 以开发模式安装本项目：

```bash
pip install -e .
```

2. 安装 pre-commit 钩子：

```bash
pip install pre-commit
pre-commit run --all-files
```

3. 提交 Pull Request。

---

## ⚖️ 许可证

本项目采用 Apache License 2.0 许可证 —— 详情请参见 [LICENSE](./LICENSE) 文件。

---

## 📈 Star 历史

[[Star History Chart](https://api.star-history.com/svg?repos=flowllm-ai/finance-mcp&type=Date)](https://www.star-history.com/#flowllm-ai/finance-mcp&Date)