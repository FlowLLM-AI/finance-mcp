"""HTTP-based integration test for the finance-mcp service.

This module starts the finance-mcp service via `FinanceMcpServiceRunner` and
uses `curl` as a subprocess to hit various HTTP endpoints. Responses are
streamed to stdout to simulate a real client consuming server-sent output.
"""

import json
import subprocess
import time

from loguru import logger

from finance_mcp.core.utils.service_runner import FinanceMcpServiceRunner

# Service configuration
service_args = [
    "finance-mcp",
    "config=default,stream_agent",
    "llm.default.model_name=qwen3-30b-a3b-thinking-2507",
]

# MCP client configuration
host = "0.0.0.0"
port = 8002


def test_http_service(endpoint: str, data: str) -> None:
    """Call a streaming HTTP endpoint using curl and print the response.

    Args:
        endpoint: API endpoint path (for example ``"conduct_research"``).
        data: JSON-encoded request body to send to the endpoint.
    """

    url = f"http://{host}:{port}/{endpoint}"
    curl_cmd = [
        "curl",
        "-X",
        "POST",
        url,
        "--no-buffer",
        "-N",
        "-s",
        "-S",
        "-H",
        "Content-Type: application/json",
        "-d",
        data,
    ]

    logger.info(f"Executing curl command: {' '.join(curl_cmd)}")
    logger.info("=" * 80)

    # Execute curl command with streaming output so we can inspect chunks
    with subprocess.Popen(
        curl_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=-1,
    ) as process:

        # Read and print output in chunks for real-time streaming feedback.
        chunk_size = 1024
        while True:
            chunk = process.stdout.read(chunk_size)
            if not chunk:
                if process.poll() is not None:
                    break
                time.sleep(0.01)
                continue

            print(chunk, end="", flush=True)

            # for x in chunk:
            #     print(x, end='', flush=True)
            #     time.sleep(0.01)

        process.wait()
        logger.info("\n" + "=" * 80)
        logger.info(f"Curl command completed with return code: {process.returncode}")


def main() -> None:
    """
    Start the finance-mcp HTTP service and exercise selected endpoints.

    Example: Streaming Deep Research

    finance-mcp \
      config=default,stream_agent \
      backend=http \
      http.host=0.0.0.0 \
      http.port=8002 \
      llm.default.model_name=qwen3-30b-a3b-thinking-2507

    curl -X POST http://0.0.0.0:8002/langchain_deep_research \
      -H "Content-Type: application/json" \
      -d '{"query": "茅台怎么样？"}'

    """

    with FinanceMcpServiceRunner(
        service_args,
        host=host,
        port=port,
    ) as service:
        logger.info(f"Service is running on port {service.port}")
        logger.info("Waiting a moment for service to fully initialize...")
        time.sleep(2)  # Give service a moment to fully initialize

        for endpoint, data in [
            # ("conduct_research", {"research_topic": "茅台怎么样？"}),
            # ("dashscope_deep_research", {"query": "茅台怎么样？"}),
            ("langchain_deep_research", {"query": "茅台怎么样？"}),
        ]:
            test_http_service(
                endpoint=endpoint,
                data=json.dumps(data, ensure_ascii=False),
            )


if __name__ == "__main__":
    main()
