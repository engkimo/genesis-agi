"""データ分析オペレーター。"""
from typing import Any, Dict, List
import pandas as pd
from collections import Counter
from genesis_agi.operators.base_operator import BaseOperator


class DataAnalysisOperator(BaseOperator):
    """データ分析を行うオペレーター。"""

    def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """データ分析タスクを実行する。

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

            # 購買パターンの分析
            patterns = self._analyze_purchase_patterns(df)
            
            # 分析結果の準備
            analysis_result = {
                "purchase_patterns": patterns,
                "customer_segments": self._segment_customers(df),
                "item_popularity": self._calculate_item_popularity(df),
                "status": "success",
                "performance_metrics": {
                    "execution_success": True,
                    "analysis_quality": self._evaluate_analysis_quality(patterns)
                }
            }

            return analysis_result

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "performance_metrics": {
                    "execution_success": False,
                    "error_type": type(e).__name__
                }
            }

    def _analyze_purchase_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """購買パターンを分析する。

        Args:
            df: 購買履歴データ

        Returns:
            分析結果
        """
        # 全ての購買履歴を結合
        all_purchases = [item for history in df['purchase_history'] for item in history]
        
        # アイテムの出現頻度を計算
        item_frequency = Counter(all_purchases)
        
        # 共起関係の分析
        co_occurrence = {}
        for history in df['purchase_history']:
            if len(history) > 1:
                for i in range(len(history)):
                    for j in range(i + 1, len(history)):
                        pair = tuple(sorted([history[i], history[j]]))
                        co_occurrence[pair] = co_occurrence.get(pair, 0) + 1
        
        return {
            "item_frequency": dict(item_frequency),
            "co_occurrence": dict(co_occurrence)
        }

    def _segment_customers(self, df: pd.DataFrame) -> Dict[str, List[int]]:
        """顧客をセグメント化する。

        Args:
            df: 購買履歴データ

        Returns:
            セグメント化結果
        """
        segments = {
            "high_activity": [],
            "medium_activity": [],
            "low_activity": []
        }
        
        for _, row in df.iterrows():
            purchase_count = len(row['purchase_history'])
            customer_id = row['customer_id']
            
            if purchase_count >= 3:
                segments["high_activity"].append(customer_id)
            elif purchase_count == 2:
                segments["medium_activity"].append(customer_id)
            else:
                segments["low_activity"].append(customer_id)
        
        return segments

    def _calculate_item_popularity(self, df: pd.DataFrame) -> Dict[str, float]:
        """商品の人気度を計算する。

        Args:
            df: 購買履歴データ

        Returns:
            商品ごとの人気度
        """
        all_purchases = [item for history in df['purchase_history'] for item in history]
        total_purchases = len(all_purchases)
        
        popularity = Counter(all_purchases)
        return {item: count/total_purchases for item, count in popularity.items()}

    def _evaluate_analysis_quality(self, patterns: Dict[str, Any]) -> float:
        """分析の品質を評価する。

        Args:
            patterns: 分析結果

        Returns:
            品質スコア
        """
        # 分析の品質を評価する基準
        criteria = {
            "has_item_frequency": bool(patterns.get("item_frequency")),
            "has_co_occurrence": bool(patterns.get("co_occurrence")),
            "item_frequency_count": len(patterns.get("item_frequency", {})),
            "co_occurrence_count": len(patterns.get("co_occurrence", {}))
        }
        
        # 基準ごとのスコアを計算
        score = 0.0
        if criteria["has_item_frequency"]:
            score += 0.3
        if criteria["has_co_occurrence"]:
            score += 0.3
        if criteria["item_frequency_count"] > 0:
            score += 0.2
        if criteria["co_occurrence_count"] > 0:
            score += 0.2
            
        return score

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
        required_keys = ["status", "purchase_patterns", "customer_segments", "item_popularity"]
        return all(key in result for key in required_keys) 