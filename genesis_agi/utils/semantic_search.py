"""セマンティック検索の実装。"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from genesis_agi.utils.cache import Cache


@dataclass
class SearchResult:
    """検索結果を表すクラス。"""

    id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class SemanticSearch:
    """セマンティック検索クラス。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-ada-002",
        cache: Optional[Cache] = None,
    ):
        """初期化。

        Args:
            api_key: OpenAI APIキー
            model: 埋め込みモデル名
            cache: キャッシュ
        """
        self.api_key = api_key
        if api_key:
            openai.api_key = api_key
        self.model = model
        self.cache = cache
        self.documents: Dict[str, str] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def _get_embedding(self, text: str) -> np.ndarray:
        """テキストの埋め込みベクトルを取得する。

        Args:
            text: テキスト

        Returns:
            埋め込みベクトル
        """
        # キャッシュをチェック
        if self.cache:
            cache_key = f"embedding:{hash(text)}"
            cached_embedding = self.cache.get(cache_key)
            if cached_embedding is not None:
                return np.array(cached_embedding)

        # 埋め込みベクトルを取得
        response = openai.Embedding.create(
            input=text,
            model=self.model,
        )
        embedding = np.array(response["data"][0]["embedding"])

        # キャッシュに保存
        if self.cache:
            self.cache.set(cache_key, embedding.tolist(), ttl=86400)  # 24時間キャッシュ

        return embedding

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """コサイン類似度を計算する。

        Args:
            a: ベクトル1
            b: ベクトル2

        Returns:
            コサイン類似度
        """
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def index_document(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """ドキュメントをインデックスに追加する。

        Args:
            doc_id: ドキュメントID
            content: ドキュメントの内容
            metadata: メタデータ
        """
        self.documents[doc_id] = content
        self.embeddings[doc_id] = self._get_embedding(content)
        self.metadata[doc_id] = metadata or {}

        # キャッシュに保存
        if self.cache:
            self.cache.set(
                f"document:{doc_id}",
                {
                    "content": content,
                    "embedding": self.embeddings[doc_id].tolist(),
                    "metadata": self.metadata[doc_id],
                },
                metadata={"type": "document"},
            )

    def remove_document(self, doc_id: str) -> None:
        """ドキュメントをインデックスから削除する。

        Args:
            doc_id: ドキュメントID
        """
        self.documents.pop(doc_id, None)
        self.embeddings.pop(doc_id, None)
        self.metadata.pop(doc_id, None)

        # キャッシュから削除
        if self.cache:
            self.cache.delete(f"document:{doc_id}")

    def search(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """クエリに関連するドキュメントを検索する。

        Args:
            query: 検索クエリ
            limit: 返す結果の最大数
            min_score: 最小類似度スコア
            filter_metadata: メタデータによるフィルタリング条件

        Returns:
            検索結果のリスト
        """
        if not self.embeddings:
            return []

        # クエリの埋め込みベクトルを取得
        query_embedding = self._get_embedding(query)

        # 類似度を計算
        results = []
        for doc_id, doc_embedding in self.embeddings.items():
            # メタデータフィルタリング
            if filter_metadata:
                doc_metadata = self.metadata[doc_id]
                if not all(
                    doc_metadata.get(k) == v for k, v in filter_metadata.items()
                ):
                    continue

            score = self._cosine_similarity(query_embedding, doc_embedding)
            if score >= min_score:
                results.append(
                    SearchResult(
                        id=doc_id,
                        content=self.documents[doc_id],
                        score=score,
                        metadata=self.metadata[doc_id],
                    )
                )

        # スコアでソート
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """インデックスの統計情報を取得する。

        Returns:
            統計情報
        """
        return {
            "total_documents": len(self.documents),
            "total_embeddings": len(self.embeddings),
            "model": self.model,
            "metadata_keys": list(
                set(key for metadata in self.metadata.values() for key in metadata.keys())
            ),
        } 