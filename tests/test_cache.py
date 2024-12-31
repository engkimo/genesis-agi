"""Test cases for cache functionality."""
import time
from pathlib import Path
from typing import Generator

import pytest
import redis

from genesis_agi.utils.cache import Cache


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """一時的なキャッシュディレクトリを作成する。"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def redis_client() -> Generator[redis.Redis, None, None]:
    """テスト用のRedisクライアントを作成する。"""
    client = redis.Redis(
        host="localhost",
        port=6379,
        db=15,  # テスト用のDB
        decode_responses=False,
    )
    try:
        client.ping()  # Redisサーバーが利用可能か確認
    except redis.ConnectionError:
        pytest.skip("Redis server is not available")
    
    yield client
    
    # テスト後のクリーンアップ
    client.flushdb()
    client.close()


class TestFileSystemCache:
    """ファイルシステムキャッシュのテスト。"""

    def test_basic_operations(self, temp_cache_dir: Path) -> None:
        """基本的な操作のテスト。"""
        cache = Cache(backend="filesystem", cache_dir=temp_cache_dir)

        # 値の設定と取得
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 存在しないキー
        assert cache.get("nonexistent") is None

        # 値の削除
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_ttl(self, temp_cache_dir: Path) -> None:
        """TTLのテスト。"""
        cache = Cache(backend="filesystem", cache_dir=temp_cache_dir)

        # TTL付きで値を設定
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"

        # TTL経過後
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_max_size(self, temp_cache_dir: Path) -> None:
        """最大サイズのテスト。"""
        cache = Cache(backend="filesystem", cache_dir=temp_cache_dir, max_size=2)

        # 最大サイズを超えるアイテムを追加
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # 最も古いアイテムが削除されていることを確認
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_metadata(self, temp_cache_dir: Path) -> None:
        """メタデータのテスト。"""
        cache = Cache(backend="filesystem", cache_dir=temp_cache_dir)

        # メタデータ付きで値を設定
        cache.set(
            "key1",
            "value1",
            metadata={"type": "test", "version": 1},
        )

        # 統計情報を確認
        stats = cache.get_stats()
        assert stats["memory_items"] == 1
        assert stats["valid_memory_items"] == 1


class TestRedisCache:
    """Redisキャッシュのテスト。"""

    def test_basic_operations(self, redis_client: redis.Redis) -> None:
        """基本的な操作のテスト。"""
        cache = Cache(
            backend="redis",
            redis_config={
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "prefix": "test:",
            },
        )

        # 値の設定と取得
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # 存在しないキー
        assert cache.get("nonexistent") is None

        # 値の削除
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_ttl(self, redis_client: redis.Redis) -> None:
        """TTLのテスト。"""
        cache = Cache(
            backend="redis",
            redis_config={
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "prefix": "test:",
            },
        )

        # TTL付きで値を設定
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"

        # TTL経過後
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_complex_data(self, redis_client: redis.Redis) -> None:
        """複雑なデータ構造のテスト。"""
        cache = Cache(
            backend="redis",
            redis_config={
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "prefix": "test:",
            },
        )

        # 複雑なデータ構造
        data = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"key": "value"},
            "boolean": True,
        }

        # 値の設定と取得
        cache.set("complex", data)
        result = cache.get("complex")
        assert result == data

    def test_prefix_isolation(self, redis_client: redis.Redis) -> None:
        """プレフィックスによる分離のテスト。"""
        cache1 = Cache(
            backend="redis",
            redis_config={
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "prefix": "test1:",
            },
        )
        cache2 = Cache(
            backend="redis",
            redis_config={
                "host": "localhost",
                "port": 6379,
                "db": 15,
                "prefix": "test2:",
            },
        )

        # 異なるプレフィックスで同じキーを使用
        cache1.set("key", "value1")
        cache2.set("key", "value2")

        # それぞれのキャッシュから正しい値が取得できることを確認
        assert cache1.get("key") == "value1"
        assert cache2.get("key") == "value2"