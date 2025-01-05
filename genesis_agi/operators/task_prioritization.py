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
        # タスクの実行履歴を取得
        task_history = context.get("task_history", [])
        objective = context.get("objective", "タスクの優先順位付け")
        current_tasks = context.get("current_tasks", [])

        # プロンプトの構築
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはタスク優先順位付けの専門家です。"
                    "与えられたタスクリストの優先順位を決定してください。"
                ),
            },
            {
                "role": "user",
                "content": f"""
目標: {objective}

現在のタスク:
{[task.model_dump() for task in current_tasks]}

タスク履歴:
{task_history}

以下の形式で優先順位付けの結果を返してください：
{{
    "prioritized_tasks": [
        {{
            "id": "タスクID",
            "priority": 優先度（1-10）,
            "reason": "優先度を決定した理由"
        }},
        ...
    ]
}}
""",
            },
        ]

        # 優先順位付けの実行
        response = self.llm_client.chat_completion(messages, temperature=0.7)
        result = self.llm_client.parse_json_response(response)

        return result

    def validate(self, task: Task) -> bool:
        """タスクが実行可能かどうかを検証する。

        Args:
            task: 検証するタスク

        Returns:
            実行可能な場合はTrue
        """
        return True

    def get_required_context(self) -> List[str]:
        """実行に必要なコンテキストのキーリストを取得する。

        Returns:
            必要なコンテキストのキーリスト
        """
        return ["objective", "task_history", "current_tasks"] 