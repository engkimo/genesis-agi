"""タスク管理システム。"""
from typing import Any, Dict, List, Optional
from uuid import uuid4

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task
from genesis_agi.utils.cache import Cache


class TaskManager:
    """タスク管理システム。"""

    def __init__(
        self,
        llm_client: LLMClient,
        cache: Optional[Cache] = None,
        objective: str = "タスクの生成と実行",
    ):
        """初期化。

        Args:
            llm_client: LLMクライアント
            cache: キャッシュ
            objective: システムの目標
        """
        self.llm_client = llm_client
        self.cache = cache
        self.objective = objective
        self.operators: Dict[str, BaseOperator] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.current_tasks: List[Task] = []
        self.performance_metrics: Dict[str, Any] = {}

    def add_operator(self, operator: BaseOperator) -> None:
        """オペレーターを追加する。

        Args:
            operator: 追加するオペレーター
        """
        operator_type = operator.__class__.__name__
        self.operators[operator_type] = operator

    def create_initial_task(self) -> Task:
        """初期タスクを生成する。

        Returns:
            生成されたタスク
        """
        task = Task(
            id=f"task-{uuid4()}",
            name="初期タスク",
            description=f"目標「{self.objective}」の達成に向けた初期タスクを生成する",
            priority=1,
            metadata={"task_type": "creation"},
        )
        self.current_tasks.append(task)
        return task

    def get_next_task(self) -> Optional[Task]:
        """次に実行するタスクを取得する。

        Returns:
            次のタスク
        """
        if not self.current_tasks:
            return None

        # 優先度でソート
        self.current_tasks.sort(key=lambda x: x.priority, reverse=True)
        return self.current_tasks[0]

    def execute_task(self, task: Task) -> Dict[str, Any]:
        """タスクを実行する。

        Args:
            task: 実行するタスク

        Returns:
            実行結果
        """
        # タスクタイプに応じたオペレーターを選択
        operator_type = self._get_operator_type(task)
        operator = self.operators.get(operator_type)
        if not operator:
            raise ValueError(f"No operator found for task type: {operator_type}")

        # タスクの検証
        if not operator.validate(task):
            raise ValueError(f"Task validation failed: {task.dict()}")

        # コンテキストの準備
        context = self._prepare_context(operator.get_required_context())

        # タスクの実行
        result = operator.execute(task, context)

        # 履歴の更新
        self.task_history.append({
            "task": task.dict(),
            "result": result,
            "operator": operator_type,
        })

        # 現在のタスクから削除
        if task in self.current_tasks:
            self.current_tasks.remove(task)

        return result

    def create_new_tasks(self, task: Task, result: Dict[str, Any]) -> List[Task]:
        """新しいタスクを生成する。

        Args:
            task: 元のタスク
            result: 実行結果

        Returns:
            生成されたタスクのリスト
        """
        operator = self.operators.get("TaskCreationOperator")
        if not operator:
            raise ValueError("TaskCreationOperator not found")

        context = self._prepare_context(operator.get_required_context())
        creation_result = operator.execute(task, context)

        new_tasks = []
        for task_data in creation_result.get("new_tasks", []):
            new_task = Task(**task_data)
            self.current_tasks.append(new_task)
            new_tasks.append(new_task)

        return new_tasks

    def prioritize_tasks(self) -> None:
        """タスクの優先順位を更新する。"""
        if not self.current_tasks:
            return

        operator = self.operators.get("TaskPrioritizationOperator")
        if not operator:
            raise ValueError("TaskPrioritizationOperator not found")

        # 優先順位付けタスクの作成
        prioritization_task = Task(
            id=f"task-{uuid4()}",
            name="タスクの優先順位付け",
            description="現在のタスクリストの優先順位を最適化する",
            priority=1,
            metadata={"task_type": "prioritization"},
        )

        # コンテキストの準備
        context = self._prepare_context(operator.get_required_context())
        context["task_list"] = self.current_tasks

        # 優先順位付けの実行
        result = operator.execute(prioritization_task, context)

        # 優先順位の更新
        for task_data in result.get("prioritized_tasks", []):
            task_id = task_data["task_id"]
            for task in self.current_tasks:
                if task.id == task_id:
                    task.priority = task_data["priority"]
                    break

    def analyze_performance(self) -> Dict[str, Any]:
        """パフォーマンスを分析する。

        Returns:
            分析結果
        """
        # 基本的な指標の計算
        total_tasks = len(self.task_history)
        successful_tasks = sum(
            1 for entry in self.task_history
            if entry["result"].get("status") == "success"
        )
        success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0

        # パフォーマンス指標の更新
        self.performance_metrics.update({
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "success_rate": success_rate,
            "average_priority": sum(
                task.priority for task in self.current_tasks
            ) / len(self.current_tasks) if self.current_tasks else 0,
        })

        return self.performance_metrics

    def cleanup(self) -> None:
        """リソースのクリーンアップを行う。"""
        for operator in self.operators.values():
            operator.cleanup()

    def _get_operator_type(self, task: Task) -> str:
        """タスクに適したオペレータータイプを取得する。

        Args:
            task: タスク

        Returns:
            オペレータータイプ
        """
        task_type = task.metadata.get("task_type", "")
        if task_type == "creation":
            return "TaskCreationOperator"
        elif task_type == "execution":
            return "TaskExecutionOperator"
        elif task_type == "prioritization":
            return "TaskPrioritizationOperator"
        else:
            return "TaskExecutionOperator"  # デフォルト

    def _prepare_context(self, required_keys: List[str]) -> Dict[str, Any]:
        """実行コンテキストを準備する。

        Args:
            required_keys: 必要なコンテキストのキー

        Returns:
            実行コンテキスト
        """
        context = {}
        for key in required_keys:
            if key == "task_history":
                context[key] = self.task_history
            elif key == "objective":
                context[key] = self.objective
            elif key == "task_list":
                context[key] = self.current_tasks
            elif key == "performance_metrics":
                context[key] = self.performance_metrics

        return context 