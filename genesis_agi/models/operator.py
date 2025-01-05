"""Operatorモデル定義。"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped

Base = declarative_base()

class Operator(Base):
    """オペレーターモデル。"""
    __tablename__ = 'operators'

    id: Mapped[int] = Column(Integer, primary_key=True)
    name: Mapped[str] = Column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    code: Mapped[str] = Column(Text, nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True)
    performance_metrics: Mapped[Optional[str]] = Column(Text, nullable=True)  # JSON形式で保存
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    generation_parameters: Mapped[Optional[str]] = Column(Text, nullable=True)  # 生成時のパラメータをJSON形式で保存

    def to_dict(self) -> dict:
        """辞書形式に変換する。"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'is_active': self.is_active,
            'performance_metrics': self.performance_metrics,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'generation_parameters': self.generation_parameters
        } 