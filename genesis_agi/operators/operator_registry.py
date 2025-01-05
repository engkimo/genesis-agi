"""オペレーターの登録と管理を行うレジストリ。"""
from typing import Dict, Type, Optional, List
import json
import inspect
from sqlalchemy.orm import Session
from genesis_agi.operators.base_operator import BaseOperator
from genesis_agi.models.operator import Operator
from genesis_agi.utils.code_loader import load_operator_from_code
import logging

logger = logging.getLogger(__name__)


class OperatorRegistry:
    """オペレーターの登録と管理を行うクラス。"""

    def __init__(self, db_session: Session):
        """初期化。

        Args:
            db_session: データベースセッション
        """
        self.db_session = db_session
        self._operator_cache: Dict[str, Type[BaseOperator]] = {}

    def has_operator(self, operator_type: str) -> bool:
        """指定されたタイプのオペレーターが存在するかどうかを確認する。

        Args:
            operator_type: オペレータータイプ

        Returns:
            オペレーターが存在する場合はTrue
        """
        # キャッシュをチェック
        if operator_type in self._operator_cache:
            return True

        # データベースをチェック
        operator = self.db_session.query(Operator).filter_by(
            name=operator_type,
            is_active=True
        ).first()

        return operator is not None

    def register_operator(self, operator_class: Type[BaseOperator], description: Optional[str] = None) -> None:
        """オペレーターを登録する。

        Args:
            operator_class: 登録するオペレータークラス
            description: オペレーターの説明

        Raises:
            ValueError: オペレータークラスが無効な場合
            RuntimeError: データベースへの登録に失敗した場合
        """
        if not issubclass(operator_class, BaseOperator):
            raise ValueError("operator_class must be a subclass of BaseOperator")

        operator_type = operator_class.__name__
        code = inspect.getsource(operator_class)
        
        try:
            # 既存のオペレーターを非アクティブ化
            existing_operator = self.db_session.query(Operator).filter_by(name=operator_type).first()
            if existing_operator:
                existing_operator.is_active = False
                self.db_session.flush()
            
            # 新しいオペレーターを登録
            operator = Operator(
                name=operator_type,
                description=description or f"Generated operator for {operator_type}",
                code=code,
                is_active=True
            )
            
            self.db_session.add(operator)
            self.db_session.commit()
            
            # キャッシュを更新
            self._operator_cache[operator_type] = operator_class
            logger.info(f"オペレーター '{operator_type}' を正常に登録しました")

        except Exception as e:
            self.db_session.rollback()
            error_msg = f"オペレーター '{operator_type}' の登録に失敗: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_operator(self, operator_type: str) -> Optional[Type[BaseOperator]]:
        """オペレーターを取得する。

        Args:
            operator_type: オペレータータイプ

        Returns:
            オペレータークラス
        """
        # キャッシュをチェック
        if operator_type in self._operator_cache:
            return self._operator_cache[operator_type]

        # データベースから取得
        operator = self.db_session.query(Operator).filter_by(
            name=operator_type,
            is_active=True
        ).first()

        if operator:
            operator_class = load_operator_from_code(operator.code)
            self._operator_cache[operator_type] = operator_class
            return operator_class

        return None

    def list_operators(self) -> List[Dict]:
        """登録されているすべてのアクティブなオペレーターを取得する。

        Returns:
            オペレーター情報のリスト
        """
        operators = self.db_session.query(Operator).filter_by(is_active=True).all()
        return [
            {
                'name': op.name,
                'description': op.description,
                'performance_metrics': json.loads(op.performance_metrics) if op.performance_metrics else None,
                'created_at': op.created_at.isoformat(),
                'updated_at': op.updated_at.isoformat()
            }
            for op in operators
        ]

    def deactivate_operator(self, operator_type: str) -> None:
        """オペレーターを非アクティブ化する。

        Args:
            operator_type: オペレータータイプ
        """
        operator = self.db_session.query(Operator).filter_by(name=operator_type).first()
        if operator:
            operator.is_active = False
            self.db_session.commit()
            if operator_type in self._operator_cache:
                del self._operator_cache[operator_type]

    def update_performance_metrics(self, operator_type: str, metrics: Dict) -> None:
        """オペレーターのパフォーマンスメトリクスを更新する。

        Args:
            operator_type: オペレータータイプ
            metrics: パフォーマンスメトリクス
        """
        operator = self.db_session.query(Operator).filter_by(name=operator_type).first()
        if operator:
            operator.performance_metrics = json.dumps(metrics)
            self.db_session.commit() 