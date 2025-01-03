"""タスク管理システム。"""
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging
import time
from datetime import datetime, timedelta

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task
from genesis_agi.utils.cache import Cache

# ロガーの設定
logger = logging.getLogger(__name__)

class TaskManager:
    """タスク管理システム。"""

    def __init__(
        self,
        llm_client: LLMClient,
        cache: Optional[Cache] = None,
        objective: str = "タスクの生成と実行",
        max_consecutive_errors: int = 3,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        execution_timeout: int = 300,  # 5分
        max_api_calls_per_minute: int = 50,
    ):
        """初期化。

        Args:
            llm_client: LLMクライアント
            cache: キャッシュ
            objective: システムの目標
            max_consecutive_errors: 連続エラーの最大許容数
            max_retries: リトライの最大回数
            retry_delay: リトライ間の待機時間（秒）
            execution_timeout: タスク実行のタイムアウト時間（秒）
            max_api_calls_per_minute: 1分あたりの最大API呼び出し回数
        """
        logger.info(f"TaskManagerを初期化: 目標「{objective}」")
        self.llm_client = llm_client
        self.cache = cache
        self.objective = objective
        self.operators: Dict[str, BaseOperator] = {}
        self.task_history: List[Dict[str, Any]] = []
        self.current_tasks: List[Task] = []
        self.performance_metrics: Dict[str, Any] = {}
        
        # 実行制御用パラメータ
        self.max_consecutive_errors = max_consecutive_errors
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.execution_timeout = execution_timeout
        self.max_api_calls_per_minute = max_api_calls_per_minute
        
        # API呼び出し制御用
        self.api_call_history: List[datetime] = []
        self.consecutive_errors = 0

    def add_operator(self, operator: BaseOperator) -> None:
        """オペレーターを追加する。

        Args:
            operator: 追加するオペレーター
        """
        operator_type = operator.__class__.__name__
        logger.info(f"オペレーターを追加: {operator_type}")
        self.operators[operator_type] = operator

    def create_initial_task(self) -> Task:
        """初期タスクを生成する。

        Returns:
            生成されたタスク
        """
        logger.info("初期タスクの生成を開始")
        task = Task(
            id=f"task-{uuid4()}",
            name="初期タスク",
            description=f"目標「{self.objective}」の達成に向けた初期タスクを生成する",
            priority=1,
            metadata={"task_type": "creation"},
        )
        self.current_tasks.append(task)
        logger.info(f"初期タスクを生成: ID={task.id}, 名前={task.name}")
        return task

    def get_next_task(self) -> Optional[Task]:
        """次に実行するタスクを取得する。

        Returns:
            次のタスク
        """
        logger.debug(f"次のタスクを取得中 (現在のタスク数: {len(self.current_tasks)})")
        if not self.current_tasks:
            logger.info("実行可能なタスクがありません")
            return None

        # 優先度でソート
        self.current_tasks.sort(key=lambda x: x.priority, reverse=True)
        next_task = self.current_tasks[0]
        logger.info(f"次のタスクを選択: ID={next_task.id}, 名前={next_task.name}, 優先度={next_task.priority}")
        return next_task

    def execute_task(self, task: Task) -> Dict[str, Any]:
        """タスクを実行する。

        Args:
            task: 実行するタスク

        Returns:
            実行結果
        """
        logger.info(f"タスク実行開始: ID={task.id}, 名前={task.name}")
        
        # API呼び出し制限のチェックと待機
        self._wait_for_api_limit()
        
        start_time = time.time()
        retries = 0
        last_error = None
        
        while retries <= self.max_retries:
            try:
                # タイムアウトチェック
                if time.time() - start_time > self.execution_timeout:
                    logger.warning(f"タスク実行がタイムアウトしました: {task.name}")
                    return {"status": "timeout", "error": "実行時間が制限を超えました"}
                
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
                
                # 成功した場合、連続エラーカウントをリセット
                self.consecutive_errors = 0
                
                # API呼び出し履歴の更新
                self.api_call_history.append(datetime.now())
                
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

            except Exception as e:
                last_error = e
                retries += 1
                self.consecutive_errors += 1
                
                if self.consecutive_errors >= self.max_consecutive_errors:
                    logger.error(f"連続エラーが制限を超えました: {self.consecutive_errors}回")
                    raise Exception("連続エラーが多すぎます")
                
                if retries <= self.max_retries:
                    wait_time = self.retry_delay * (2 ** (retries - 1))  # 指数バックオフ
                    logger.warning(f"タスク実行に失敗、{wait_time}秒後にリトライ ({retries}/{self.max_retries}): {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"リトライ回数が上限に達しました: {str(e)}")
                    raise

        return {"status": "error", "error": str(last_error)}

    def _wait_for_api_limit(self) -> None:
        """API呼び出し制限に基づいて待機する。"""
        now = datetime.now()
        # 1分以上前の呼び出し履歴を削除
        self.api_call_history = [t for t in self.api_call_history if now - t <= timedelta(minutes=1)]
        
        # 制限に達している場合は待機
        if len(self.api_call_history) >= self.max_api_calls_per_minute:
            oldest_call = self.api_call_history[0]
            wait_time = 60 - (now - oldest_call).total_seconds()
            if wait_time > 0:
                logger.info(f"API制限に達しました。{wait_time:.1f}秒待機します")
                time.sleep(wait_time)

    def create_new_tasks(self, task: Task, result: Dict[str, Any]) -> List[Task]:
        """新しいタスクを生成する。

        Args:
            task: 元のタスク
            result: 実行結果

        Returns:
            生成されたタスクのリスト
        """
        logger.info(f"新規タスク生成開始: 元タスク={task.name}")
        
        operator = self.operators.get("TaskCreationOperator")
        if not operator:
            logger.error("TaskCreationOperatorが見つかりません")
            raise ValueError("TaskCreationOperator not found")

        context = self._prepare_context(operator.get_required_context())
        logger.debug("タスク生成のコンテキストを準備完了")
        
        creation_result = operator.execute(task, context)
        logger.debug(f"タスク生成の実行結果: {creation_result}")

        new_tasks = []
        for task_data in creation_result.get("new_tasks", []):
            new_task = Task(**task_data)
            self.current_tasks.append(new_task)
            new_tasks.append(new_task)
            logger.info(f"新規タスクを追加: ID={new_task.id}, 名前={new_task.name}")

        logger.info(f"タスク生成完了: {len(new_tasks)}件のタスクを生成")
        return new_tasks

    def prioritize_tasks(self) -> None:
        """タスクの優先順位を更新する。"""
        logger.info("タスクの優先順位付けを開始")
        if not self.current_tasks:
            logger.info("優先順位付けするタスクがありません")
            return

        operator = self.operators.get("TaskPrioritizationOperator")
        if not operator:
            logger.error("TaskPrioritizationOperatorが見つかりません")
            raise ValueError("TaskPrioritizationOperator not found")

        # 優先順位付けタスクの作成
        prioritization_task = Task(
            id=f"task-{uuid4()}",
            name="タスクの優先順位付け",
            description="現在のタスクリストの優先順位を最適化する",
            priority=1,
            metadata={"task_type": "prioritization"},
        )
        logger.debug(f"優先順位付けタスクを作成: ID={prioritization_task.id}")

        # コンテキストの準備
        context = self._prepare_context(operator.get_required_context())
        context["task_list"] = self.current_tasks

        # 優先順位付けの実行
        logger.debug("優先順位付けを実行中")
        result = operator.execute(prioritization_task, context)

        # 優先順位の更新
        update_count = 0
        for task_data in result.get("prioritized_tasks", []):
            task_id = task_data.get("id")
            new_priority = task_data.get("priority")
            if task_id and new_priority is not None:
                for task in self.current_tasks:
                    if task.id == task_id:
                        old_priority = task.priority
                        task.priority = new_priority
                        logger.debug(f"タスク{task_id}の優先度を更新: {old_priority} → {new_priority}")
                        update_count += 1
                        break

        logger.info(f"優先順位付け完了: {update_count}件のタスクを更新")

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
        if task.metadata is None:
            return "TaskExecutionOperator"
            
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
                context[key] = [task for task in self.current_tasks if task is not None]
            elif key == "performance_metrics":
                context[key] = self.performance_metrics

        return context 