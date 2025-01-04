"""オペレーター生成モジュール。"""
from typing import Any, Dict, List, Optional, Type
import logging
import inspect
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.utils.cache import Cache
from genesis_agi.operators.base_operator import BaseOperator

logger = logging.getLogger(__name__)


class OperatorGenerator:
    """オペレーターを動的に生成するジェネレーター。"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: OperatorRegistry,
        cache: Optional[Cache] = None
    ):
        """初期化。"""
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
        if self.cache:
            cached_operator = self._load_from_cache(cache_key)
            if cached_operator:
                return cached_operator

        # LLMを使用してオペレーターを生成
        prompt = {
            "task": task_description,
            "context": current_context,
            "strategy": generation_strategy,
            "known_operators": [
                self._get_operator_code(op)
                for op in self.registry.list_operators().values()
            ]
        }
        
        response = self.llm_client.generate_operator_code(prompt)
        operator_code = response["code"]
        
        # オペレータークラスを動的に生成
        namespace = {}
        exec(operator_code, namespace)
        operator_class = namespace[response["class_name"]]
        
        # 生成されたクラスの検証
        if not self._validate_operator_class(operator_class):
            raise ValueError("生成されたオペレーターが無効です")

        # キャッシュに保存
        if self.cache:
            self._save_to_cache(cache_key, operator_code, response["class_name"])
        
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
        # 元のオペレーターを取得
        original_operator = self.registry.get_operator(operator_type)
        if not original_operator:
            raise ValueError(f"オペレーター {operator_type} が見つかりません")

        # LLMを使用してオペレーターを進化
        prompt = {
            "original_code": self._get_operator_code(original_operator),
            "performance": performance_data,
            "strategy": evolution_strategy,
            "improvement_focus": evolution_strategy["improvement_focus"]
        }
        
        response = self.llm_client.evolve_operator(prompt)
        evolved_code = response["code"]
        
        # 進化したオペレータークラスを動的に生成
        namespace = {}
        exec(evolved_code, namespace)
        evolved_operator = namespace[response["class_name"]]
        
        # 進化したクラスの検証
        if not self._validate_operator_class(evolved_operator):
            raise ValueError("進化したオペレーターが無効です")
        
        return evolved_operator

    def _validate_operator_class(self, operator_class: Type[BaseOperator]) -> bool:
        """オペレータークラスを検証する。

        Args:
            operator_class: 検証するオペレータークラス

        Returns:
            検証結果
        """
        # 必要なメソッドの存在を確認
        required_methods = ["execute", "get_required_context", "validate_result"]
        for method in required_methods:
            if not hasattr(operator_class, method):
                return False

        # BaseOperatorを継承していることを確認
        if not issubclass(operator_class, BaseOperator):
            return False

        return True

    def _get_operator_code(self, operator_class: Type[BaseOperator]) -> str:
        """オペレータークラスのソースコードを取得する。

        Args:
            operator_class: オペレータークラス

        Returns:
            ソースコード
        """
        return inspect.getsource(operator_class)

    def _save_to_cache(
        self,
        cache_key: str,
        operator_code: str,
        class_name: str
    ) -> None:
        """オペレーターをキャッシュに保存する。

        Args:
            cache_key: キャッシュキー
            operator_code: オペレーターのコード
            class_name: クラス名
        """
        if not self.cache:
            return

        try:
            cache_data = {
                "code": operator_code,
                "class_name": class_name
            }
            self.cache.set(cache_key, cache_data)
        except Exception as e:
            logger.warning(f"キャッシュの保存に失敗しました: {str(e)}")

    def _load_from_cache(self, cache_key: str) -> Optional[Type[BaseOperator]]:
        """キャッシュからオペレーターを読み込む。

        Args:
            cache_key: キャッシュキー

        Returns:
            キャッシュされたオペレータークラス
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