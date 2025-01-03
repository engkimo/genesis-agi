"""Operator generator module."""
from typing import Any, Dict, List, Optional, Type
import logging

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.utils.cache import Cache
from genesis_agi.operators import BaseOperator

logger = logging.getLogger(__name__)


class OperatorGenerator:
    """オペレーターを動的に生成するジェネレーター。"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: OperatorRegistry,
        cache: Optional[Cache] = None
    ):
        """初期化。

        Args:
            llm_client: LLMクライアント
            registry: オペレーターレジストリ
            cache: キャッシュ（オプション）
        """
        self.llm_client = llm_client
        self.registry = registry
        self.cache = cache

    def generate_operator(
        self,
        task_description: str,
        current_context: Dict[str, Any],
        generation_strategy: Dict[str, Any]
    ) -> Type[BaseOperator]:
        """タスクに適したオペレーターを生成する。

        Args:
            task_description: タスクの説明
            current_context: 現在のコンテキスト
            generation_strategy: 生成戦略

        Returns:
            生成されたオペレータークラス
        """
        # キャッシュをチェック
        cache_key = f"operator:{task_description}"
        cached_operator = self._load_from_cache(cache_key)
        if cached_operator:
            return cached_operator

        # LLMを使用してオペレーターを生成
        prompt = {
            "task": task_description,
            "context": current_context,
            "strategy": generation_strategy,
            "known_operators": self.registry.list_operators()
        }
        
        response = self.llm_client.generate_operator_code(prompt)
        operator_code = response["code"].replace("your_file.csv", "data/customer_data.csv")
        
        # オペレータークラスを動的に生成
        namespace = {}
        exec(operator_code, namespace)
        operator_class = namespace[response["class_name"]]
        
        # キャッシュに保存
        if self.cache:
            try:
                cache_data = {
                    "code": operator_code,
                    "class_name": response["class_name"]
                }
                self.cache.set(cache_key, cache_data)
            except Exception as e:
                logger.warning(f"キャッシュの保存に失敗しました: {str(e)}")
        
        return operator_class

    def evolve_operator(
        self,
        operator_type: str,
        performance_data: Dict[str, Any],
        evolution_strategy: Dict[str, Any]
    ) -> Type[BaseOperator]:
        """既存のオペレーターを進化させる。

        Args:
            operator_type: オペレーターの種類
            performance_data: パフォーマンスデータ
            evolution_strategy: 進化戦略

        Returns:
            進化したオペレータークラス
        """
        original_operator = self.registry.get_operator(operator_type)
        
        # LLMを使用してオペレーターを進化
        prompt = {
            "original_code": self._get_operator_code(original_operator),
            "performance": performance_data,
            "strategy": evolution_strategy
        }
        
        response = self.llm_client.evolve_operator(prompt)
        evolved_code = response["code"]
        
        # 進化したオペレータークラスを動的に生成
        namespace = {}
        exec(evolved_code, namespace)
        evolved_operator = namespace[response["class_name"]]
        
        return evolved_operator

    def analyze_operator_chain(
        self,
        execution_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """オペレーターチェーンを分析する。

        Args:
            execution_history: 実行履歴

        Returns:
            分析結果
        """
        # オペレーターの使用状況を分析
        operator_stats = {}
        for record in execution_history:
            operator_type = record["operator"]
            if operator_type not in operator_stats:
                operator_stats[operator_type] = {
                    "count": 0,
                    "success_count": 0,
                    "total_time": 0
                }
            
            stats = operator_stats[operator_type]
            stats["count"] += 1
            if record["result"]["status"] == "success":
                stats["success_count"] += 1
            stats["total_time"] += record["result"].get("execution_time", 0)
        
        # 効率性とボトルネックを特定
        bottlenecks = []
        total_efficiency = 0
        
        for operator_type, stats in operator_stats.items():
            efficiency = stats["success_count"] / stats["count"]
            total_efficiency += efficiency
            
            if efficiency < 0.8 or stats["total_time"] / stats["count"] > 5.0:
                bottlenecks.append(operator_type)
        
        return {
            "efficiency": total_efficiency / len(operator_stats) if operator_stats else 1.0,
            "bottlenecks": bottlenecks,
            "stats": operator_stats
        }

    def _get_operator_code(self, operator_class: Type[BaseOperator]) -> str:
        """オペレータークラスのソースコードを取得する。

        Args:
            operator_class: オペレータークラス

        Returns:
            ソースコード
        """
        import inspect
        return inspect.getsource(operator_class) 

    def _load_from_cache(self, cache_key: str) -> Optional[Type[BaseOperator]]:
        """キャッシュからオペレーターを読み込む。

        Args:
            cache_key: キャッシュキー

        Returns:
            キャッシュされたオペレータークラス（存在しない場合はNone）
        """
        if not self.cache:
            return None

        try:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                namespace = {}
                exec(cached_data["code"], namespace)
                return namespace[cached_data["class_name"]]
        except Exception as e:
            logger.warning(f"キャッシュの読み込みに失敗しました: {str(e)}")
        
        return None 