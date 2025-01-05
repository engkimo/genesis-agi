"""Unified task and workflow management system."""
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from genesis_agi.core.meta_learning import MetaLearner
from genesis_agi.llm.client import LLMClient
from genesis_agi.models.task import ExecutionRecord, Task, TaskMetadata
from genesis_agi.operators.operator_generator import OperatorGenerator
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.utils.cache import Cache

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
        """初期化。"""
        self.llm_client = llm_client
        self.registry = registry
        self.cache = cache
        self.objective = objective
        self.meta_learner = meta_learner
        self.operator_generator = operator_generator
        self.max_iterations = max_iterations
        self.iteration_delay = iteration_delay
        self.max_execution_time = max_execution_time

        self.execution_history: List[ExecutionRecord] = []
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

        Raises:
            ValueError: タスクの説明が無効な場合
            RuntimeError: タスクの生成に失敗した場合
        """
        if not task_description:
            raise ValueError("タスクの説明が必要です")

        try:
            # タスクの分析とオペレータータイプの決定
            analysis = self.llm_client.analyze_task({
                "description": task_description,
                "context": self._prepare_context_for_json(self.current_context),
                "generation_strategy": {
                    "strategy_type": "adaptive",
                    "parameters": {
                        "complexity": "medium",
                        "focus_areas": ["error_handling", "performance_optimization"]
                    }
                }
            })

            if not analysis or "required_operator_type" not in analysis:
                raise ValueError("タスクの分析に失敗しました")

            operator_type = analysis["required_operator_type"]
            logger.info(f"必要なオペレータータイプ: {operator_type}")

            # 必要なオペレーターが存在しない場合は生成
            if not self.registry.has_operator(operator_type):
                logger.info(f"オペレーター '{operator_type}' が存在しないため、生成を開始します")
                try:
                    # 生成戦略の準備
                    generation_strategy = {
                        "strategy_type": "adaptive",
                        "parameters": {
                            "task_description": task_description,
                            "operator_type": operator_type,
                            "complexity": analysis["required_params"].get("estimated_complexity", "medium"),
                            "focus_areas": ["error_handling", "performance_optimization"]
                        }
                    }

                    # オペレーターの生成
                    operator_class = self.operator_generator.generate_operator(
                        task_description,
                        self.current_context,
                        generation_strategy
                    )
                    logger.info(f"オペレーター '{operator_type}' を生成しました")

                    # オペレーターの登録
                    self.registry.register_operator(operator_class)
                    logger.info(f"オペレーター '{operator_type}' を登録しました")

                except Exception as e:
                    error_msg = f"オペレーターの生成と登録に失敗: {str(e)}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from e

            # タスクの作成
            try:
                task = self.create_task(
                    description=task_description,
                    task_type=operator_type,
                    params=analysis.get("required_params", {}),
                    priority=float(analysis["required_params"].get("priority", 1.0))
                )
                logger.info(f"タスクを作成しました: {task.id}")
                return task

            except Exception as e:
                error_msg = f"タスクの作成に失敗: {str(e)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        except Exception as e:
            logger.error(f"タスクの生成中にエラーが発生: {str(e)}")
            # エラー時のフォールバックタスクを作成
            try:
                return self.create_task(
                    description=task_description,
                    task_type="DataAnalysisOperator",  # デフォルトのオペレーター
                    params={},
                    priority=1.0
                )
            except Exception as fallback_error:
                error_msg = f"フォールバックタスクの作成にも失敗: {str(fallback_error)}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from fallback_error

    def execute_next_task(self) -> Optional[Dict[str, Any]]:
        """次のタスクを実行する。"""
        if not self.task_queue:
            return None

        # 最適なタスクを選択
        next_task = self.select_next_task()
        if not next_task:
            return None

        try:
            # オペレーターの取得または生成
            operator_type = next_task.metadata.task_type
            logger.debug(f"オペレータータイプ: {operator_type}")

            operator = self.registry.get_operator(operator_type)
            if not operator:
                logger.debug("オペレーターが見つからないため、TaskExecutionOperatorを使用")
                from genesis_agi.operators.task_execution_operator import (
                    TaskExecutionOperator,
                )
                operator = TaskExecutionOperator(self.llm_client)

            # コンテキストの準備
            context = {
                "objective": self.objective,
                "task_history": [
                    {
                        "task": record.task.model_dump(mode='json'),
                        "result": record.result,
                        "operator": record.operator
                    }
                    for record in self.execution_history
                ],
                "current_state": {
                    "total_tasks": len(self.execution_history),
                    "successful_tasks": sum(
                        1 for record in self.execution_history
                        if record.result.get("status") == "success"
                    ),
                    "failed_tasks": sum(
                        1 for record in self.execution_history
                        if record.result.get("status") in ["failed", "error"]
                    )
                }
            }

            logger.debug(f"実行コンテキスト: {context}")

            # タスクの実行
            start_time = time.time()
            result = operator.execute(next_task, context)
            execution_time = time.time() - start_time

            logger.debug(f"実行結果: {result}")

            # 実行結果の検証と整形
            if not isinstance(result, dict):
                result = {"output": result}

            if "status" not in result:
                result["status"] = "success" if result.get("output") else "failed"

            result.update({
                "execution_time": execution_time,
                "task_id": next_task.id,
                "performance_metrics": {
                    "execution_success": result.get("status") == "success",
                    "quality_score": result.get("metrics", {}).get("quality_score", 0.5)
                }
            })

            # パフォーマンスの分析と改善
            self._analyze_and_improve_operator(operator_type, result)

            # 実行履歴の更新
            record = ExecutionRecord(
                task=next_task,
                result=result,
                operator=operator_type,
                meta_data={
                    "context": context,
                    "performance_metrics": result.get("performance_metrics", {})
                }
            )
            self.execution_history.append(record)
            self.current_context["completed_tasks"].append(next_task.id)

            # パフォーマンス指標の更新
            self._update_performance_metrics(result)

            # 新しいタスクの生成
            if result.get("status") == "success":
                self._generate_new_tasks()

            return result

        except Exception as e:
            logger.error(f"タスク実行中にエラーが発生: {str(e)}")
            error_result = {
                "status": "failed",
                "error": str(e),
                "task_id": next_task.id,
                "output": f"タスクの実行中にエラーが発生しました: {str(e)}",
                "metrics": {
                    "execution_time": 0,
                    "quality_score": 0
                },
                "performance_metrics": {
                    "execution_success": False,
                    "error_type": type(e).__name__
                }
            }

            # エラー時の実行履歴の更新
            record = ExecutionRecord(
                task=next_task,
                result=error_result,
                operator=operator_type,
                meta_data={
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            self.execution_history.append(record)

            return error_result

    def _analyze_and_improve_operator(self, operator_type: str, result: Dict[str, Any]) -> None:
        """オペレーターのパフォーマンスを分析し、必要に応じて改善する。

        Args:
            operator_type: オペレーターの種類
            result: 実行結果
        """
        # パフォーマンスデータの収集
        performance_data = {
            "execution_time": result.get("execution_time", 0),
            "success_rate": 1 if result.get("status") == "success" else 0,
            "output_quality": result.get("performance_metrics", {}).get("output_quality", 0),
            "error_type": result.get("error") if result.get("status") == "failed" else None
        }

        # 実行履歴からの追加データ
        operator_history = [
            record for record in self.execution_history
            if record.operator == operator_type
        ]

        if operator_history:
            success_rate = sum(
                1 for record in operator_history
                if record.result.get("status") == "success"
            ) / len(operator_history)

            performance_data.update({
                "historical_success_rate": success_rate,
                "execution_count": len(operator_history)
            })

        # 改善が必要かどうかの判断
        needs_improvement = (
            performance_data["success_rate"] == 0 or
            performance_data.get("historical_success_rate", 0) < 0.5 or
            performance_data.get("output_quality", 0) < 0.5
        )

        if needs_improvement:
            try:
                # 現在のオペレーターを取得
                current_operator = self.registry.get_operator(operator_type)
                if not current_operator:
                    return

                # 進化戦略の生成
                evolution_strategy = {
                    "target_metrics": ["success_rate", "output_quality"],
                    "improvement_focus": (
                        "error_handling" if performance_data["success_rate"] == 0
                        else "quality_optimization"
                    ),
                    "historical_data": {
                        "success_rate": performance_data.get("historical_success_rate", 0),
                        "execution_count": performance_data.get("execution_count", 0)
                    }
                }

                # オペレーターの進化
                evolved_operator = self.operator_generator.evolve_operator(
                    operator_type,
                    performance_data,
                    evolution_strategy
                )

                # 進化したオペレーターの検証
                if evolved_operator and hasattr(evolved_operator, "execute"):
                    # 進化したオペレーターを登録
                    self.registry.register_operator(evolved_operator)

                    # メタ知識の更新
                    if self.meta_learner:
                        self.meta_learner.learn_evolution_patterns(
                            current_operator,
                            evolved_operator,
                            performance_data,
                            evolution_strategy
                        )

            except Exception as e:
                logger.error(f"オペレーターの進化中にエラーが発生: {str(e)}")

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
                result = self.execute_next_task()

                if not result:
                    result = {
                        "status": "failed",
                        "output": "タスクの実行に失敗しました",
                        "metrics": {
                            "execution_time": 0,
                            "quality_score": 0
                        }
                    }

                # 実行結果の記録
                record = ExecutionRecord(
                    task=next_task,
                    result=result,
                    operator=next_task.metadata.task_type,
                    meta_data={
                        "context": self.current_context.copy(),
                        "performance_metrics": result.get("performance_metrics", {})
                    }
                )
                self.execution_history.append(record)

                # 成功した場合は新しいタスクを生成
                if result.get("status") == "success":
                    self._generate_new_tasks()

            except Exception as e:
                logger.error(f"タスク実行中にエラーが発生: {str(e)}")
                # エラーを記録して次のタスクへ
                error_result = {
                    "status": "failed",
                    "output": f"エラーが発生しました: {str(e)}",
                    "metrics": {
                        "execution_time": 0,
                        "quality_score": 0
                    }
                }
                record = ExecutionRecord(
                    task=next_task,
                    result=error_result,
                    operator=next_task.metadata.task_type,
                    meta_data={
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                self.execution_history.append(record)

            # イテレーション間の待機
            time.sleep(self.iteration_delay)
            iteration += 1

            # 進捗状況の表示
            self._display_progress(iteration)

        if iteration >= self.max_iterations:
            logger.warning(f"最大イテレーション数（{self.max_iterations}）に達しました")

    def _display_progress(self, iteration: int) -> None:
        """進捗状況を表示する。"""
        logger.info(f"進捗: {iteration}/{self.max_iterations} "
                   f"({iteration/self.max_iterations*100:.1f}%)")

        # 成功率の計算
        success_count = sum(
            1 for record in self.execution_history
            if record.result.get("status") == "success"
        )
        logger.debug(f"実行履歴の長さ: {len(self.execution_history)}")
        logger.debug("実行結果の詳細:")
        for i, record in enumerate(self.execution_history):
            logger.debug(f"タスク {i+1}:")
            logger.debug(f"  - ステータス: {record.result.get('status')}")
            logger.debug(f"  - 品質スコア: {record.result.get('metrics', {}).get('quality_score')}")
            logger.debug(f"  - 出力: {record.result.get('output')}")

        if self.execution_history:
            success_rate = success_count / len(self.execution_history) * 100
            logger.info(f"成功率: {success_rate:.1f}% (成功: {success_count}, 総数: {len(self.execution_history)})")

    def _display_execution_stats(self) -> None:
        """実行統計を表示する。"""
        total_tasks = len(self.execution_history)
        successful_tasks = sum(
            1 for record in self.execution_history
            if record.result.get("status") == "success"
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
        try:
            # 実行履歴をJSON直列化可能な形式に変換
            serializable_history = [
                record.model_dump(mode='json')
                for record in self.execution_history
            ]

            # コンテキストをJSON直列化可能な形式に変換
            serializable_context = {
                k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in self.current_context.items()
            }

            # LLMに新しいタスクの生成を依頼
            response = self.llm_client.generate_tasks({
                "objective": self.objective,
                "context": serializable_context,
                "execution_history": serializable_history,
                "current_state": {
                    "total_tasks": len(self.execution_history),
                    "successful_tasks": sum(
                        1 for record in self.execution_history
                        if record.result.get("status") == "success"
                    ),
                    "failed_tasks": sum(
                        1 for record in self.execution_history
                        if record.result.get("status") == "failed"
                    )
                }
            })

            # レスポンスの形式をチェック
            if isinstance(response, dict):
                tasks = response.get("tasks", [])
                if not tasks and "task" in response:
                    tasks = [response["task"]]
            elif isinstance(response, list):
                tasks = response
            else:
                tasks = []

            if tasks:
                self._create_generated_tasks(tasks)
                logger.info(f"{len(tasks)}個の新しいタスクを生成しました")
            else:
                logger.warning("新しいタスクは生成されませんでした")

        except Exception as e:
            logger.error(f"タスク生成中にエラーが発生: {str(e)}")

    def create_task(
        self,
        description: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: float = 1.0
    ) -> Task:
        """タスクを作成する。"""
        metadata = TaskMetadata(
            task_type=task_type,
            params=params or {},
            context=self.current_context.copy()
        )

        task = Task(
            id=f"task-{uuid4()}",
            name=description,
            description=description,
            priority=priority,
            metadata=metadata
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
            "current_tasks": [task.model_dump(mode='json') for task in self.task_queue],
            "completed_tasks": self.current_context["completed_tasks"],
            "execution_history": [record.model_dump(mode='json') for record in self.execution_history]
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
        """生成されたタスク仕様から新しいタスクを作成する。"""
        for spec in task_specs:
            self.create_task(
                description=spec["description"],
                task_type=spec.get("operator_type", "default"),
                params=spec.get("params", {}),
                priority=float(spec.get("priority", 1.0))
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
        metrics = self.current_context.setdefault("performance_metrics", {})

        # 基本的な実行統計
        metrics["total_tasks"] = len(self.execution_history)

        # 成功したタスクの数を計算（より寛容な判定基準を使用）
        successful_tasks = sum(
            1 for record in self.execution_history
            if (
                isinstance(record.result, dict) and
                (
                    record.result.get("status") == "success" or
                    record.result.get("metrics", {}).get("quality_score", 0) >= 0.3 or
                    record.result.get("metrics", {}).get("progress_score", 0) >= 0.3 or
                    record.result.get("metrics", {}).get("confidence_score", 0) >= 0.3
                )
            )
        )

        logger.debug("パフォーマンス指標の更新:")
        logger.debug(f"  - 総タスク数: {metrics['total_tasks']}")
        logger.debug(f"  - 成功タスク数: {successful_tasks}")
        logger.debug("各タスクの判定基準:")
        for record in self.execution_history:
            if isinstance(record.result, dict):
                task_metrics = record.result.get("metrics", {})
                status = record.result.get("status")
                quality_score = task_metrics.get("quality_score", 0)
                progress_score = task_metrics.get("progress_score", 0)
                confidence_score = task_metrics.get("confidence_score", 0)
                logger.debug(
                    f"  - ステータス: {status}, "
                    f"品質スコア: {quality_score:.2f}, "
                    f"進捗スコア: {progress_score:.2f}, "
                    f"信頼度スコア: {confidence_score:.2f}"
                )
                logger.debug(
                    f"    -> 成功判定: {status == 'success' or quality_score >= 0.3 or progress_score >= 0.3 or confidence_score >= 0.3}"
                )

        metrics["successful_tasks"] = successful_tasks

        # 失敗したタスクの数を計算
        failed_tasks = sum(
            1 for record in self.execution_history
            if (
                isinstance(record.result, dict) and
                record.result.get("status") == "failed" and
                all(
                    record.result.get("metrics", {}).get(score, 0) < 0.3
                    for score in ["quality_score", "progress_score", "confidence_score"]
                )
            )
        )
        metrics["failed_tasks"] = failed_tasks

        # 成功率の計算（より寛容な計算方法）
        total_completed = metrics["total_tasks"]
        logger.debug(f"total_completed: {total_completed}")
        metrics["success_rate"] = (
            successful_tasks / total_completed
            if total_completed > 0 else 0.0
        )

        # 実行時間の統計
        execution_times = [
            float(record.result.get("metrics", {}).get("execution_time", 0))
            for record in self.execution_history
            if isinstance(record.result, dict)
        ]

        if execution_times:
            metrics["avg_execution_time"] = sum(execution_times) / len(execution_times)
            metrics["max_execution_time"] = max(execution_times)
            metrics["min_execution_time"] = min(execution_times)

        # オペレーター別の統計
        operator_stats = {}
        for record in self.execution_history:
            if not record.operator:
                continue

            operator = record.operator
            if operator not in operator_stats:
                operator_stats[operator] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_quality_score": 0,
                    "avg_progress_score": 0,
                    "avg_confidence_score": 0
                }

            stats = operator_stats[operator]
            stats["total"] += 1

            if isinstance(record.result, dict):
                task_metrics = record.result.get("metrics", {})
                if any(
                    task_metrics.get(score, 0) >= 0.3
                    for score in ["quality_score", "progress_score", "confidence_score"]
                ):
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1

                # 平均スコアの更新
                stats["avg_quality_score"] = (
                    (stats["avg_quality_score"] * (stats["total"] - 1) +
                     task_metrics.get("quality_score", 0)) / stats["total"]
                )
                stats["avg_progress_score"] = (
                    (stats["avg_progress_score"] * (stats["total"] - 1) +
                     task_metrics.get("progress_score", 0)) / stats["total"]
                )
                stats["avg_confidence_score"] = (
                    (stats["avg_confidence_score"] * (stats["total"] - 1) +
                     task_metrics.get("confidence_score", 0)) / stats["total"]
                )

        metrics["operator_stats"] = operator_stats

        # メタ知識の更新
        if self.meta_learner:
            self.current_context["meta_knowledge"] = {
                "generation_strategies": self.meta_learner.generation_strategies,
                "evolution_patterns": self.meta_learner.evolution_patterns,
                "context_dependencies": self.meta_learner.meta_knowledge.get("context_dependencies", {}),
                "successful_patterns": self.meta_learner.meta_knowledge.get("successful_patterns", []),
                "failed_patterns": self.meta_learner.meta_knowledge.get("failed_patterns", [])
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

    def _prepare_context_for_json(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """コンテキストをJSON直列化可能な形式に変換する。

        Args:
            context: 変換するコンテキスト

        Returns:
            JSON直列化可能なコンテキスト
        """
        serializable_context = {}
        for key, value in context.items():
            if isinstance(value, datetime):
                serializable_context[key] = value.isoformat()
            elif isinstance(value, (list, dict)):
                serializable_context[key] = self._prepare_nested_structure(value)
            else:
                serializable_context[key] = value
        return serializable_context

    def _prepare_nested_structure(self, data: Any) -> Any:
        """ネストされたデータ構造をJSON直列化可能な形式に変換する。

        Args:
            data: 変換するデータ

        Returns:
            JSON直列化可能なデータ
        """
        if isinstance(data, dict):
            return {
                key: self._prepare_nested_structure(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._prepare_nested_structure(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data
