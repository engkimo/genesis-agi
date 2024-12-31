"""基本的な使用方法を示すサンプルスクリプト。"""
import json
import logging
import os
from datetime import datetime
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

def setup_logging():
    """ログの設定を行う。"""
    # ログディレクトリの作成
    log_dir = Path("./logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # ログファイル名の設定（タイムスタンプ付き）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"genesis_agi_{timestamp}.log"

    # ログハンドラの設定
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # ルートロガーの設定
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

    return log_file

def save_artifacts(task_manager, output_dir: Path):
    """アーティファクトを保存する。

    Args:
        task_manager: タスクマネージャー
        output_dir: 出力ディレクトリ
    """
    # 出力ディレクトリの作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # タスク履歴の保存
    task_history_file = output_dir / "task_history.json"
    with open(task_history_file, "w", encoding="utf-8") as f:
        json.dump(task_manager.task_history, f, ensure_ascii=False, indent=2)

    # 現在のタスクの保存
    current_tasks_file = output_dir / "current_tasks.json"
    with open(current_tasks_file, "w", encoding="utf-8") as f:
        json.dump(
            [task.dict() for task in task_manager.current_tasks],
            f,
            ensure_ascii=False,
            indent=2,
        )

    # パフォーマンス指標の保存
    metrics_file = output_dir / "performance_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(task_manager.performance_metrics, f, ensure_ascii=False, indent=2)

def main():
    # ログの設定
    log_file = setup_logging()
    logger.info(f"ログファイル: {log_file}")

    # アーティファクトディレクトリの設定
    artifacts_dir = Path("./artifacts")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = artifacts_dir / timestamp
    logger.info(f"アーティファクトディレクトリ: {output_dir}")

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

        # アーティファクトの保存
        save_artifacts(task_manager, output_dir)
        logger.info(f"アーティファクトを保存しました: {output_dir}")

    except Exception as e:
        logger.error(f"エラーが発生しました: {e}", exc_info=True)
    finally:
        # クリーンアップ
        task_manager.cleanup()

if __name__ == "__main__":
    main()