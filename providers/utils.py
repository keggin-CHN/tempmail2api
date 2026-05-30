"""
通用工具函数：重试、日志、ETag 缓存
"""

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

logger = logging.getLogger("chatgptmail-2api")

F = TypeVar("F", bound=Callable[..., Any])


class TempMailError(Exception):
    """临时邮箱操作基础异常"""
    pass


class EmailGenerateError(TempMailError):
    """生成邮箱失败"""
    pass


class EmailFetchError(TempMailError):
    """获取邮件失败"""
    pass


class RateLimitError(TempMailError):
    """请求频率超限"""
    def __init__(self, retry_after: Optional[float] = None):
        self.retry_after = retry_after
        super().__init__(f"速率限制，建议 {retry_after}s 后重试" if retry_after else "速率限制")


class ETagCache:
    """
    ETag 缓存管理器
    
    - 按 key（通常是邮箱地址）存储 ETag
    - 支持 TTL 自动过期
    - 记录 hit / miss 统计
    """

    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, Tuple[str, float]] = {}  # key -> (etag, expire_ts)
        self._ttl = ttl_seconds
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[str]:
        """返回缓存的 ETag，过期或不存在返回 None"""
        entry = self._cache.get(key)
        if entry is None:
            self.misses += 1
            return None
        etag, expire_ts = entry
        if time.time() > expire_ts:
            del self._cache[key]
            self.misses += 1
            return None
        self.hits += 1
        return etag

    def put(self, key: str, etag: str) -> None:
        """存储 ETag"""
        self._cache[key] = (etag, time.time() + self._ttl)

    def invalidate(self, key: str) -> None:
        """手动失效"""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """清空全部缓存"""
        self._cache.clear()

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0

    def stats(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{self.hit_rate:.1%}",
            "cached_keys": len(self._cache),
        }


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
                            "%s 第 %d/%d 次失败，%0.1fs 后重试: %s",
                            func.__name__, attempt + 1, max_attempts, wait, e,
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            "%s 第 %d/%d 次失败，已耗尽重试次数: %s",
                            func.__name__, attempt + 1, max_attempts, e,
                        )
            raise last_exception  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator
