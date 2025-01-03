"""メタ学習を含む自律的なワークフロー実行のサンプル。"""
import os
import logging
from dotenv import load_dotenv
from genesis_agi.core.unified_manager import UnifiedManager
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.utils.cache import Cache


def setup_logging() -> None:
    """ロギングの設定を行う。"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # 標準出力へのハンドラ
            logging.FileHandler('genesis_agi.log')  # ファイルへのハンドラ
        ]
    )


def setup_environment() -> None:
    """環境設定を行う。"""
    load_dotenv()
    
    required_vars = ["OPENAI_API_KEY"]  # MODEL_NAMEはオプショナルに
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise EnvironmentError(
            f"必要な環境変数が設定されていません: {', '.join(missing_vars)}\n"
            ".envファイルを作成し、必要な環境変数を設定してください。"
        )


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
        
        # APIキーの取得（必須）
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません")
        
        # モデルの選択（オプショナル）
        model = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
        
        # LLMクライアントの初期化
        llm_client = LLMClient(
            api_key=api_key,
            model=model
        )
        logger.info(f"LLMクライアントを初期化: モデル={model}")
        
        # オペレーターレジストリの初期化
        registry = OperatorRegistry()
        logger.info("オペレーターレジストリを初期化")
        
        # キャッシュの初期化（オプショナル）
        cache = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            cache = Cache(
                backend="redis",
                redis_config={
                    "host": redis_url.split("://")[-1].split(":")[0],
                    "port": int(redis_url.split(":")[-1].split("/")[0]),
                    "db": int(redis_url.split("/")[-1]) if "/" in redis_url else 0
                }
            )
            logger.info("Redisキャッシュを初期化")
        else:
            logger.info("キャッシュなしで実行")
        
        # UnifiedManagerの初期化
        objective = "顧客データを分析し、購買パターンを特定して、パーソナライズされた推薦を生成する"
        manager = UnifiedManager(
            llm_client=llm_client,
            registry=registry,
            cache=cache,
            objective=objective
        )
        logger.info(f"UnifiedManagerを初期化: 目標「{objective}」")
        
        print("=== 実行開始 ===")
        print(f"目的: {manager.objective}")
        print("初期タスクを生成中...")
        logger.info("初期タスク生成を開始")
        
        # 初期タスクの作成（以降は自動的にタスクが生成・進化する）
        task = manager.analyze_and_create_task(
            "顧客の購買履歴データを収集し、基本的な分析を行う"
        )
        logger.info(f"初期タスク生成完了: {task.description}")
        print(f"初期タスク生成完了: {task.description}")
        
        # 自律的な実行を開始
        print("\n自律的な実行を開始します...")
        logger.info("自律的な実行を開始")
        manager.run()
        logger.info("自律的な実行が完了")
        
        # 実行結果とメタ学習の状態を確認
        print("\n=== 実行結果 ===")
        for record in manager.execution_history:
            print(f"\nタスク: {record.task.description}")
            print(f"状態: {record.result.get('status')}")
            if record.result.get('data'):
                print(f"データ: {record.result['data']}")
            
            # メタデータの表示
            if record.meta_data:
                print("\nメタ情報:")
                if "generation_strategy" in record.meta_data:
                    print(f"生成戦略: {record.meta_data['generation_strategy']}")
                if "performance_metrics" in record.meta_data:
                    print(f"パフォーマンス指標: {record.meta_data['performance_metrics']}")
        
        print("\n=== パフォーマンス指標 ===")
        print(manager.current_context["performance_metrics"])
        
        print("\n=== メタ知識 ===")
        meta_knowledge = manager.current_context["meta_knowledge"]
        
        print("\n生成戦略:")
        for strategy_name, strategy in meta_knowledge["generation_strategies"].items():
            print(f"\n戦略名: {strategy_name}")
            if hasattr(strategy, 'success_rate'):
                print(f"成功率: {strategy.success_rate:.2f}")
            if hasattr(strategy, 'avg_performance'):
                print(f"平均パフォーマンス: {strategy.avg_performance:.2f}")
            if hasattr(strategy, 'usage_count'):
                print(f"使用回数: {strategy.usage_count}")
        
        print("\n進化パターン:")
        for pattern in meta_knowledge["evolution_patterns"]:
            if hasattr(pattern, 'pattern_name'):
                print(f"\nパターン名: {pattern.pattern_name}")
            if hasattr(pattern, 'performance_improvement'):
                print(f"パフォーマンス改善: {pattern.performance_improvement:.2f}")
        
        print("\nコンテキスト依存関係:")
        for factor, dependencies in meta_knowledge["context_dependencies"].items():
            print(f"\n要因: {factor}")
            for dep in dependencies:
                if isinstance(dep, dict):
                    print(f"- パターン: {dep.get('pattern')}, 影響度: {dep.get('impact', 0.0):.2f}")
                else:
                    print(f"- 依存関係: {dep}")
        
        # 詳細な分析の実行
        analyze_results(manager)

    except Exception as e:
        print(f"\nエラーが発生しました: {str(e)}")
        raise


def analyze_results(manager: UnifiedManager) -> None:
    """実行結果の詳細な分析を行う。

    Args:
        manager: 実行を管理したUnifiedManagerインスタンス
    """
    print("\n=== 詳細分析 ===")
    
    try:
        # オペレーター生成の分析
        operator_stats = {}
        for record in manager.execution_history:
            operator_type = record.operator or "unknown"
            if operator_type not in operator_stats:
                operator_stats[operator_type] = {
                    "count": 0,
                    "success_count": 0,
                    "total_time": 0,
                    "generated_tasks": 0
                }
            
            stats = operator_stats[operator_type]
            stats["count"] += 1
            if record.result.get("status") == "success":
                stats["success_count"] += 1
            stats["total_time"] += record.result.get("execution_time", 0)
            stats["generated_tasks"] += len(record.result.get("generated_tasks", []))
        
        print("\n=== オペレーター統計 ===")
        for operator_type, stats in operator_stats.items():
            print(f"\nオペレーター: {operator_type}")
            print(f"実行回数: {stats['count']}")
            success_rate = stats['success_count'] / stats['count'] if stats['count'] > 0 else 0
            print(f"成功率: {success_rate:.2f}")
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            print(f"平均実行時間: {avg_time:.2f}秒")
            print(f"生成タスク数: {stats['generated_tasks']}")
        
        # 進化パターンの分析
        evolution_stats = {
            "total_evolutions": len(manager.meta_learner.evolution_patterns if manager.meta_learner else []),
            "successful_evolutions": len(manager.meta_learner.meta_knowledge["successful_patterns"] if manager.meta_learner else []),
            "failed_evolutions": len(manager.meta_learner.meta_knowledge["failed_patterns"] if manager.meta_learner else []),
            "avg_improvement": (
                sum(pattern.performance_improvement for pattern in manager.meta_learner.evolution_patterns)
                / len(manager.meta_learner.evolution_patterns)
                if manager.meta_learner and manager.meta_learner.evolution_patterns
                else 0
            )
        }
        
        print("\n=== 進化統計 ===")
        print(f"総進化回数: {evolution_stats['total_evolutions']}")
        print(f"成功した進化: {evolution_stats['successful_evolutions']}")
        print(f"失敗した進化: {evolution_stats['failed_evolutions']}")
        print(f"平均パフォーマンス改善: {evolution_stats['avg_improvement']:.2f}")

    except Exception as e:
        print(f"分析中にエラーが発生しました: {str(e)}")
        raise


if __name__ == "__main__":
    main() 