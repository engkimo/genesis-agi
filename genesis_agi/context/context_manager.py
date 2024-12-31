"""コンテキストマネージャー。"""
from typing import Any, Dict, List, Optional

from genesis_agi.utils.cache import Cache
from genesis_agi.utils.semantic_search import SemanticSearch


class ContextManager:
    """コンテキストマネージャー。"""

    def __init__(
        self,
        cache: Optional[Cache] = None,
        semantic_search: Optional[SemanticSearch] = None,
    ):
        """初期化。

        Args:
            cache: キャッシュ
            semantic_search: セマンティック検索
        """
        self.cache = cache
        self.semantic_search = semantic_search or SemanticSearch()
        self.prompt_templates: Dict[str, str] = {}
        self.parameters: Dict[str, Any] = {}
        self.strategies: Dict[str, Dict[str, Any]] = {}
        self.context: Dict[str, Any] = {}

    def add_to_context(self, key: str, value: Any) -> None:
        """コンテキストに情報を追加する。

        Args:
            key: キー
            value: 値
        """
        self.context[key] = value

        # キャッシュに保存
        if self.cache:
            self.cache.set(f"context:{key}", value)

        # セマンティック検索用のインデックスを更新
        if isinstance(value, (str, dict, list)):
            self.semantic_search.index_document(
                key,
                str(value),
                metadata={"type": "context", "key": key},
            )

    def get_context(self, key: str) -> Optional[Any]:
        """コンテキストから情報を取得する。

        Args:
            key: キー

        Returns:
            値
        """
        # まずメモリから取得
        value = self.context.get(key)
        if value is not None:
            return value

        # キャッシュから取得
        if self.cache:
            value = self.cache.get(f"context:{key}")
            if value is not None:
                self.context[key] = value
                return value

        return None

    def get_relevant_context(
        self,
        query: str,
        limit: int = 5,
        min_score: float = 0.5,
    ) -> Dict[str, Any]:
        """クエリに関連するコンテキストを取得する。

        Args:
            query: クエリ
            limit: 取得する最大数
            min_score: 最小類似度スコア

        Returns:
            関連するコンテキスト
        """
        results = self.semantic_search.search(
            query,
            limit=limit,
            min_score=min_score,
            filter_metadata={"type": "context"},
        )

        relevant_context = {}
        for result in results:
            key = result.metadata["key"]
            value = self.get_context(key)
            if value is not None:
                relevant_context[key] = value

        return relevant_context

    def update_prompt_template(self, template_name: str, new_template: str) -> None:
        """プロンプトテンプレートを更新する。

        Args:
            template_name: テンプレート名
            new_template: 新しいテンプレート
        """
        self.prompt_templates[template_name] = new_template

        # キャッシュに保存
        if self.cache:
            self.cache.set(
                f"prompt_template:{template_name}",
                new_template,
                metadata={"type": "prompt_template"},
            )

        # セマンティック検索用のインデックスを更新
        self.semantic_search.index_document(
            f"prompt_template:{template_name}",
            new_template,
            metadata={"type": "prompt_template", "name": template_name},
        )

    def update_parameter(self, parameter_name: str, new_value: Any) -> None:
        """パラメータを更新する。

        Args:
            parameter_name: パラメータ名
            new_value: 新しい値
        """
        self.parameters[parameter_name] = new_value

        # キャッシュに保存
        if self.cache:
            self.cache.set(
                f"parameter:{parameter_name}",
                new_value,
                metadata={"type": "parameter"},
            )

    def update_strategy(self, strategy_name: str, new_strategy: Dict[str, Any]) -> None:
        """戦略を更新する。

        Args:
            strategy_name: 戦略名
            new_strategy: 新しい戦略
        """
        self.strategies[strategy_name] = new_strategy

        # キャッシュに保存
        if self.cache:
            self.cache.set(
                f"strategy:{strategy_name}",
                new_strategy,
                metadata={"type": "strategy"},
            )

        # セマンティック検索用のインデックスを更新
        self.semantic_search.index_document(
            f"strategy:{strategy_name}",
            str(new_strategy),
            metadata={"type": "strategy", "name": strategy_name},
        ) 