<p align="center">
 <img src="docs/figure/logo.png" alt="Finance MCP Logo" width="50%">
</p>

<p align="center">
  <strong>MCP-Server for Financial Research Agents</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/finance-mcp/"><img src="https://img.shields.io/badge/python-3.10+-blue" alt="Python Version"></a>
  <a href="https://pypi.org/project/finance-mcp/"><img src="https://img.shields.io/pypi/v/finance-mcp.svg?logo=pypi" alt="PyPI Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-black" alt="License"></a>
  <a href="https://github.com/flowllm-ai/finance-mcp"><img src="https://img.shields.io/github/stars/flowllm-ai/finance-mcp?style=social" alt="GitHub Stars"></a>
</p>

<p align="center">
  <em><sub>If you have any financial data integration requirements, please submit an issue.</sub></em>
</p>

<p align="center">
  <a href="https://flowllm-ai.github.io/finance-mcp/">简体中文</a> | English
</p>

---

## 📖 Project Overview

Finance MCP is an intelligent agent toolkit and MCP (Model Context Protocol) server designed for financial research scenarios. Built on the [FlowLLM](https://github.com/flowllm-ai/flowllm) framework, it integrates components such as [Crawl4AI](https://github.com/unclecode/crawl4ai), Tushare, Tavily/DashScope search, and more, helping you quickly build professional financial research agent systems.

### 🎯 Core Features

Finance MCP aims to provide a complete toolchain for financial research scenarios, supporting:

- **🔬 Deep Research Agents**: Financial research agents based on ReAct architecture, supporting multi-turn retrieval, reasoning, and analysis
- **🌐 Web Content Scraping**: Intelligent web scraping and long-text extraction capabilities based on Crawl4AI
- **📊 Financial Data Acquisition**: Integration with Tushare for historical data calculation and analysis
- **🔍 Multi-Source Search**: Support for multiple search backends including Tavily, DashScope, and more
- **🏢 TongHuaShun Data Integration**: Provides 13+ TongHuaShun data scraping flows (company profiles, shareholder research, financial analysis, etc.)
- **⚙️ Composable Workflows**: Flexibly combine operators through YAML configuration to build customized research workflows

### 💡 Why Choose Finance MCP?

- ✅ **Zero-Code Configuration**: Combine operators through YAML configuration files without writing service code
- ✅ **Out-of-the-Box**: Pre-configured 20+ financial research-related flows covering common research scenarios
- ✅ **Multi-Protocol Support**: Supports both MCP (stdio/SSE/HTTP) and HTTP RESTful API
- ✅ **Smart Caching**: Built-in multi-level caching mechanism to improve efficiency and reduce costs
- ✅ **Modular Design**: Each functional module is independently configurable, supporting enable/disable as needed

---

## 🚀 MCP Services

### Default MCP Services

| Service Name              | Description                                                                              | Dependencies           | Input Parameters                                                                 |
|---------------------------|------------------------------------------------------------------------------------------|------------------------|----------------------------------------------------------------------------------|
| **history_calculate**     | Price-volume analysis based on Tushare A-share historical data                          | `TUSHARE_API_TOKEN`    | `code`: '601899'<br>`query`: "How much did it rise in the past week? Any MACD golden cross?" |
| **crawl_url**             | Scrape and parse web content                                                            | `crawl4ai`             | `url`: `https://example.com`                                                     |
| **extract_entities_code** | Identify financial entities from text and complete stock codes (currently uses dashscope_search, replaceable) | `DASHSCOPE_API_KEY`    | `query`: "I want to learn about Kweichow Moutai stock"                          |
| **execute_code**          | Execute arbitrary Python code                                                           | -                      | `code`: `print(1+1)`                                                             |
| **execute_shell**         | Execute shell commands                                                                   | -                      | `command`: `ls`                                                                   |
| **dashscope_search**      | Web search based on DashScope                                                           | `DASHSCOPE_API_KEY`    | `query`: "Recent news about Zijin Mining"                                        |
| **tavily_search**         | Web search based on Tavily                                                              | `TAVILY_API_KEY`       | `query`: "financial news"                                                        |
| **mock_search**           | Mock search for LLM simulation                                                           | -                      | `query`: "test query"                                                            |
| **react_agent**           | ReAct agent combining multiple tools for answering complex questions                    | -                      | `query`: "Help me analyze Zijin Mining's trend for the next week"                |

### TongHuaShun MCP Services

> **Note**: These MCP services are implemented via crawl4ai. High concurrency may result in IP blocking.

| Service Name              | Description                                                                                                                                    | Dependencies | Input Parameters Example                                                                      |
|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|--------------|-----------------------------------------------------------------------------------------------|
| **crawl_ths_company**      | Get company profile information by A-share stock code, including details, executive introductions, issuance-related info, subsidiaries, etc., and return query-relevant information | `crawl4ai`    | `code`: "600519"<br>`query`: "What are the company's main business and executive situation?"  |
| **crawl_ths_holder**       | Get shareholder research information by A-share stock code, including shareholder count, top 10 circulating shareholders, top 10 shareholders, bondholders, controlling hierarchy, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "How have shareholder count and major shareholder structure changed recently?" |
| **crawl_ths_operate**      | Get operational analysis information by A-share stock code, including main business introduction, operational data, main business composition, customers & suppliers, business review, product prices, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What is the company's main business composition and operational situation?" |
| **crawl_ths_equity**       | Get equity structure information by A-share stock code, including unlock schedule, total equity composition, A-share structure chart, historical equity changes, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What restricted shares will be unlocked in the next year?"      |
| **crawl_ths_capital**      | Get capital operation information by A-share stock code, including funding sources, project investments, M&A, equity investments, IPO participation, equity transfers, pledge/unfreeze, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What recent M&A or capital operations has the company had?"    |
| **crawl_ths_worth**        | Get earnings forecast information by A-share stock code, including performance forecasts, detailed forecast tables, research report ratings, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What are the earnings forecasts and institutional ratings for the next three years?" |
| **crawl_ths_news**         | Get news and announcements by A-share stock code, including news-price correlation, announcement lists, hot news, research report lists, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What are the recent important announcements or news?"          |
| **crawl_ths_concept**      | Get concept and theme information by A-share stock code, including regular concepts, other concepts, theme highlights, concept comparison, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What concept themes does this stock involve?"                  |
| **crawl_ths_position**    | Get major position information by A-share stock code, including institutional holdings summary, holding details, takeover situations, IPO allocation institutions, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What is the institutional holding trend and major institutional holdings?" |
| **crawl_ths_finance**      | Get financial analysis information by A-share stock code, including financial diagnosis, financial indicators, indicator change explanations, asset-liability composition, financial reports, DuPont analysis, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What is the company's profitability and financial structure?"  |
| **crawl_ths_bonus**        | Get dividend and financing information by A-share stock code, including dividend diagnosis, dividend history, additional issuance allocation details, additional issuance overview, rights issue overview, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What is the historical dividend situation and recent financing arrangements?" |
| **crawl_ths_event**        | Get company events by A-share stock code, including executive shareholding changes, shareholder shareholding changes, guarantee details, violations, institutional research, investor interactions, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What are the recent major events or executive shareholding changes?" |
| **crawl_ths_field**        | Get industry comparison information by A-share stock code, including industry position, industry news, etc. | `crawl4ai`    | `code`: "600519"<br>`query`: "What is the company's position in its industry?"               |

### External MCP Services

> **Note**: External MCP services are called via SSE (Server-Sent Events). You need to configure the `BAILIAN_MCP_API_KEY` environment variable in `.env`.

| Service Name       | Description                                    | Dependencies           | Input Parameters Example                    |
|--------------------|------------------------------------------------|------------------------|--------------------------------------------|
| **tongyi_search**  | WebSearch service based on DashScope           | `BAILIAN_MCP_API_KEY`  | `query`: "Recent news about Zijin Mining" |
| **bochaai_search** | BochaAI search service based on DashScope      | `BAILIAN_MCP_API_KEY`  | `query`: "financial news"                  |

---

## 🚀 Quick Start

### Installation

Install Finance MCP using pip:

```bash
pip install finance-mcp
```

Or using uv:

```bash
uv pip install finance-mcp
```

### MCP Client Configuration

Add this configuration to your MCP client (e.g., Claude Desktop, Cursor):

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

### Environment Setup

> **Note**: If you're using MCP client configuration (see MCP Client Configuration section above), you don't need to create a `.env` file. Simply fill in the environment variables in the `env` field of your `mcpServers` configuration.

For HTTP server mode, configure environment variables:

1. Copy `example.env` to `.env`:

```bash
cp example.env .env
```

2. Edit `.env` and fill in your API keys:

```bash
FLOW_LLM_API_KEY=your_api_key_here
FLOW_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Optional: Uncomment if you plan to use corresponding features
# DASHSCOPE_API_KEY=your_dashscope_api_key
# TUSHARE_API_TOKEN=your_tushare_token
# TAVILY_API_KEY=your_tavily_api_key
# BAILIAN_MCP_API_KEY=your_bailian_mcp_api_key
```

### Deploy HTTP Server

Start the HTTP server with SSE transport:

```bash
finance-mcp \
  config=default,ths \
  mcp.transport=sse \
  mcp.host=0.0.0.0 \
  mcp.port=8001 \
  llm.default.model_name=qwen3-30b-a3b-thinking-2507 \
  disabled_flows='["tavily_search","mock_search","react_agent"]'
```

The service will be available at: `http://0.0.0.0:8001/sse`

### Configuration Parameters

| Parameter                | Description                                                                                                                                                                                 | Example                                                |
|--------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| `config`                 | Configuration files to load (comma-separated). Available: `default` (core flows), `ths` (TongHuaShun stock data), `stream_agent` (streaming agents), `external_mcp` (external MCP services) | config=default,ths                                     |
| `mcp.transport`          | Transport mode: `stdio` (Claude Desktop), `sse` (web apps), `http` (RESTful), `streamable-http`                                                                                             | mcp.transport=stdio                                    |
| `mcp.host`               | Host address (for sse/http transports only)                                                                                                                                                 | mcp.host=0.0.0.0                                       |
| `mcp.port`               | Port number (for sse/http transports only)                                                                                                                                                  | mcp.port=8001                                          |
| `llm.default.model_name` | Default LLM model name (overrides config file)                                                                                                                                              | llm.default.model_name=<br>qwen3-30b-a3b-thinking-2507 |
| `disabled_flows`         | JSON array of flow names to disable. **Tip**: Disable flows if you don't have the required API keys (e.g., `tavily_search` requires `TAVILY_API_KEY`)                                       | disabled_flows=<br>'["react_agent"]'                   |

### Environment Variables

| Variable              | Required    | Description                                |
|-----------------------|-------------|--------------------------------------------|
| `FLOW_LLM_API_KEY`    | ✅ Yes       | API key for OpenAI-compatible LLM service  |
| `FLOW_LLM_BASE_URL`   | ✅ Yes       | Base URL for OpenAI-compatible LLM service |
| `DASHSCOPE_API_KEY`   | ⚠️ Optional | For DashScope search and entity extraction |
| `TUSHARE_API_TOKEN`   | ⚠️ Optional | For historical data analysis               |
| `TAVILY_API_KEY`      | ⚠️ Optional | For Tavily web search                      |
| `BAILIAN_MCP_API_KEY` | ⚠️ Optional | For external MCP services                  |

---

## 🤝 Contributing

We welcome contributions! To get started:

1. Install the package in development mode:

```bash
pip install -e .
```

2. Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit run --all-files
```

3. Submit a pull request with your changes.

---

## ⚖️ License

This project is licensed under the Apache License 2.0 - see the [LICENSE](./LICENSE) file for details.

---

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=flowllm-ai/finance-mcp&type=Date)](https://www.star-history.com/#flowllm-ai/finance-mcp&Date)
