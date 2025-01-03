"""Operator execution pipeline management."""
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .operator_registry import OperatorRegistry
from .base_operator import BaseOperator


class Pipeline:
    """オペレーターの実行パイプラインを管理するクラス。"""

    def __init__(self, registry: OperatorRegistry):
        """Initialize the pipeline.

        Args:
            registry: オペレーターレジストリのインスタンス
        """
        self.registry = registry
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, Exception] = {}

    def execute_operator(self, operator_name: str, task_id: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """単一のオペレーターを実行する。

        Args:
            operator_name: 実行するオペレーターの名前
            task_id: タスクID
            params: オペレーターのパラメータ

        Returns:
            実行結果
        """
        operator_class = self.registry.get_operator(operator_name)
        operator = operator_class(task_id=task_id, params=params)
        try:
            result = operator.run()
            self.results[task_id] = result
            return result
        except Exception as e:
            self.errors[task_id] = e
            raise

    def execute_parallel(self, operators: List[Dict[str, Any]], max_workers: int = 3) -> Dict[str, Any]:
        """複数のオペレーターを並列実行する。

        Args:
            operators: 実行するオペレーターのリスト。各要素は以下のキーを持つ辞書:
                - operator_name: オペレーターの名前
                - task_id: タスクID
                - params: オペレーターのパラメータ（オプション）
            max_workers: 最大並列実行数

        Returns:
            タスクIDをキー、実行結果を値とする辞書
        """
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(
                    self.execute_operator,
                    op['operator_name'],
                    op['task_id'],
                    op.get('params')
                ): op['task_id']
                for op in operators
            }

            for future in as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    self.results[task_id] = future.result()
                except Exception as e:
                    self.errors[task_id] = e

        return self.results

    def get_results(self) -> Dict[str, Any]:
        """全ての実行結果を取得する。

        Returns:
            実行結果の辞書
        """
        return self.results

    def get_errors(self) -> Dict[str, Exception]:
        """発生したエラーを取得する。

        Returns:
            エラーの辞書
        """
        return self.errors 