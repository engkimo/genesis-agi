"""メタ学習システム。"""
from typing import Any, Dict, List, Optional, Type
from datetime import datetime
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.operators.operator_generator import OperatorGenerator
from genesis_agi.utils.cache import Cache
from genesis_agi.operators.base_operator import BaseOperator


class GenerationStrategy:
    """オペレーター生成戦略。"""

    def __init__(
        self,
        strategy_type: str,
        parameters: Dict[str, Any],
        success_rate: float = 0.0,
        last_updated: Optional[datetime] = None
    ):
        """初期化。"""
        self.strategy_type = strategy_type
        self.parameters = parameters
        self.success_rate = success_rate
        self.last_updated = last_updated or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する。"""
        return {
            "strategy_type": self.strategy_type,
            "parameters": self.parameters,
            "success_rate": self.success_rate,
            "last_updated": self.last_updated.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationStrategy':
        """辞書からインスタンスを生成する。"""
        return cls(
            strategy_type=data["strategy_type"],
            parameters=data["parameters"],
            success_rate=data["success_rate"],
            last_updated=datetime.fromisoformat(data["last_updated"])
        )


class MetaLearner:
    """メタ学習を行うクラス。"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: OperatorRegistry,
        operator_generator: Optional[OperatorGenerator] = None,
        cache: Optional[Cache] = None
    ):
        """初期化。"""
        self.llm_client = llm_client
        self.registry = registry
        self.operator_generator = operator_generator
        self.cache = cache
        self.generation_strategies: Dict[str, GenerationStrategy] = {}
        self.evolution_patterns: List[Dict[str, Any]] = []
        self.meta_knowledge: Dict[str, Any] = {
            "context_dependencies": {},
            "successful_patterns": [],
            "failed_patterns": []
        }

    def optimize_generation_strategy(
        self,
        task_description: str,
        current_context: Dict[str, Any],
        execution_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """タスクに最適な生成戦略を決定する。

        Args:
            task_description: タスクの説明
            current_context: 現在のコンテキスト
            execution_history: 実行履歴

        Returns:
            生成戦略
        """
        # キャッシュをチェック
        cache_key = f"strategy:{task_description}"
        if self.cache:
            cached_strategy = self.cache.get(cache_key)
            if cached_strategy:
                return GenerationStrategy.from_dict(cached_strategy).to_dict()

        # LLMを使用して戦略を生成
        prompt = {
            "task": task_description,
            "context": self._prepare_context_for_json(current_context),
            "history": execution_history,
            "known_strategies": [
                strategy.to_dict()
                for strategy in self.generation_strategies.values()
            ]
        }

        response = self.llm_client.generate_strategy(prompt)
        
        # 新しい戦略を保存
        strategy = GenerationStrategy(
            strategy_type=response["strategy_type"],
            parameters=response["parameters"]
        )
        self.generation_strategies[task_description] = strategy

        # キャッシュに保存
        if self.cache:
            self.cache.set(cache_key, strategy.to_dict())

        return strategy.to_dict()

    def learn_evolution_patterns(
        self,
        original_operator: Type[BaseOperator],
        evolved_operator: Type[BaseOperator],
        performance_data: Dict[str, Any],
        evolution_strategy: Dict[str, Any]
    ) -> None:
        """オペレーターの進化パターンを学習する。

        Args:
            original_operator: 元のオペレーター
            evolved_operator: 進化後のオペレーター
            performance_data: パフォーマンスデータ
            evolution_strategy: 進化戦略
        """
        pattern = {
            "original_operator": original_operator.__name__,
            "evolved_operator": evolved_operator.__name__,
            "performance_improvement": {
                "before": performance_data.get("historical_success_rate", 0),
                "after": performance_data.get("success_rate", 0)
            },
            "strategy": evolution_strategy,
            "timestamp": datetime.now().isoformat()
        }

        self.evolution_patterns.append(pattern)

        # 成功・失敗パターンの更新
        if pattern["performance_improvement"]["after"] > pattern["performance_improvement"]["before"]:
            self.meta_knowledge["successful_patterns"].append(pattern)
        else:
            self.meta_knowledge["failed_patterns"].append(pattern)

    def _prepare_context_for_json(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """コンテキストをJSON直列化可能な形式に変換する。

        Args:
            context: 変換するコンテキスト

        Returns:
            JSON直列化可能なコンテキスト
        """
        serializable_context = {}
        for key, value in context.items():
            if isinstance(value, datetime):
                serializable_context[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                serializable_context[key] = self._prepare_nested_structure(value)
            else:
                serializable_context[key] = value
        return serializable_context

    def _prepare_nested_structure(self, data: Any) -> Any:
        """ネストされたデータ構造をJSON直列化可能な形式に変換する。

        Args:
            data: 変換するデータ

        Returns:
            JSON直列化可能なデータ
        """
        if isinstance(data, dict):
            return {
                key: self._prepare_nested_structure(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._prepare_nested_structure(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data 