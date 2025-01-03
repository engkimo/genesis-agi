"""Unified task and workflow management system."""
from typing import Any, Dict, List, Optional
from uuid import uuid4
import logging
import time
from datetime import datetime, timedelta

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators import BaseOperator, Task
from genesis_agi.utils.cache import Cache
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.operators.operator_generator import OperatorGenerator
from genesis_agi.core.meta_learning import MetaLearner

logger = logging.getLogger(__name__)


class UnifiedManager:
    """タスクとワークフローを統合的に管理するシステム。"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: OperatorRegistry,
        cache: Optional[Cache] = None,
        objective: str = "タスクの生成と実行",
        meta_learner: Optional[MetaLearner] = None,
        operator_generator: Optional[OperatorGenerator] = None,
        max_iterations: int = 10,
        iteration_delay: float = 1.0,
        max_execution_time: int = 600,
    ):
        """初期化。

        Args:
            llm_client: LLMクライアント
            registry: オペレーターレジストリ
            cache: キャッシュ
            objective: システムの目標
            meta_learner: メタ学習コンポーネント
            operator_generator: オペレータージェネレーター
            max_iterations: 最大イテレーション数
            iteration_delay: イテレーション間の待機時間（秒）
            max_execution_time: 最大実行時間（秒）
        """
        self.llm_client = llm_client
        self.registry = registry
        self.cache = cache
        self.objective = objective
        self.meta_learner = meta_learner
        self.operator_generator = operator_generator
        self.max_iterations = max_iterations
        self.iteration_delay = iteration_delay
        self.max_execution_time = max_execution_time
        
        self.execution_history: List[Dict[str, Any]] = []
        self.task_queue: List[Task] = []
        self.current_context: Dict[str, Any] = {
            "objective": objective,
            "completed_tasks": [],
            "current_state": {},
            "performance_metrics": {},
            "meta_knowledge": self._initialize_meta_knowledge()
        }

        # meta_learnerが必要な場合は初期化
        if self.meta_learner is None and meta_learner is None:
            self.meta_learner = MetaLearner(
                llm_client=llm_client,
                registry=registry,
                cache=cache,
                operator_generator=self.operator_generator
            )

        # operator_generatorが必要な場合は初期化
        if self.operator_generator is None and operator_generator is None:
            self.operator_generator = OperatorGenerator(
                llm_client=llm_client,
                registry=registry,
                cache=cache
            )

    def analyze_and_create_task(self, task_description: str) -> Task:
        """タスクを分析し、必要なオペレーターを生成して、タスクを作成する。

        Args:
            task_description: タスクの説明

        Returns:
            作成されたタスク
        """
        # メタ学習を使用して最適な生成戦略を取得
        generation_strategy = self.meta_learner.optimize_generation_strategy(
            task_description,
            self.current_context,
            self.execution_history
        )

        # タスクの分析とオペレータータイプの決定
        analysis = self.llm_client.analyze_task({
            "description": task_description,
            "context": self.meta_learner._prepare_context_for_json(self.current_context),
            "generation_strategy": generation_strategy
        })

        operator_type = analysis["required_operator_type"]
        
        # 必要なオペレーターが存在しない場合は生成
        if operator_type not in self.registry._operators:
            operator_class = self.operator_generator.generate_operator(
                task_description,
                self.current_context,
                generation_strategy
            )
            self.registry.register_operator(operator_class)

        # タスクの作成
        return self.create_task(
            description=task_description,
            task_type=operator_type,
            params=analysis.get("required_params", {})
        )

    def execute_next_task(self) -> Optional[Dict[str, Any]]:
        """次のタスクを実行する。

        Returns:
            実行結果
        """
        if not self.task_queue:
            return None

        # 最適なタスクを選択
        next_task = self.select_next_task()
        if not next_task:
            return None

        try:
            # オペレーターの取得または生成
            operator_type = next_task.metadata["task_type"]
            if operator_type not in self.registry._operators:
                # メタ学習を使用して最適な生成戦略を取得
                generation_strategy = self.meta_learner.optimize_generation_strategy(
                    next_task.description,
                    self.current_context,
                    self.execution_history
                )
                
                operator_class = self.operator_generator.generate_operator(
                    next_task.description,
                    self.current_context,
                    generation_strategy
                )
                self.registry.register_operator(operator_class)

            operator = self.registry.get_operator(operator_type)
            
            # コンテキストの準備
            context = self._prepare_context(operator.get_required_context())
            
            # タスクの実行
            result = operator.execute(next_task, context)

            # パフォーマンスの分析と改善
            self._analyze_and_improve_operator(operator_type, result)

            # 実行履歴の更新
            execution_record = {
                "task": next_task.dict(),
                "result": result,
                "operator": operator_type,
                "meta_data": {
                    "generation_strategy": self.meta_learner._prepare_context_for_json(generation_strategy),
                    "performance_metrics": result.get("performance_metrics", {})
                }
            }
            self.execution_history.append(execution_record)
            self.current_context["completed_tasks"].append(next_task.id)

            # 新しいタスクの生成
            if isinstance(result, dict) and result.get("generated_tasks"):
                for task_spec in result["generated_tasks"]:
                    self.analyze_and_create_task(task_spec["description"])

            return result

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "task_id": next_task.id
            }

    def _analyze_and_improve_operator(self, operator_type: str, result: Dict[str, Any]) -> None:
        """オペレーターのパフォーマンスを分析し、必要に応じて改善する。

        Args:
            operator_type: オペレーターの種類
            result: 実行結果
        """
        # パフォーマンスデータの収集
        performance_data = {
            "execution_time": result.get("execution_time"),
            "memory_usage": result.get("memory_usage"),
            "success_rate": 1 if result.get("status") == "success" else 0,
            "output_quality": result.get("quality_metrics", {})
        }

        # オペレーターチェーンの分析
        chain_analysis = self.operator_generator.analyze_operator_chain(
            self.execution_history
        )

        # メタ学習を使用して進化戦略を取得
        evolution_strategy = self.meta_learner.suggest_evolution_strategy(
            self.registry.get_operator(operator_type),
            self.current_context,
            performance_data
        )

        # 改善が必要な場合、オペレーターを進化させる
        if (
            chain_analysis["efficiency"] < 0.8 or
            operator_type in chain_analysis["bottlenecks"]
        ):
            original_operator = self.registry.get_operator(operator_type)
            evolved_operator = self.operator_generator.evolve_operator(
                operator_type,
                performance_data,
                evolution_strategy
            )
            
            # 進化パターンの学習
            self.meta_learner.learn_evolution_patterns(
                original_operator,
                evolved_operator,
                performance_data,
                self.current_context
            )
            
            # 進化したオペレーターを登録
            self.registry.register_operator(evolved_operator)

    def run(self) -> None:
        """タスクを自律的に実行する。"""
        start_time = time.time()
        iteration = 0
        
        while iteration < self.max_iterations:
            # 実行時間のチェック
            if time.time() - start_time > self.max_execution_time:
                logger.warning("最大実行時間を超過しました")
                break
            
            # 次のタスクを取得
            next_task = self.select_next_task()
            if not next_task:
                # 新しいタスクを生成
                self._generate_new_tasks()
                continue
            
            try:
                # タスクの実行
                logger.info(f"タスク実行: {next_task.name}")
                result = self.execute_task(next_task)
                
                # 実行結果の記録
                self.execution_history.append({
                    "task": next_task.dict(),
                    "result": result,
                    "timestamp": datetime.now()
                })
                
                # 成功した場合は新しいタスクを生成
                if result.get("status") == "success":
                    self.create_new_tasks(next_task, result)
                
            except Exception as e:
                logger.error(f"タスク実行中にエラーが発生: {str(e)}")
                # エラーを記録して次のタスクへ
                self.execution_history.append({
                    "task": next_task.dict(),
                    "result": {"status": "error", "error": str(e)},
                    "timestamp": datetime.now()
                })
            
            # イテレーション間の待機
            time.sleep(self.iteration_delay)
            iteration += 1
            
            # 進捗状況の表示
            self._display_progress(iteration)
        
        if iteration >= self.max_iterations:
            logger.warning(f"最大イテレーション数（{self.max_iterations}）に達しました")
        
    def _display_progress(self, iteration: int) -> None:
        """進捗状況を表示する。

        Args:
            iteration: 現在のイテレーション数
        """
        logger.info(f"進捗: {iteration}/{self.max_iterations} "
                   f"({iteration/self.max_iterations*100:.1f}%)")
        
        # 成功率の計算
        success_count = sum(
            1 for record in self.execution_history
            if record["result"].get("status") == "success"
        )
        if self.execution_history:
            success_rate = success_count / len(self.execution_history) * 100
            logger.info(f"成功率: {success_rate:.1f}%")

    def _display_execution_stats(self) -> None:
        """実行統計を表示する。"""
        total_tasks = len(self.execution_history)
        successful_tasks = sum(
            1 for record in self.execution_history
            if record["result"].get("status") == "success"
        )
        
        logger.info("\n=== 実行統計 ===")
        logger.info(f"総タスク数: {total_tasks}")
        logger.info(f"成功タスク数: {successful_tasks}")
        if total_tasks > 0:
            logger.info(f"全体の成功率: {successful_tasks/total_tasks*100:.1f}%")

    def _initialize_meta_knowledge(self) -> Dict[str, Any]:
        """メタ知識を初期化する。

        Returns:
            初期化されたメタ知識
        """
        return {
            "generation_strategies": {},
            "evolution_patterns": [],
            "context_dependencies": {},
            "successful_patterns": [],
            "failed_patterns": []
        }

    def _generate_new_tasks(self) -> None:
        """新しいタスクを生成する。"""
        # プロンプトの準備
        prompt = {
            "objective": self.objective,
            "current_context": {
                k: str(v) if isinstance(v, datetime) else v
                for k, v in self.current_context.items()
            },
            "execution_history": [
                {
                    k: str(v) if isinstance(v, datetime) else v
                    for k, v in item.items()
                }
                for item in self.execution_history
            ]
        }
        
        # LLMを使用してタスクを生成
        response = self.llm_client.suggest_new_tasks(prompt)
        
        # 生成されたタスクを作成
        self._create_generated_tasks(response["tasks"])

    def create_task(
        self,
        description: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: float = 1.0
    ) -> Task:
        """タスクを作成する。

        Args:
            description: タスクの説明
            task_type: タスクの種類
            params: タスクのパラメータ
            priority: 優先度

        Returns:
            作成されたタスク
        """
        task = Task(
            id=f"task-{uuid4()}",
            name=description,
            description=description,
            priority=priority,
            metadata={
                "task_type": task_type,
                "params": params or {},
                "context": self.current_context.copy()
            }
        )
        self.task_queue.append(task)
        return task

    def select_next_task(self) -> Optional[Task]:
        """次に実行すべきタスクを選択する。

        Returns:
            選択されたタスク
        """
        if not self.task_queue:
            return None

        # LLMを使用してタスクの優先順位を更新
        self._update_task_priorities()
        
        # 優先度でソート
        self.task_queue.sort(key=lambda x: x.priority, reverse=True)
        
        # 最適なタスクを選択
        selected_task = self.task_queue[0]
        self.task_queue.remove(selected_task)
        return selected_task

    def _update_task_priorities(self) -> None:
        """LLMを使用してタスクの優先順位を更新する。"""
        context = {
            "objective": self.objective,
            "current_tasks": [task.dict() for task in self.task_queue],
            "completed_tasks": self.current_context["completed_tasks"],
            "execution_history": self.execution_history
        }

        # LLMに優先順位付けを依頼
        response = self.llm_client.prioritize_tasks(context)
        
        # 優先順位の更新
        for priority_info in response.get("priorities", []):
            task_id = priority_info["task_id"]
            new_priority = priority_info["priority"]
            for task in self.task_queue:
                if task.id == task_id:
                    task.priority = new_priority
                    break

    def _create_generated_tasks(self, task_specs: List[Dict[str, Any]]) -> None:
        """生成されたタスク仕様から新しいタスクを作成する。

        Args:
            task_specs: タスク仕様のリスト
        """
        for spec in task_specs:
            self.create_task(
                description=spec["description"],
                task_type=spec["operator_type"],
                params=spec.get("params", {}),
                priority=spec.get("priority", 1.0)
            )

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
                context[key] = self.execution_history
            elif key == "objective":
                context[key] = self.objective
            elif key == "task_list":
                context[key] = self.task_queue
            elif key == "performance_metrics":
                context[key] = self.current_context["performance_metrics"]
            elif key in self.current_context:
                context[key] = self.current_context[key]

        return context

    def _update_performance_metrics(self, result: Dict[str, Any]) -> None:
        """パフォーマンス指標を更新する。

        Args:
            result: タスク実行結果
        """
        metrics = self.current_context["performance_metrics"]
        metrics["total_tasks"] = len(self.execution_history)
        metrics["successful_tasks"] = sum(
            1 for entry in self.execution_history
            if entry["result"].get("status") == "success"
        )
        metrics["success_rate"] = (
            metrics["successful_tasks"] / metrics["total_tasks"]
            if metrics["total_tasks"] > 0 else 0
        )
        
        # メタ知識の更新
        self.current_context["meta_knowledge"] = {
            "generation_strategies": self.meta_learner.generation_strategies,
            "evolution_patterns": self.meta_learner.evolution_patterns,
            "context_dependencies": self.meta_learner.meta_knowledge["context_dependencies"]
        }

    def _is_objective_achieved(self) -> bool:
        """目的が達成されたかどうかを判断する。

        Returns:
            目的達成の判定結果
        """
        # LLMを使用して目的達成を評価
        context = {
            "objective": self.objective,
            "execution_history": self.execution_history,
            "performance_metrics": self.current_context["performance_metrics"]
        }
        
        response = self.llm_client.evaluate_objective_completion(context)
        return response.get("is_achieved", False) 