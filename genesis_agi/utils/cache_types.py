"""キャッシュの共通型定義。"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class CacheItem:
    """キャッシュアイテムを表すクラス。"""

    key: str
    value: Any
    created_at: datetime
    ttl: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

    @property
    def is_expired(self) -> bool:
        """TTLに基づいて有効期限切れかどうかを判定する。"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl 