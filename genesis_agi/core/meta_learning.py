"""Meta-learning system for optimizing task generation and execution."""
from typing import Any, Dict, List, Optional
import logging

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.utils.cache import Cache
from genesis_agi.operators.operator_generator import OperatorGenerator

logger = logging.getLogger(__name__)


class MetaLearner:
    """メタ学習システム。タスク生成と実行の最適化を行う。"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: OperatorRegistry,
        operator_generator: Optional[OperatorGenerator] = None,
        cache: Optional[Cache] = None
    ):
        """初期化。

        Args:
            llm_client: LLMクライアント
            registry: オペレーターレジストリ
            operator_generator: オペレータージェネレーター
            cache: キャッシュ（オプション）
        """
        self.llm_client = llm_client
        self.registry = registry
        self.operator_generator = operator_generator
        self.cache = cache
        
        # メタ知識の初期化
        self.generation_strategies = {}
        self.evolution_patterns = []
        self.meta_knowledge = {
            "successful_patterns": [],
            "failed_patterns": [],
            "context_dependencies": {}
        }

    def optimize_generation_strategy(
        self,
        task_description: str,
        current_context: Dict[str, Any],
        execution_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """タスク生成戦略を最適化する。

        Args:
            task_description: タスクの説明
            current_context: 現在のコンテキスト
            execution_history: 実行履歴

        Returns:
            最適化された生成戦略
        """
        # キャッシュをチェック（キャッシュが利用可能な場合のみ）
        if self.cache is not None:
            try:
                cache_key = f"strategy:{task_description}"
                cached_strategy = self.cache.get(cache_key)
                if cached_strategy:
                    return cached_strategy
            except Exception as e:
                logger.warning(f"キャッシュの取得に失敗しました: {str(e)}")

        # LLMを使用して戦略を生成
        prompt = {
            "task": task_description,
            "context": self._prepare_context_for_json(current_context),
            "history": execution_history,
            "known_strategies": self.generation_strategies
        }
        
        response = self.llm_client.optimize_generation_strategy(prompt)
        # レスポンス全体を返す
        return response
        
        # キャッシュに保存（キャッシュが利用可能な場合のみ）
        if self.cache is not None:
            try:
                self.cache.set(cache_key, strategy)
            except Exception as e:
                logger.warning(f"キャッシュの保存に失敗しました: {str(e)}")
        
        return strategy

    def suggest_evolution_strategy(
        self,
        operator: Any,
        current_context: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """オペレーターの進化戦略を提案する。

        Args:
            operator: 対象のオペレーター
            current_context: 現在のコンテキスト
            performance_data: パフォーマンスデータ

        Returns:
            進化戦略
        """
        prompt = {
            "operator": operator.__class__.__name__,
            "context": self._prepare_context_for_json(current_context),
            "performance": performance_data,
            "evolution_patterns": self.evolution_patterns
        }
        
        response = self.llm_client.suggest_evolution_strategy(prompt)
        return response["strategy"]

    def learn_evolution_patterns(
        self,
        original_operator: Any,
        evolved_operator: Any,
        performance_data: Dict[str, Any],
        current_context: Dict[str, Any]
    ) -> None:
        """進化パターンを学習する。

        Args:
            original_operator: 元のオペレーター
            evolved_operator: 進化後のオペレーター
            performance_data: パフォーマンスデータ
            current_context: 現在のコンテキスト
        """
        pattern = {
            "original": original_operator.__class__.__name__,
            "evolved": evolved_operator.__class__.__name__,
            "performance_improvement": (
                performance_data.get("success_rate", 0) -
                performance_data.get("original_success_rate", 0)
            ),
            "context": self._prepare_context_for_json(current_context)
        }
        
        self.evolution_patterns.append(pattern)
        
        # 成功・失敗パターンの分類
        if pattern["performance_improvement"] > 0:
            self.meta_knowledge["successful_patterns"].append(pattern)
        else:
            self.meta_knowledge["failed_patterns"].append(pattern)
        
        # コンテキスト依存関係の更新
        self._update_context_dependencies(pattern)

    def _update_context_dependencies(self, pattern: Dict[str, Any]) -> None:
        """コンテキスト依存関係を更新する。

        Args:
            pattern: 進化パターン
        """
        context = pattern["context"]
        improvement = pattern["performance_improvement"]
        
        for factor, value in context.items():
            if factor not in self.meta_knowledge["context_dependencies"]:
                self.meta_knowledge["context_dependencies"][factor] = []
            
            self.meta_knowledge["context_dependencies"][factor].append({
                "pattern": pattern["evolved"],
                "impact": improvement
            })

    def _prepare_context_for_json(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """コンテキストをJSON形式に変換する。

        Args:
            context: 変換するコンテキスト

        Returns:
            JSON形式に変換されたコンテキスト
        """
        prepared_context = {}
        
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool, list, dict)):
                prepared_context[key] = value
            else:
                # 複雑なオブジェクトは文字列に変換
                prepared_context[key] = str(value)
        
        return prepared_context 