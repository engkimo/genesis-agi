"""Operatorモデル定義。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Operator(Base):
    """オペレーターモデル。"""
    __tablename__ = 'operators'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    performance_metrics = Column(Text, nullable=True)  # JSON形式で保存
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    generation_parameters = Column(Text, nullable=True)  # 生成時のパラメータをJSON形式で保存 