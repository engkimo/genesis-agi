"""キャッシュの実装。"""
from pathlib import Path
from typing import Any, Dict, Optional, Union

from genesis_agi.utils.cache_backends import (
    CacheBackend,
    FileSystemBackend,
    RedisBackend,
)


class Cache:
    """キャッシュクラス。"""

    def __init__(
        self,
        backend: str = "filesystem",
        cache_dir: Optional[Union[str, Path]] = None,
        redis_config: Optional[Dict[str, Any]] = None,
        max_size: Optional[int] = None,
    ):
        """初期化。

        Args:
            backend: バックエンドの種類 ("filesystem" or "redis")
            cache_dir: キャッシュディレクトリ（filesystemバックエンド用）
            redis_config: Redisの設定（redisバックエンド用）
            max_size: キャッシュの最大サイズ（filesystemバックエンド用）
        """
        if backend == "filesystem":
            if cache_dir is None:
                cache_dir = Path.home() / ".genesis_agi" / "cache"
            self.backend: CacheBackend = FileSystemBackend(
                cache_dir=cache_dir,
                max_size=max_size,
            )
        elif backend == "redis":
            if redis_config is None:
                redis_config = {}
            self.backend = RedisBackend(**redis_config)
        else:
            raise ValueError(f"Unsupported backend: {backend}")

    def get(self, key: str) -> Optional[Any]:
        """キーに対応する値を取得する。"""
        return self.backend.get(key)

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """キーと値のペアを保存する。"""
        self.backend.set(key, value, ttl=ttl, metadata=metadata)

    def delete(self, key: str) -> None:
        """キーに対応する値を削除する。"""
        self.backend.delete(key)

    def clear(self) -> None:
        """すべてのキャッシュをクリアする。"""
        self.backend.clear()

    def get_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を取得する。"""
        return self.backend.get_stats() 