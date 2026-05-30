"""
通用工具函数：重试、日志等
"""

import functools
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger("chatgptmail-2api")

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    exceptions: tuple = (Exception,),
) -> Callable[[F], F]:
    """
    重试装饰器，支持指数退避

    Args:
        max_attempts: 最大重试次数
        backoff_factor: 退避因子（秒）
        exceptions: 需要重试的异常类型
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait = backoff_factor * (2 ** attempt)
                        logger.warning(
                            "%s 第 %d 次失败，%0.1fs 后重试: %s",
                            func.__name__, attempt + 1, wait, e,
                        )
                        time.sleep(wait)
            raise last_exception  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator
