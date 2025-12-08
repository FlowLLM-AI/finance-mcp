"""Service runner for finance-mcp service.

This module provides a context manager for starting and managing the finance-mcp
service as a subprocess, with automatic cleanup on exit.
"""

import socket
import subprocess
import time
from typing import List, Optional

from loguru import logger


class FinanceMcpServiceRunner:
    """Context manager for running finance-mcp service as a subprocess.

    This class manages the lifecycle of a finance-mcp service process:
    - Starts the service with specified arguments
    - Waits for the service to be ready
    - Provides cleanup on exit

    Example:
        ```python
        service_args = [
            "finance-mcp",
            "config=default,ths",
            "mcp.transport=http",
            "llm.default.model_name=qwen3-30b-a3b-thinking-2507",
        ]

        with FinanceMcpServiceRunner(service_args, port=8001) as service:
            # Service is ready, use it here
            print(f"Service is running on port {service.port}")
        # Service is automatically terminated on exit
        ```
    """

    def __init__(
        self,
        service_args: List[str] | str,
        port: int = 8001,
        host: str = "0.0.0.0",
        max_wait: int = 3600,
        check_interval: float = 0.5,
        stdout=None,
        stderr=None,
        **popen_kwargs,
    ):
        """Initialize the service runner.

        Args:
            service_args: List of command-line arguments to start the service
            port: Port number to check for service readiness
            host: Host address (default: "0.0.0.0")
            max_wait: Maximum time to wait for service to start (seconds)
            check_interval: Time between readiness checks (seconds)
            stdout: stdout for subprocess (None = terminal, subprocess.PIPE = capture)
            stderr: stderr for subprocess (None = terminal, subprocess.PIPE = capture)
            **popen_kwargs: Additional keyword arguments passed to subprocess.Popen
        """
        if isinstance(service_args, str):
            self.service_args = [service_args]
        elif isinstance(service_args, list):
            self.service_args = service_args
        else:
            raise ValueError("service_args must be a list or a string")

        self.service_args.extend(
            [
                f"mcp.port={port}",
                f"mcp.host={host}",
            ],
        )

        self.port = port
        self.host = host
        self.max_wait = max_wait
        self.check_interval = check_interval
        self.stdout = stdout
        self.stderr = stderr
        self.popen_kwargs = popen_kwargs

        self.process: Optional[subprocess.Popen] = None
        self._is_ready = False

    def _wait_for_service(self) -> bool:
        """Wait for the service to be ready by checking if the port is listening.

        Returns:
            True if service is ready, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < self.max_wait:
            try:
                # Try to connect to the port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.host, self.port))
                sock.close()
                if result == 0:
                    logger.info(f"Service is ready on {self.host}:{self.port}")
                    # Give it a bit more time to fully initialize
                    time.sleep(1)
                    return True
            except Exception:
                pass
            time.sleep(self.check_interval)
        return False

    def _cleanup_process(self):
        """Clean up the service process."""
        if self.process is None:
            return

        try:
            # Check if process is still running
            if self.process.poll() is None:
                logger.info("Terminating service process...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully, killing...")
                    self.process.kill()
                    self.process.wait()
            else:
                # Process has already exited
                logger.debug(f"Service process already exited with code: {self.process.returncode}")
        except Exception as e:
            logger.exception(f"Error terminating process: {e}")
        finally:
            self.process = None
            self._is_ready = False

    def __enter__(self) -> "FinanceMcpServiceRunner":
        """Start the service and wait for it to be ready.

        Returns:
            self

        Raises:
            RuntimeError: If service fails to start within timeout
        """
        logger.info(f"Starting finance-mcp service with args: {self.service_args}")

        # Start service in background (non-blocking)
        try:
            self.process = subprocess.Popen(
                self.service_args,
                stdout=self.stdout,
                stderr=self.stderr,
                text=True,
                **self.popen_kwargs,
            )
        except Exception as e:
            logger.exception(f"Failed to start service: {e}")
            raise RuntimeError(f"Failed to start service: {e}") from e

        # Wait for service to be ready
        logger.info(f"Waiting for service to start on port {self.port}...")
        if not self._wait_for_service():
            logger.error("Service failed to start within timeout")
            self._cleanup_process()

            # Try to get error information if process has exited
            if self.process and self.process.poll() is not None:
                logger.error(f"Service process exited with code: {self.process.returncode}")

            raise RuntimeError(
                f"Service failed to start within {self.max_wait} seconds. " f"Check service logs for details.",
            )

        self._is_ready = True
        logger.info("Service is ready and running")
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        """Clean up the service process on exit.

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)
        """
        self._cleanup_process()
        return False  # Don't suppress exceptions

    @property
    def is_ready(self) -> bool:
        """Check if the service is ready.

        Returns:
            True if service is ready, False otherwise
        """
        return self._is_ready

    @property
    def is_running(self) -> bool:
        """Check if the service process is still running.

        Returns:
            True if process is running, False otherwise
        """
        if self.process is None:
            return False
        return self.process.poll() is None
