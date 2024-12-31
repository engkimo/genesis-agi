"""自己改善オペレーター。"""
from typing import Any, Dict, List

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task


class SelfImprovementOperator(BaseOperator):
    """自己改善オペレーター。"""

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
        performance_metrics = context.get("performance_metrics", {})

        # 改善提案を生成
        improvement_suggestions = self.llm_client.generate_improvement_suggestions(
            task=task,
            task_history=task_history,
            performance_metrics=performance_metrics,
        )

        # 改善提案を適用
        applied_improvements = self.apply_improvements(improvement_suggestions)

        return {
            "status": "success",
            "suggestions": improvement_suggestions,
            "applied_improvements": applied_improvements,
        }

    def validate(self, task: Task) -> bool:
        """タスクが実行可能かどうかを検証する。

        Args:
            task: 検証するタスク

        Returns:
            実行可能な場合はTrue
        """
        return (
            task.metadata is not None
            and "improvement_target" in task.metadata
            and "improvement_type" in task.metadata
        )

    def get_required_context(self) -> List[str]:
        """実行に必要なコンテキストのキーリストを取得する。

        Returns:
            必要なコンテキストのキーリスト
        """
        return ["task_history", "performance_metrics"]

    def apply_improvements(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """改善提案を適用する。

        Args:
            suggestions: 改善提案のリスト

        Returns:
            適用された改善のリスト
        """
        applied_improvements = []
        for suggestion in suggestions:
            try:
                # 改善提案の種類に応じて適切な処理を実行
                improvement_type = suggestion.get("type")
                if improvement_type == "prompt":
                    # プロンプトの改善
                    self.llm_client.update_prompt_template(
                        template_name=suggestion["target"],
                        new_template=suggestion["content"],
                    )
                elif improvement_type == "parameter":
                    # パラメータの改善
                    self.llm_client.update_parameters(
                        parameter_name=suggestion["target"],
                        new_value=suggestion["content"],
                    )
                elif improvement_type == "strategy":
                    # 戦略の改善
                    self.llm_client.update_strategy(
                        strategy_name=suggestion["target"],
                        new_strategy=suggestion["content"],
                    )

                applied_improvements.append({
                    "type": improvement_type,
                    "target": suggestion["target"],
                    "status": "success",
                })
            except Exception as e:
                applied_improvements.append({
                    "type": improvement_type,
                    "target": suggestion["target"],
                    "status": "error",
                    "error": str(e),
                })

        return applied_improvements 