"""オペレーターの基底クラス。"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class Task(BaseModel):
    """タスクを表すクラス。"""

    id: str
    name: str
    description: str
    priority: int
    metadata: Optional[Dict[str, Any]] = None


class BaseOperator(ABC):
    """オペレーターの基底クラス。"""

    @abstractmethod
    def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """タスクを実行する。

        Args:
            task: 実行するタスク
            context: 実行コンテキスト

        Returns:
            実行結果
        """
        pass

    @abstractmethod
    def validate(self, task: Task) -> bool:
        """タスクが実行可能かどうかを検証する。

        Args:
            task: 検証するタスク

        Returns:
            実行可能な場合はTrue
        """
        pass

    @abstractmethod
    def get_required_context(self) -> List[str]:
        """実行に必要なコンテキストのキーリストを取得する。

        Returns:
            必要なコンテキストのキーリスト
        """
        pass

    def cleanup(self) -> None:
        """リソースのクリーンアップを行う。"""
        pass 