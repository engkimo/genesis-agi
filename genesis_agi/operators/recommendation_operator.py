"""推薦システムオペレーター。"""
from typing import Any, Dict, List
import pandas as pd
from collections import Counter, defaultdict
from genesis_agi.operators.base_operator import BaseOperator


class RecommendationOperator(BaseOperator):
    """商品推薦を行うオペレーター。"""

    def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """商品推薦タスクを実行する。

        Args:
            task: 実行するタスク
            context: 実行コンテキスト

        Returns:
            実行結果
        """
        try:
            # サンプルデータの作成（実際のアプリケーションではデータベースから取得）
            data = {
                'customer_id': [1, 2, 3],
                'purchase_history': [
                    ['item1', 'item2'],
                    ['item1'],
                    ['item2', 'item3']
                ]
            }
            df = pd.DataFrame(data)

            # 推薦リストの生成
            recommendations = self._generate_recommendations(df)
            
            # 推薦結果の評価
            evaluation = self._evaluate_recommendations(recommendations, df)
            
            result = {
                "recommendations": recommendations,
                "evaluation": evaluation,
                "status": "success",
                "performance_metrics": {
                    "execution_success": True,
                    "recommendation_quality": evaluation.get("quality_score", 0.0)
                }
            }

            return result

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "performance_metrics": {
                    "execution_success": False,
                    "error_type": type(e).__name__
                }
            }

    def _generate_recommendations(self, df: pd.DataFrame) -> Dict[int, List[str]]:
        """購買履歴から推薦リストを生成する。

        Args:
            df: 購買履歴データ

        Returns:
            ユーザーごとの推薦リスト
        """
        recommendations = {}
        all_items = set()
        
        # 全商品のリストを作成
        for items in df['purchase_history']:
            all_items.update(items)
        
        # 各ユーザーに対して推薦を生成
        for _, row in df.iterrows():
            user_id = row['customer_id']
            user_items = set(row['purchase_history'])
            
            # まだ購入していない商品を推薦
            recommendations[user_id] = list(all_items - user_items)
            
        return recommendations

    def _evaluate_recommendations(self, recommendations: Dict[int, List[str]], df: pd.DataFrame) -> Dict[str, Any]:
        """推薦結果を評価する。

        Args:
            recommendations: 推薦リスト
            df: 購買履歴データ

        Returns:
            評価結果
        """
        total_recommendations = sum(len(items) for items in recommendations.values())
        unique_recommendations = len(set().union(*[set(items) for items in recommendations.values()]))
        
        evaluation = {
            "total_recommendations": total_recommendations,
            "unique_recommendations": unique_recommendations,
            "coverage": unique_recommendations / len(recommendations) if recommendations else 0,
            "quality_score": 0.8  # 仮の品質スコア
        }
        
        return evaluation

    @classmethod
    def get_required_context(cls) -> List[str]:
        """必要なコンテキストのキーを取得する。

        Returns:
            必要なコンテキストのキーのリスト
        """
        return [
            "objective",
            "task_history",
            "performance_metrics"
        ]

    def validate_result(self, result: Dict[str, Any]) -> bool:
        """実行結果を検証する。

        Args:
            result: 検証する実行結果

        Returns:
            検証結果（True: 有効、False: 無効）
        """
        required_keys = ["status", "recommendations", "evaluation"]
        return all(key in result for key in required_keys) 