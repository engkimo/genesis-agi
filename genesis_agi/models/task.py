"""Task model for Genesis AGI."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    """タスクモデル。"""

    task_id: str = Field(..., description="タスクの一意な識別子")
    name: str = Field(..., description="タスクの名前")
    objective: str = Field(..., description="タスクの目的")
    type: str = Field(..., description="タスクの種類（research/execution/improvement等）")
    status: str = Field(default="pending", description="タスクの状態")
    priority: int = Field(default=0, description="タスクの優先度（高いほど優先）")
    dependencies: List[str] = Field(default_factory=list, description="依存するタスクのID")
    context: Dict[str, Any] = Field(default_factory=dict, description="タスクのコンテキスト")
    result: Optional[Dict[str, Any]] = Field(default=None, description="タスクの実行結果")
    created_by: Optional[str] = Field(default=None, description="タスクを生成したオペレーターのID")
    improvement_suggestions: List[str] = Field(
        default_factory=list, description="タスクの改善提案"
    )

    class Config:
        """設定クラス。"""

        json_schema_extra = {
            "example": {
                "task_id": "task_1",
                "name": "システムの自己改善分析",
                "objective": "現在のシステムの改善点を分析し、新しいタスクを提案する",
                "type": "improvement",
                "priority": 5,
                "dependencies": [],
                "context": {"current_system_state": "基本機能実装済み"},
            }
        } 