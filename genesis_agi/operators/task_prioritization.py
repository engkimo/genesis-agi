"""タスク優先順位付けオペレーター。"""
from typing import Any, Dict, List

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task


class TaskPrioritizationOperator(BaseOperator):
    """タスク優先順位付けオペレーター。"""

    def __init__(self, llm_client: LLMClient):
        """初期化。

        Args:
            llm_client: LLMクライアント
        """
        self.llm_client = llm_client

    def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """タスクを実行する。

        Args:
            task: 実行するタスク
            context: 実行コンテキスト

        Returns:
            実行結果
        """
        # タスクリストとコンテキストを取得
        task_list = context.get("task_list", [])
        objective = context.get("objective", "タスクの優先順位付け")
        performance_metrics = context.get("performance_metrics", {})

        # プロンプトの構築
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはタスク優先順位付けアシスタントです。"
                    "与えられたタスクリストを分析し、"
                    "最適な優先順位を設定してください。"
                ),
            },
            {
                "role": "user",
                "content": f"""
目標: {objective}

タスクリスト:
{[task.dict() for task in task_list]}

パフォーマンス指標:
{performance_metrics}

以下の点を考慮して優先順位を設定してください：
1. タスクの重要度と緊急度
2. 依存関係
3. リソースの利用可能性
4. 予想される実行時間
5. これまでの実行結果

以下の形式で結果を返してください：
{{
    "prioritized_tasks": [
        {{
            "id": "タスクID",
            "priority": 優先度（1-5）,
            "reason": "優先度を設定した理由"
        }}
    ],
    "analysis": {{
        "bottlenecks": ["ボトルネック"],
        "suggestions": ["改善提案"]
    }}
}}
""",
            },
        ]

        # 優先順位付けの実行
        response = self.llm_client._call_openai(messages, temperature=0.3)
        result = self.llm_client.parse_json_response(response)

        # タスクの優先順位を更新
        updated_tasks = []
        for task_info in result["prioritized_tasks"]:
            task_id = task_info["id"]
            for task in task_list:
                if task.id == task_id:
                    task.priority = int(task_info["priority"])
                    if not task.metadata:
                        task.metadata = {}
                    task.metadata["prioritization_reason"] = task_info["reason"]
                    updated_tasks.append(task)
                    break

        return {
            "status": "success",
            "prioritized_tasks": [task.dict() for task in updated_tasks],
            "analysis": result["analysis"],
        }

    def validate(self, task: Task) -> bool:
        """タスクが実行可能かどうかを検証する。

        Args:
            task: 検証するタスク

        Returns:
            実行可能な場合はTrue
        """
        return task.metadata is not None and task.metadata.get("task_type") == "prioritization"

    def get_required_context(self) -> List[str]:
        """実行に必要なコンテキストのキーリストを取得する。

        Returns:
            必要なコンテキストのキーリスト
        """
        return ["task_list", "objective", "performance_metrics"] 