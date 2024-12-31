"""分散キャッシュを使用したサンプルスクリプト。"""
import logging
from genesis_agi.task_manager import TaskManager
from genesis_agi.operators.task_creation import TaskCreationOperator
from genesis_agi.operators.task_execution import TaskExecutionOperator
from genesis_agi.operators.task_prioritization import TaskPrioritizationOperator
from genesis_agi.utils.cache import Cache

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    # Redisキャッシュの初期化
    cache = Cache(
        backend="redis",
        redis_config={
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "prefix": "genesis:",
            "decode_responses": True,
        }
    )

    # タスクマネージャーの初期化
    task_manager = TaskManager(
        openai_api_key="your-api-key-here",
        cache=cache,
        objective="機械学習モデルの性能改善計画を立てる",
    )

    # オペレーターの設定
    task_manager.add_operator(TaskCreationOperator())
    task_manager.add_operator(TaskExecutionOperator())
    task_manager.add_operator(TaskPrioritizationOperator())

    # タスクの実行
    try:
        logger.info("分散環境でのタスク実行を開始します...")
        
        # 初期タスクの生成
        initial_task = task_manager.create_initial_task()
        logger.info(f"初期タスク: {initial_task}")

        # タスクの実行ループ
        for i in range(5):  # 5回のイテレーション
            logger.info(f"\nイテレーション {i+1}")
            
            # キャッシュからタスク情報を取得
            current_task = task_manager.get_next_task()
            if not current_task:
                logger.info("実行するタスクがありません。")
                break

            logger.info(f"現在のタスク: {current_task}")

            # タスクの実行とキャッシュの更新
            result = task_manager.execute_task(current_task)
            logger.info(f"実行結果: {result}")

            # 新しいタスクの生成とキャッシュへの保存
            new_tasks = task_manager.create_new_tasks(current_task, result)
            logger.info(f"生成された新しいタスク: {new_tasks}")

            # タスクの優先順位付けとキャッシュの更新
            task_manager.prioritize_tasks()
            logger.info("タスクの優先順位を更新しました")

            # パフォーマンス分析の結果をキャッシュに保存
            performance = task_manager.analyze_performance()
            logger.info(f"パフォーマンス分析: {performance}")

            # キャッシュの統計情報を表示
            cache_stats = cache.get_stats()
            logger.info(f"キャッシュ統計: {cache_stats}")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
    finally:
        # クリーンアップ
        task_manager.cleanup()

if __name__ == "__main__":
    main() 