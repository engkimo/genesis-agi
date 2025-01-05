"""タスク実行オペレーター。"""
from typing import Any, Dict, List
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task


class TaskExecutionOperator(BaseOperator):
    """タスクを実行するオペレーター。"""

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
        objective = context.get("objective", "タスクの実行")

        # プロンプトの構築
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはタスク実行アシスタントです。"
                    "与えられたタスクを実行し、結果を返してください。"
                ),
            },
            {
                "role": "user",
                "content": f"""
目標: {objective}

タスク:
{task.model_dump()}

タスク履歴:
{task_history}

タスクを実行し、以下の形式で結果を返してください：
{{
    "status": "success" または "failed",
    "output": "実行結果の説明",
    "metrics": {{
        "execution_time": 実行時間（秒）,
        "resource_usage": リソース使用量,
        "quality_score": 品質スコア（0-1）
    }}
}}
""",
            },
        ]

        # タスクの実行
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
        return ["objective", "task_history"] 