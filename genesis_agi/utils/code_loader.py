"""動的にコードをロードするユーティリティ。"""
import ast
import types
from typing import Type
from genesis_agi.operators.base_operator import BaseOperator


def load_operator_from_code(code: str) -> Type[BaseOperator]:
    """文字列からオペレータークラスを動的にロードする。

    Args:
        code: オペレーターのソースコード

    Returns:
        オペレータークラス

    Raises:
        ValueError: コードが不正な場合
    """
    try:
        # コードをASTに変換
        tree = ast.parse(code)
        
        # グローバル名前空間を準備
        namespace = {}
        
        # 必要なインポートを追加
        exec('from genesis_agi.operators.base_operator import BaseOperator', namespace)
        
        # コードを実行
        exec(code, namespace)
        
        # クラス定義を探す
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                if class_name in namespace:
                    operator_class = namespace[class_name]
                    
                    # BaseOperatorのサブクラスであることを確認
                    if (isinstance(operator_class, type) and 
                        issubclass(operator_class, BaseOperator)):
                        return operator_class
        
        raise ValueError('有効なオペレータークラスが見つかりません')
        
    except Exception as e:
        raise ValueError(f'コードのロードに失敗しました: {str(e)}') 