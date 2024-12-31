"""キャッシュバックエンドの実装。"""
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import msgpack
import redis

from genesis_agi.utils.cache_types import CacheItem


class CacheBackend(ABC):
    """キャッシュバックエンドの基底クラス。"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """キーに対応する値を取得する。"""
        pass

    @abstractmethod
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """キーと値のペアを保存する。"""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """キーに対応する値を削除する。"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """すべてのキャッシュをクリアする。"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を取得する。"""
        pass


class FileSystemBackend(CacheBackend):
    """ファイルシステムベースのキャッシュバックエンド。"""

    def __init__(self, cache_dir: Union[str, Path], max_size: Optional[int] = None):
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, key: str) -> Path:
        """キーに対応するファイルパスを取得する。"""
        return self.cache_dir / f"{key}.msgpack"

    def get(self, key: str) -> Optional[Any]:
        """キーに対応する値を取得する。"""
        path = self._get_path(key)
        if not path.exists():
            return None

        try:
            with path.open("rb") as f:
                data = msgpack.unpackb(f.read(), raw=False)
                item = CacheItem(
                    key=data["key"],
                    value=data["value"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    ttl=data.get("ttl"),
                    metadata=data.get("metadata"),
                )

                if item.is_expired:
                    self.delete(key)
                    return None

                return item.value
        except Exception:
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """キーと値のペアを保存する。"""
        if self.max_size is not None:
            self._enforce_max_size()

        item = CacheItem(
            key=key,
            value=value,
            created_at=datetime.now(),
            ttl=ttl,
            metadata=metadata,
        )

        data = {
            "key": item.key,
            "value": item.value,
            "created_at": item.created_at.isoformat(),
            "ttl": item.ttl,
            "metadata": item.metadata,
        }

        path = self._get_path(key)
        with path.open("wb") as f:
            f.write(msgpack.packb(data, use_bin_type=True))

    def delete(self, key: str) -> None:
        """キーに対応する値を削除する。"""
        path = self._get_path(key)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        """すべてのキャッシュをクリアする。"""
        for path in self.cache_dir.glob("*.msgpack"):
            path.unlink()

    def get_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を取得する。"""
        total_items = 0
        valid_items = 0
        total_size = 0

        for path in self.cache_dir.glob("*.msgpack"):
            total_items += 1
            total_size += path.stat().st_size

            try:
                with path.open("rb") as f:
                    data = msgpack.unpackb(f.read(), raw=False)
                    item = CacheItem(
                        key=data["key"],
                        value=data["value"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        ttl=data.get("ttl"),
                        metadata=data.get("metadata"),
                    )
                    if not item.is_expired:
                        valid_items += 1
            except Exception:
                pass

        return {
            "total_items": total_items,
            "valid_items": valid_items,
            "total_size_bytes": total_size,
            "cache_dir": str(self.cache_dir),
            "max_size": self.max_size,
        }

    def _enforce_max_size(self) -> None:
        """最大サイズを超えないようにキャッシュを管理する。"""
        if self.max_size is None:
            return

        items: List[tuple[Path, datetime]] = []
        current_size = 0

        for path in self.cache_dir.glob("*.msgpack"):
            try:
                with path.open("rb") as f:
                    data = msgpack.unpackb(f.read(), raw=False)
                    created_at = datetime.fromisoformat(data["created_at"])
                    items.append((path, created_at))
                    current_size += 1
            except Exception:
                path.unlink()  # 破損したファイルを削除

        if current_size > self.max_size:
            # 古い順にソート
            items.sort(key=lambda x: x[1])
            # 超過分を削除
            for path, _ in items[: current_size - self.max_size]:
                path.unlink()


class RedisBackend(CacheBackend):
    """Redisベースのキャッシュバックエンド。"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "",
        **kwargs,
    ):
        self.prefix = prefix
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            **kwargs,
        )

    def _get_key(self, key: str) -> str:
        """プレフィックス付きのキーを取得する。"""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """キーに対応する値を取得する。"""
        full_key = self._get_key(key)
        data = self.client.get(full_key)
        if data is None:
            return None

        try:
            item_data = msgpack.unpackb(data, raw=False)
            item = CacheItem(
                key=item_data["key"],
                value=item_data["value"],
                created_at=datetime.fromisoformat(item_data["created_at"]),
                ttl=item_data.get("ttl"),
                metadata=item_data.get("metadata"),
            )

            if item.is_expired:
                self.delete(key)
                return None

            return item.value
        except Exception:
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """キーと値のペアを保存する。"""
        item = CacheItem(
            key=key,
            value=value,
            created_at=datetime.now(),
            ttl=ttl,
            metadata=metadata,
        )

        data = {
            "key": item.key,
            "value": item.value,
            "created_at": item.created_at.isoformat(),
            "ttl": item.ttl,
            "metadata": item.metadata,
        }

        full_key = self._get_key(key)
        packed_data = msgpack.packb(data, use_bin_type=True)
        if ttl is not None:
            self.client.setex(full_key, ttl, packed_data)
        else:
            self.client.set(full_key, packed_data)

    def delete(self, key: str) -> None:
        """キーに対応する値を削除する。"""
        full_key = self._get_key(key)
        self.client.delete(full_key)

    def clear(self) -> None:
        """すべてのキャッシュをクリアする。"""
        pattern = f"{self.prefix}*"
        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern)
            if keys:
                self.client.delete(*keys)
            if cursor == 0:
                break

    def get_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を取得する。"""
        pattern = f"{self.prefix}*"
        total_items = 0
        valid_items = 0
        memory_usage = 0

        cursor = 0
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern)
            for key in keys:
                total_items += 1
                try:
                    data = self.client.get(key)
                    if data is not None:
                        memory_usage += len(data)
                        item_data = msgpack.unpackb(data, raw=False)
                        item = CacheItem(
                            key=item_data["key"],
                            value=item_data["value"],
                            created_at=datetime.fromisoformat(item_data["created_at"]),
                            ttl=item_data.get("ttl"),
                            metadata=item_data.get("metadata"),
                        )
                        if not item.is_expired:
                            valid_items += 1
                except Exception:
                    pass

            if cursor == 0:
                break

        return {
            "total_items": total_items,
            "valid_items": valid_items,
            "memory_usage_bytes": memory_usage,
            "prefix": self.prefix,
        } 