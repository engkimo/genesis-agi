"""Autonomous task and workflow management."""
from typing import Dict, List, Any, Optional, TypedDict
from .operator_registry import OperatorRegistry
from .operator_factory import OperatorFactory
from .pipeline import Pipeline


class TaskResult(TypedDict):
    """タスク実行結果の型定義"""
    task_id: str
    status: str
    result: Any
    generated_tasks: List[Dict[str, Any]]


class AutonomousManager:
    """自律的なタスクとワークフロー管理を行うクラス。"""

    def __init__(self, registry: OperatorRegistry, objective: str):
        """Initialize the autonomous manager.

        Args:
            registry: オペレーターレジストリのインスタンス
            objective: システムの目的
        """
        self.registry = registry
        self.pipeline = Pipeline(registry)
        self.objective = objective
        self.task_queue: List[Dict[str, Any]] = []
        self.execution_history: List[Dict[str, Any]] = []
        self.current_context: Dict[str, Any] = {
            "objective": objective,
            "completed_tasks": [],
            "current_state": {}
        }

    def analyze_task_result(self, result: TaskResult) -> List[Dict[str, Any]]:
        """タスクの実行結果を分析し、次のタスクを生成する。

        Args:
            result: タスク実行結果

        Returns:
            生成された次のタスクのリスト
        """
        # タスクの結果をコンテキストに追加
        self.current_context["current_state"].update({
            "last_task_result": result["result"],
            "last_task_id": result["task_id"]
        })
        self.current_context["completed_tasks"].append(result["task_id"])

        # 結果に基づいて新しいタスクを生成
        new_tasks = []
        if result.get("generated_tasks"):
            for task_info in result["generated_tasks"]:
                task = self.create_task(
                    task_description=task_info["description"],
                    task_type=task_info["operator_type"],
                    params=task_info.get("params", {}),
                    context=self.current_context
                )
                new_tasks.append(task)

        return new_tasks

    def create_task(self, task_description: str, task_type: str, 
                   params: Optional[Dict[str, Any]] = None,
                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """コンテキストを考慮してタスクを作成する。

        Args:
            task_description: タスクの説明
            task_type: タスクの種類
            params: タスクのパラメータ
            context: 現在のコンテキスト

        Returns:
            作成されたタスク
        """
        task_id = f"task_{len(self.task_queue)}"
        task = {
            "task_id": task_id,
            "description": task_description,
            "operator_name": task_type,
            "params": params or {},
            "status": "pending",
            "context": context or self.current_context.copy()
        }
        self.task_queue.append(task)
        return task

    def execute_next_task(self) -> Optional[TaskResult]:
        """次のタスクを実行する。

        Returns:
            タスクの実行結果
        """
        if not self.task_queue:
            return None

        # コンテキストに基づいて最適なタスクを選択
        next_task = self.select_next_task()
        if not next_task:
            return None

        try:
            # タスクの実行
            result = self.pipeline.execute_operator(
                next_task["operator_name"],
                next_task["task_id"],
                {**next_task["params"], "context": next_task["context"]}
            )

            task_result: TaskResult = {
                "task_id": next_task["task_id"],
                "status": "completed",
                "result": result,
                "generated_tasks": result.get("generated_tasks", []) if isinstance(result, dict) else []
            }

            # 実行履歴の更新
            self.execution_history.append({
                **next_task,
                "result": result,
                "completion_time": "current_timestamp"
            })

            return task_result

        except Exception as e:
            return {
                "task_id": next_task["task_id"],
                "status": "failed",
                "result": str(e),
                "generated_tasks": []
            }

    def select_next_task(self) -> Optional[Dict[str, Any]]:
        """コンテキストに基づいて次に実行すべきタスクを選択する。

        Returns:
            選択されたタスク
        """
        if not self.task_queue:
            return None

        # 現在のコンテキストに基づいてタスクの優先順位を評価
        prioritized_tasks = self.prioritize_tasks()
        if prioritized_tasks:
            selected_task = prioritized_tasks[0]
            self.task_queue.remove(selected_task)
            return selected_task

        return None

    def prioritize_tasks(self) -> List[Dict[str, Any]]:
        """タスクの優先順位付けを行う。

        Returns:
            優先順位付けされたタスクのリスト
        """
        # コンテキストに基づいてタスクをスコアリング
        scored_tasks = []
        for task in self.task_queue:
            score = self.calculate_task_priority(task)
            scored_tasks.append((score, task))

        # スコアの高い順にソート
        scored_tasks.sort(reverse=True, key=lambda x: x[0])
        return [task for _, task in scored_tasks]

    def calculate_task_priority(self, task: Dict[str, Any]) -> float:
        """タスクの優先度を計算する。

        Args:
            task: 評価対象のタスク

        Returns:
            優先度スコア
        """
        score = 0.0
        
        # 目的との関連性を評価
        if self.objective in task["description"].lower():
            score += 1.0

        # 依存関係の考慮
        completed_tasks = set(self.current_context["completed_tasks"])
        if all(dep in completed_tasks for dep in task.get("dependencies", [])):
            score += 0.5

        # タスクの緊急性や重要性を評価
        # （ここでは簡単な実装例を示していますが、より高度な評価ロジックを実装可能です）
        if "urgent" in task["description"].lower():
            score += 0.3
        if "important" in task["description"].lower():
            score += 0.2

        return score

    def run(self) -> None:
        """自律的なタスク実行のメインループ。"""
        while True:
            # 次のタスクを実行
            result = self.execute_next_task()
            if not result:
                break

            # 結果を分析し、新しいタスクを生成
            new_tasks = self.analyze_task_result(result)
            
            # 目的が達成されたかチェック
            if self.is_objective_achieved():
                break

    def is_objective_achieved(self) -> bool:
        """目的が達成されたかどうかを判断する。

        Returns:
            目的達成の判定結果
        """
        # ここでは簡単な判定ロジックを実装
        # より高度な判定ロジックを実装可能
        return (
            len(self.task_queue) == 0 and
            len(self.current_context["completed_tasks"]) > 0
        ) 