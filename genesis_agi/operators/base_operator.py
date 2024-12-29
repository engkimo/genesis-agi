"""Base operator module for Genesis AGI."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseOperator(ABC):
    """全てのオペレーターの基底クラス。

    各オペレーターはこのクラスを継承して実装する必要があります。
    """

    def __init__(self, task_id: str, params: Optional[Dict[str, Any]] = None) -> None:
        """BaseOperatorの初期化。

        Args:
            task_id: タスクの一意な識別子
            params: オペレーターに渡すパラメータ
        """
        self.task_id = task_id
        self.params = params or {}

    @abstractmethod
    def execute(self) -> Any:
        """オペレーターのメイン処理を実行するメソッド。

        全ての子クラスでこのメソッドを実装する必要があります。

        Returns:
            実行結果
        """
        pass

    def pre_execute(self) -> None:
        """実行前の前処理を行うメソッド。"""
        pass

    def post_execute(self) -> None:
        """実行後の後処理を行うメソッド。"""
        pass

    def run(self) -> Any:
        """オペレーターの実行フローを制御するメソッド。

        Returns:
            execute()メソッドの実行結果
        """
        self.pre_execute()
        result = self.execute()
        self.post_execute()
        return result 