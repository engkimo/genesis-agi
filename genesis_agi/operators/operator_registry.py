"""オペレーターの登録と管理を行うレジストリ。"""
from typing import Dict, Type, Optional
from genesis_agi.operators.base_operator import BaseOperator


class OperatorRegistry:
    """オペレーターの登録と管理を行うクラス。"""

    def __init__(self):
        """初期化。"""
        self._operators: Dict[str, Type[BaseOperator]] = {}
        self._initialize_default_operators()

    def _initialize_default_operators(self) -> None:
        """デフォルトのオペレーターを初期化する。"""
        from genesis_agi.operators.data_analysis_operator import DataAnalysisOperator
        from genesis_agi.operators.recommendation_operator import RecommendationOperator
        
        self.register_operator(DataAnalysisOperator)
        self.register_operator(RecommendationOperator)

    def register_operator(self, operator_class: Type[BaseOperator]) -> None:
        """オペレーターを登録する。

        Args:
            operator_class: 登録するオペレータークラス
        """
        operator_type = operator_class.__name__
        self._operators[operator_type] = operator_class

    def get_operator(self, operator_type: str) -> Optional[Type[BaseOperator]]:
        """オペレーターを取得する。

        Args:
            operator_type: オペレータータイプ

        Returns:
            オペレータークラス
        """
        return self._operators.get(operator_type)

    def has_operator(self, operator_type: str) -> bool:
        """指定されたタイプのオペレーターが存在するかどうかを確認する。

        Args:
            operator_type: オペレータータイプ

        Returns:
            オペレーターが存在する場合はTrue
        """
        return operator_type in self._operators

    def list_operators(self) -> Dict[str, Type[BaseOperator]]:
        """登録されているオペレーターの一覧を取得する。

        Returns:
            オペレーターの一覧
        """
        return self._operators.copy() 