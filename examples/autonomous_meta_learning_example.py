"""メタ学習を含む自律的なワークフロー実行のサンプル。"""
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from genesis_agi.core.unified_manager import UnifiedManager
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.operators.operator_generator import OperatorGenerator
from genesis_agi.models.operator import Base
from genesis_agi.utils.cache import Cache
from genesis_agi.core.meta_learning import MetaLearner


def setup_logging() -> None:
    """ロギングの設定を行う。"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # 標準出力へのハンドラ
            logging.FileHandler('genesis_agi.log')  # ファイルへのハンドラ
        ]
    )


def setup_environment() -> None:
    """環境設定を行う。"""
    load_dotenv()
    
    required_vars = ["OPENAI_API_KEY", "DATABASE_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(
            f"必要な環境変数が設定されていません: {', '.join(missing_vars)}\n"
            ".envファイルを作成し、必要な環境変数を設定してください。"
        )


def setup_database():
    """データベースの設定を行う。"""
    database_url = os.getenv("DATABASE_URL")
    if database_url is None:
        raise ValueError("DATABASE_URLが設定されていません")
    engine = create_engine(database_url)
    
    # テーブルの作成
    Base.metadata.create_all(engine)
    
    # セッションの作成
    Session = sessionmaker(bind=engine)
    return Session()


def main():
    """メイン実行関数。"""
    try:
        # ロギング設定
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Genesis AGIを開始")
        
        # 環境設定
        setup_environment()
        logger.info("環境設定完了")
        
        # APIキーの取得
        api_key = os.getenv("OPENAI_API_KEY")
        
        # データベース設定
        db_session = setup_database()
        logger.info("データベース設定完了")
        
        # 基本コンポーネントの初期化
        llm_client = LLMClient(api_key)
        cache = Cache()  # 必要に応じてキャッシュの設定を追加
        
        # オペレーターレジストリの初期化
        registry = OperatorRegistry(db_session)
        
        # オペレータージェネレーターの初期化
        generator = OperatorGenerator(llm_client, registry, cache)
        
        # メタラーナーの初期化
        meta_learner = MetaLearner(llm_client, cache)
        
        # UnifiedManagerの初期化
        manager = UnifiedManager(
            llm_client=llm_client,
            registry=registry,
            cache=cache,
            objective="データ分析と可視化タスクの実行",
            meta_learner=meta_learner,
            operator_generator=generator,
            max_iterations=5,
            iteration_delay=1.0
        )
        
        # サンプルタスクの実行
        task_description = "データセットの分析と可視化を行うオペレーターを生成し実行する"
        context = {
            "dataset_path": "data/sample_dataset.csv",
            "analysis_type": "exploratory",
            "visualization_type": "scatter"
        }
        
        # タスクの生成と実行
        task = manager.analyze_and_create_task(task_description)
        logger.info(f"タスク生成完了: {task.description}")
        
        # 自律的な実行を開始
        logger.info("自律的な実行を開始")
        manager.run()
        
        # 結果の分析
        analyze_results(manager)
        
        logger.info("処理が正常に完了しました")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}", exc_info=True)
        raise
    finally:
        # データベースセッションのクリーンアップ
        db_session.close()


def analyze_results(manager: UnifiedManager) -> None:
    """実行結果の分析を行う。

    Args:
        manager: UnifiedManagerインスタンス
    """
    # アクティブなオペレーターの一覧を取得
    active_operators = manager.registry.list_operators()
    
    # パフォーマンスメトリクスの分析
    for operator_info in active_operators:
        print(f"オペレーター: {operator_info['name']}")
        print(f"説明: {operator_info['description']}")
        if operator_info['performance_metrics']:
            print("パフォーマンスメトリクス:")
            for metric, value in operator_info['performance_metrics'].items():
                print(f"  - {metric}: {value}")
        print("---")
    
    # 実行履歴の表示
    print("\n=== 実行履歴 ===")
    for record in manager.execution_history:
        print(f"\nタスク: {record.task.description}")
        if hasattr(record, 'result'):
            print(f"状態: {record.result.get('status', '不明')}")
            if 'data' in record.result:
                print(f"データ: {record.result['data']}")


if __name__ == "__main__":
    main() 