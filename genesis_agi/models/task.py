"""Task model for Genesis AGI."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskMetadata(BaseModel):
    """タスクのメタデータ。"""
    task_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """タスクを表すモデル。"""
    id: str
    name: str
    description: str
    priority: float = 1.0
    metadata: TaskMetadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "id": "task-123",
                "name": "データ分析タスク",
                "description": "顧客データの基本分析を行う",
                "priority": 1.0,
                "metadata": {
                    "task_type": "analysis",
                    "params": {},
                    "context": {}
                }
            }
        }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """モデルをJSON直列化可能な辞書に変換する。"""
        data = super().model_dump(**kwargs)
        if kwargs.get('mode') == 'json':
            data['created_at'] = self.created_at.isoformat()
            data['updated_at'] = self.updated_at.isoformat()
        return data


class ExecutionRecord(BaseModel):
    """実行記録を表すモデル。"""
    task: Task
    result: Dict[str, Any]
    operator: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "task": Task.Config.json_schema_extra["example"],
                "result": {"status": "success", "data": {}},
                "operator": "analysis_operator",
                "meta_data": {"performance_metrics": {}}
            }
        }

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """モデルをJSON直列化可能な辞書に変換する。"""
        data = super().model_dump(**kwargs)
        if kwargs.get('mode') == 'json':
            data['timestamp'] = self.timestamp.isoformat()
            data['task'] = self.task.model_dump(mode='json')
        return data 