"""タスク生成オペレーター。"""
from typing import Any, Dict, List
from uuid import uuid4

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task


class TaskCreationOperator(BaseOperator):
    """タスク生成オペレーター。"""

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
        # タスクの実行履歴を取得
        task_history = context.get("task_history", [])
        objective = context.get("objective", "タスクの生成と実行")

        # プロンプトの構築
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはタスク生成アシスタントです。"
                    "与えられた目標とタスク履歴に基づいて、"
                    "次に実行すべきタスクのリストを生成してください。"
                ),
            },
            {
                "role": "user",
                "content": f"""
目標: {objective}

現在のタスク:
{task.dict()}

タスク履歴:
{task_history}

以下の形式でタスクのリストを生成してください：
[
    {{
        "name": "タスク名",
        "description": "タスクの詳細な説明",
        "priority": 優先度（1-5）,
        "metadata": {{
            "dependencies": ["依存タスクのID"],
            "estimated_time": "予想所要時間（分）",
            "required_resources": ["必要なリソース"]
        }}
    }},
    ...
]
""",
            },
        ]

        # タスクの生成
        response = self.llm_client._call_openai(messages, temperature=0.7)
        tasks_data = self.llm_client.parse_json_response(response)

        # タスクオブジェクトの作成
        new_tasks = []
        for task_data in tasks_data:
            task_data["id"] = f"task-{uuid4()}"
            new_tasks.append(Task(**task_data))

        return {
            "status": "success",
            "new_tasks": [task.dict() for task in new_tasks],
        }

    def validate(self, task: Task) -> bool:
        """タスクが実行可能かどうかを検証する。

        Args:
            task: 検証するタスク

        Returns:
            実行可能な場合はTrue
        """
        return task.metadata is not None and "task_type" in task.metadata

    def get_required_context(self) -> List[str]:
        """実行に必要なコンテキストのキーリストを取得する。

        Returns:
            必要なコンテキストのキーリスト
        """
        return ["task_history", "objective"] 