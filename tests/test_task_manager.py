"""Test cases for task management system."""
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from genesis_agi.operators import (
    TaskCreationOperator,
    TaskExecutionOperator,
    TaskPrioritizationOperator,
)
from genesis_agi.task_manager import Task, TaskManager


@pytest.fixture
def mock_openai():
    """OpenAI APIのモックを作成する。"""
    with patch("openai.ChatCompletion.create") as mock:
        mock.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content="Generated task description"
                    )
                )
            ]
        )
        yield mock


@pytest.fixture
def task_manager(mock_openai):
    """テスト用のTaskManagerインスタンスを作成する。"""
    return TaskManager(
        openai_api_key="dummy_key",
        model_name="gpt-3.5-turbo",
    )


class TestTaskManager:
    """TaskManagerのテスト。"""

    def test_task_creation(self, task_manager: TaskManager) -> None:
        """タスク作成のテスト。"""
        initial_task = Task(
            id="task-1",
            name="Initial task",
            description="Test initial task",
            priority=1,
        )

        # タスクの生成
        new_tasks = task_manager.create_tasks(initial_task)
        assert len(new_tasks) > 0
        for task in new_tasks:
            assert isinstance(task, Task)
            assert task.id is not None
            assert task.name is not None
            assert task.description is not None
            assert task.priority is not None

    def test_task_execution(self, task_manager: TaskManager) -> None:
        """タスク実行のテスト。"""
        task = Task(
            id="task-1",
            name="Test task",
            description="Execute this test task",
            priority=1,
        )

        # タスクの実行
        result = task_manager.execute_task(task)
        assert result is not None
        assert isinstance(result, dict)
        assert "status" in result
        assert "output" in result

    def test_task_prioritization(self, task_manager: TaskManager) -> None:
        """タスク優先順位付けのテスト。"""
        tasks = [
            Task(
                id=f"task-{i}",
                name=f"Task {i}",
                description=f"Test task {i}",
                priority=1,
            )
            for i in range(3)
        ]

        # タスクの優先順位付け
        prioritized_tasks = task_manager.prioritize_tasks(tasks)
        assert len(prioritized_tasks) == len(tasks)
        
        # 優先順位が適切に設定されていることを確認
        priorities = [task.priority for task in prioritized_tasks]
        assert len(set(priorities)) == len(priorities)  # 優先順位が重複していないことを確認

    def test_task_lifecycle(self, task_manager: TaskManager) -> None:
        """タスクのライフサイクル全体のテスト。"""
        # 初期タスクの作成
        initial_task = Task(
            id="initial-task",
            name="Initial task",
            description="Start the task chain",
            priority=1,
        )

        # タスクの生成
        new_tasks = task_manager.create_tasks(initial_task)
        assert len(new_tasks) > 0

        # タスクの優先順位付け
        prioritized_tasks = task_manager.prioritize_tasks(new_tasks)
        assert len(prioritized_tasks) == len(new_tasks)

        # 最優先タスクの実行
        highest_priority_task = prioritized_tasks[0]
        result = task_manager.execute_task(highest_priority_task)
        assert result is not None

    def test_performance_analysis(self, task_manager: TaskManager) -> None:
        """パフォーマンス分析のテスト。"""
        task = Task(
            id="task-1",
            name="Test task",
            description="Test performance analysis",
            priority=1,
        )

        # タスクの実行と分析
        result = task_manager.execute_task(task)
        analysis = task_manager.analyze_performance(task, result)
        
        assert analysis is not None
        assert "metrics" in analysis
        assert "suggestions" in analysis

    def test_context_management(self, task_manager: TaskManager) -> None:
        """コンテキスト管理のテスト。"""
        # コンテキストの追加
        task_manager.add_to_context("test_key", "test_value")
        assert task_manager.get_context("test_key") == "test_value"

        # コンテキストを使用したタスク生成
        task = Task(
            id="context-task",
            name="Context test",
            description="Test with context",
            priority=1,
        )
        new_tasks = task_manager.create_tasks(task)
        assert len(new_tasks) > 0

    def test_error_handling(self, task_manager: TaskManager) -> None:
        """エラーハンドリングのテスト。"""
        # 無効なタスク
        invalid_task = Task(
            id="invalid-task",
            name="",  # 無効な名前
            description="",  # 無効な説明
            priority=-1,  # 無効な優先順位
        )

        # タスク生成時のエラーハンドリング
        with pytest.raises(ValueError):
            task_manager.create_tasks(invalid_task)

        # タスク実行時のエラーハンドリング
        with pytest.raises(ValueError):
            task_manager.execute_task(invalid_task)

    def test_improvement_suggestions(self, task_manager: TaskManager) -> None:
        """改善提案機能のテスト。"""
        task = Task(
            id="task-1",
            name="Test task",
            description="Test improvement suggestions",
            priority=1,
        )

        # タスクの実行と改善提案の生成
        result = task_manager.execute_task(task)
        suggestions = task_manager.generate_improvement_suggestions(task, result)
        
        assert suggestions is not None
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0