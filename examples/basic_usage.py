"""基本的な使用方法を示すサンプルスクリプト。"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.task_creation import TaskCreationOperator
from genesis_agi.operators.task_execution import TaskExecutionOperator
from genesis_agi.operators.task_prioritization import TaskPrioritizationOperator
from genesis_agi.task_manager import TaskManager
from genesis_agi.utils.cache import Cache

# 環境変数の読み込み
load_dotenv()

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    # OpenAI APIキーの取得
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    # キャッシュディレクトリの作成
    cache_dir = Path("./cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # キャッシュの初期化
    cache = Cache(
        backend="filesystem",
        cache_dir=cache_dir,
        max_size=1000
    )

    # LLMクライアントの初期化
    llm_client = LLMClient(
        api_key=api_key,
        model="gpt-3.5-turbo",
        cache=cache,
    )

    # タスクマネージャーの初期化
    task_manager = TaskManager(
        llm_client=llm_client,
        cache=cache,
        objective="Webアプリケーションの開発計画を立てる",
    )

    # オペレーターの設定
    task_manager.add_operator(TaskCreationOperator(llm_client))
    task_manager.add_operator(TaskExecutionOperator(llm_client))
    task_manager.add_operator(TaskPrioritizationOperator(llm_client))

    # タスクの実行
    try:
        logger.info("タスクの実行を開始します...")
        
        # 初期タスクの生成
        initial_task = task_manager.create_initial_task()
        logger.info(f"初期タスク: {initial_task}")

        # タスクの実行ループ
        for i in range(5):  # 5回のイテレーション
            logger.info(f"\nイテレーション {i+1}")
            
            # 次のタスクを取得
            current_task = task_manager.get_next_task()
            if not current_task:
                logger.info("実行するタスクがありません。")
                break

            logger.info(f"現在のタスク: {current_task}")

            # タスクの実行
            result = task_manager.execute_task(current_task)
            logger.info(f"実行結果: {result}")

            # 新しいタスクの生成
            new_tasks = task_manager.create_new_tasks(current_task, result)
            logger.info(f"生成された新しいタスク: {new_tasks}")

            # タスクの優先順位付け
            task_manager.prioritize_tasks()
            logger.info("タスクの優先順位を更新しました")

            # パフォーマンス分析
            performance = task_manager.analyze_performance()
            logger.info(f"パフォーマンス分析: {performance}")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
    finally:
        # クリーンアップ
        task_manager.cleanup()

if __name__ == "__main__":
    main()