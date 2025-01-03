"""Operator factory for dynamically creating operators."""
from typing import Dict, Any, Type, Optional
import inspect
from .base_operator import BaseOperator


class OperatorFactory:
    """オペレーターを動的に生成するファクトリークラス。"""

    @classmethod
    def create_operator(cls, 
                       name: str,
                       execute_logic: str,
                       params: Optional[Dict[str, Any]] = None) -> Type[BaseOperator]:
        """新しいオペレータークラスを動的に生成する。

        Args:
            name: 生成するオペレーターの名前
            execute_logic: execute メソッドの実装コード
            params: オペレーターのパラメータ

        Returns:
            生成されたオペレータークラス
        """
        # クラス定義の準備
        class_dict = {
            '__init__': lambda self, task_id, params=None: BaseOperator.__init__(self, task_id, params),
            '__doc__': f"""Dynamically generated operator: {name}"""
        }

        # executeメソッドの実装
        exec(f"def execute(self): {execute_logic}", class_dict)
        
        # 新しいオペレータークラスを作成
        new_operator = type(
            name,
            (BaseOperator,),
            class_dict
        )

        return new_operator

    @classmethod
    def validate_operator(cls, operator_class: Type[BaseOperator]) -> bool:
        """生成されたオペレーターが正しく実装されているか検証する。

        Args:
            operator_class: 検証するオペレータークラス

        Returns:
            検証結果（True/False）
        """
        # 必要なメソッドが実装されているか確認
        required_methods = ['execute', 'run', 'pre_execute', 'post_execute']
        for method in required_methods:
            if not hasattr(operator_class, method):
                return False
            
            # executeメソッドが抽象メソッドでないことを確認
            if method == 'execute' and inspect.isabstract(operator_class):
                return False

        return True 