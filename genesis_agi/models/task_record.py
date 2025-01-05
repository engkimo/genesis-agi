"""タスクとその実行結果を保存するためのモデル。"""
from datetime import datetime
from typing import Dict, Any
import json
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TaskRecord(Base):
    """タスクの実行記録を表すモデル。"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(Float, nullable=False, default=1.0)
    task_metadata = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False)
    result = Column(JSON, nullable=True)
    operator = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する。"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'priority': self.priority,
            'task_metadata': self.task_metadata,
            'status': self.status,
            'result': self.result,
            'operator': self.operator,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 