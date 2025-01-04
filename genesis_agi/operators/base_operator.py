"""基本オペレータークラス。"""
from typing import Any, Dict, List
from abc import ABC, abstractmethod


class BaseOperator(ABC):
    """全てのオペレーターの基底クラス。"""

    @abstractmethod
    def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """タスクを実行する。

        Args:
            task: 実行するタスク
            context: 実行コンテキスト

        Returns:
            実行結果
        """
        pass

    @classmethod
    def get_required_context(cls) -> List[str]:
        """必要なコンテキストのキーを取得する。

        Returns:
            必要なコンテキストのキーのリスト
        """
        return [
            "objective",
            "task_history",
            "performance_metrics"
        ]

    def validate_result(self, result: Dict[str, Any]) -> bool:
        """実行結果を検証する。

        Args:
            result: 検証する実行結果

        Returns:
            検証結果（True: 有効、False: 無効）
        """
        required_keys = ["status", "output"]
        return all(key in result for key in required_keys)

    def prepare_result(self, output: Any, status: str = "success") -> Dict[str, Any]:
        """実行結果を準備する。

        Args:
            output: 実行出力
            status: 実行状態

        Returns:
            整形された実行結果
        """
        return {
            "status": status,
            "output": output,
            "performance_metrics": {
                "execution_success": status == "success",
                "output_quality": self._evaluate_output_quality(output)
            }
        }

    def _evaluate_output_quality(self, output: Any) -> float:
        """出力の品質を評価する。

        Args:
            output: 評価する出力

        Returns:
            品質スコア（0-1）
        """
        if output is None:
            return 0.0
        
        if isinstance(output, (dict, list)):
            return 1.0 if output else 0.0
        
        if isinstance(output, str):
            return 1.0 if output.strip() else 0.0
        
        return 1.0 