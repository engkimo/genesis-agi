"""タスク実行オペレーター。"""
from typing import Any, Dict, List

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task


class TaskExecutionOperator(BaseOperator):
    """タスク実行オペレーター。"""

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
                    "与えられたタスクを実行し、その結果を報告してください。"
                ),
            },
            {
                "role": "user",
                "content": f"""
目標: {objective}

実行するタスク:
{task.dict()}

タスク履歴:
{task_history}

以下の形式で実行結果を報告してください：
{{
    "status": "success" または "failure",
    "output": "タスクの実行結果",
    "metrics": {{
        "execution_time": 実行時間（秒）,
        "resource_usage": リソース使用量,
        "quality_score": 品質スコア（0-1）
    }},
    "next_steps": [
        {{
            "action": "次のアクション",
            "reason": "その理由"
        }}
    ]
}}
""",
            },
        ]

        # タスクの実行
        response = self.llm_client._call_openai(messages, temperature=0.3)
        result = self.llm_client.parse_json_response(response)

        # 実行結果の検証
        if result["status"] == "failure":
            # エラーハンドリング
            self._handle_failure(task, result)

        return result

    def validate(self, task: Task) -> bool:
        """タスクが実行可能かどうかを検証する。

        Args:
            task: 検証するタスク

        Returns:
            実行可能な場合はTrue
        """
        if not task.metadata:
            return False

        # 依存タスクのチェック
        dependencies = task.metadata.get("dependencies", [])
        if dependencies:
            # TODO: 依存タスクの完了状態をチェック
            pass

        # リソースのチェック
        required_resources = task.metadata.get("required_resources", [])
        if required_resources:
            # TODO: 必要なリソースの利用可能性をチェック
            pass

        return True

    def get_required_context(self) -> List[str]:
        """実行に必要なコンテキストのキーリストを取得する。

        Returns:
            必要なコンテキストのキーリスト
        """
        return ["task_history", "objective"]

    def _handle_failure(self, task: Task, result: Dict[str, Any]) -> None:
        """タスクの失敗を処理する。

        Args:
            task: 失敗したタスク
            result: 実行結果
        """
        # エラーログの記録
        error_message = result.get("output", "Unknown error")
        print(f"Task {task.id} failed: {error_message}")

        # リトライポリシーの適用
        if task.metadata and task.metadata.get("retry_count", 0) < 3:
            # リトライ回数を増やして再スケジュール
            task.metadata["retry_count"] = task.metadata.get("retry_count", 0) + 1
            task.priority += 1  # 優先度を上げる
            # TODO: タスクの再スケジュール処理 