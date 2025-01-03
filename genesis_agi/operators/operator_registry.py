"""Operator registry for managing and tracking operators."""
from typing import Dict, Type, List, Optional
from .base_operator import BaseOperator


class OperatorRegistry:
    """オペレーターの登録と管理を行うクラス。"""
    
    def __init__(self):
        """Initialize the operator registry."""
        self._operators: Dict[str, Type[BaseOperator]] = {}
        self._dependencies: Dict[str, List[str]] = {}
    
    def register_operator(self, operator_class: Type[BaseOperator], dependencies: Optional[List[str]] = None) -> None:
        """新しいオペレーターを登録する。

        Args:
            operator_class: 登録するオペレータークラス
            dependencies: 依存するオペレーターのリスト
        """
        operator_name = operator_class.__name__
        self._operators[operator_name] = operator_class
        if dependencies:
            self._dependencies[operator_name] = dependencies
    
    def get_operator(self, operator_name: str) -> Type[BaseOperator]:
        """指定された名前のオペレーターを取得する。

        Args:
            operator_name: オペレーターの名前

        Returns:
            オペレータークラス

        Raises:
            KeyError: 指定された名前のオペレーターが存在しない場合
        """
        if operator_name not in self._operators:
            raise KeyError(f"Operator {operator_name} not found in registry")
        return self._operators[operator_name]
    
    def list_operators(self) -> List[str]:
        """登録されているオペレーターの一覧を返す。

        Returns:
            オペレーター名のリスト
        """
        return list(self._operators.keys())
    
    def get_dependencies(self, operator_name: str) -> List[str]:
        """指定されたオペレーターの依存関係を取得する。

        Args:
            operator_name: オペレーターの名前

        Returns:
            依存するオペレーターのリスト
        """
        return self._dependencies.get(operator_name, []) 