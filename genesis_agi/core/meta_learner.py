"""メタ学習システム。"""
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass, asdict
import numpy as np
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.base_operator import BaseOperator


@dataclass
class GenerationStrategy:
    """オペレーター生成戦略。"""
    strategy_name: str
    parameters: Dict[str, Any]
    success_rate: float
    avg_performance: float
    usage_count: int

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する。

        Returns:
            辞書形式のデータ
        """
        return {
            "strategy_name": self.strategy_name,
            "parameters": self.parameters,
            "success_rate": self.success_rate,
            "avg_performance": self.avg_performance,
            "usage_count": self.usage_count
        }


@dataclass
class EvolutionPattern:
    """進化パターン。"""
    pattern_name: str
    initial_state: Dict[str, Any]
    evolved_state: Dict[str, Any]
    performance_improvement: float
    context: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換する。

        Returns:
            辞書形式のデータ
        """
        return {
            "pattern_name": self.pattern_name,
            "initial_state": self.initial_state,
            "evolved_state": self.evolved_state,
            "performance_improvement": self.performance_improvement,
            "context": self.context
        }


class MetaLearner:
    """メタ学習を行うクラス。"""

    def __init__(self, llm_client: LLMClient):
        """初期化。

        Args:
            llm_client: LLMクライアント
        """
        self.llm_client = llm_client
        self.generation_strategies: Dict[str, GenerationStrategy] = {}
        self.evolution_patterns: List[EvolutionPattern] = []
        self.meta_knowledge: Dict[str, Any] = {
            "successful_patterns": [],
            "failed_patterns": [],
            "context_dependencies": {},
            "performance_correlations": {}
        }

    def optimize_generation_strategy(
        self,
        task_description: str,
        context: Dict[str, Any],
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """オペレーター生成戦略を最適化する。

        Args:
            task_description: タスクの説明
            context: 現在のコンテキスト
            previous_results: 過去の生成結果

        Returns:
            最適化された生成戦略
        """
        # 現在のコンテキストに最も適した戦略を選択
        best_strategies = self._select_best_strategies(context)
        
        # 過去の結果から学習
        if previous_results:
            self._update_strategy_performance(previous_results)
        
        # メタ知識をJSONシリアライズ可能な形式に変換
        prepared_meta_knowledge = {
            "successful_patterns": [
                pattern.to_dict() if isinstance(pattern, EvolutionPattern) else pattern
                for pattern in self.meta_knowledge["successful_patterns"]
            ],
            "failed_patterns": [
                pattern.to_dict() if isinstance(pattern, EvolutionPattern) else pattern
                for pattern in self.meta_knowledge["failed_patterns"]
            ],
            "context_dependencies": self.meta_knowledge["context_dependencies"],
            "performance_correlations": self.meta_knowledge["performance_correlations"]
        }
        
        # LLMを使用して戦略を最適化
        optimization_prompt = {
            "task": task_description,
            "context": self._prepare_context_for_json(context),
            "best_strategies": best_strategies,
            "meta_knowledge": prepared_meta_knowledge
        }
        
        response = self.llm_client.optimize_generation_strategy(optimization_prompt)
        
        # 新しい戦略を登録
        new_strategy = GenerationStrategy(
            strategy_name=response["strategy_name"],
            parameters=response["parameters"],
            success_rate=0.0,
            avg_performance=0.0,
            usage_count=0
        )
        self.generation_strategies[new_strategy.strategy_name] = new_strategy
        
        return response["parameters"]

    def learn_evolution_patterns(
        self,
        original_operator: Type[BaseOperator],
        evolved_operator: Type[BaseOperator],
        performance_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> None:
        """進化パターンを学習する。

        Args:
            original_operator: 元のオペレーター
            evolved_operator: 進化後のオペレーター
            performance_data: パフォーマンスデータ
            context: 進化時のコンテキスト
        """
        # 進化パターンの抽出
        pattern = EvolutionPattern(
            pattern_name=f"evolution_{len(self.evolution_patterns)}",
            initial_state=self._extract_operator_state(original_operator),
            evolved_state=self._extract_operator_state(evolved_operator),
            performance_improvement=self._calculate_improvement(performance_data),
            context=context
        )
        
        # パターンの分析
        analysis = self._analyze_evolution_pattern(pattern)
        
        # メタ知識の更新
        if analysis["is_successful"]:
            self.meta_knowledge["successful_patterns"].append(pattern)
            self._update_context_dependencies(pattern, analysis)
        else:
            self.meta_knowledge["failed_patterns"].append(pattern)
        
        self.evolution_patterns.append(pattern)

    def suggest_evolution_strategy(
        self,
        operator: Type[BaseOperator],
        context: Dict[str, Any],
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """進化戦略を提案する。

        Args:
            operator: 対象のオペレーター
            context: 現在のコンテキスト
            performance_data: パフォーマンスデータ

        Returns:
            提案された進化戦略
        """
        # 類似のパターンを検索
        similar_patterns = self._find_similar_patterns(operator, context)
        
        # パターンの成功率を分析
        pattern_analysis = self._analyze_pattern_success_rates(similar_patterns)
        
        # LLMを使用して最適な進化戦略を生成
        strategy_prompt = {
            "operator": self._extract_operator_state(operator),
            "context": context,
            "performance_data": performance_data,
            "similar_patterns": similar_patterns,
            "pattern_analysis": pattern_analysis,
            "meta_knowledge": self.meta_knowledge
        }
        
        response = self.llm_client.generate_evolution_strategy(strategy_prompt)
        return response["strategy"]

    def _select_best_strategies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """コンテキストに最も適した戦略を選択する。

        Args:
            context: 現在のコンテキスト

        Returns:
            選択された戦略のリスト（辞書形式）
        """
        scored_strategies = []
        for strategy in self.generation_strategies.values():
            score = self._calculate_strategy_score(strategy, context)
            scored_strategies.append((score, strategy))
        
        scored_strategies.sort(reverse=True, key=lambda x: x[0])
        return [strategy.to_dict() for _, strategy in scored_strategies[:3]]

    def _calculate_strategy_score(self, strategy: GenerationStrategy, context: Dict[str, Any]) -> float:
        """戦略のスコアを計算する。

        Args:
            strategy: 評価する戦略
            context: 現在のコンテキスト

        Returns:
            スコア
        """
        # 基本スコア（成功率と平均パフォーマンス）
        base_score = (strategy.success_rate * 0.6 + strategy.avg_performance * 0.4)
        
        # コンテキスト類似性
        context_similarity = self._calculate_context_similarity(
            strategy.parameters.get("target_context", {}),
            context
        )
        
        # 使用頻度による調整（探索と活用のバランス）
        exploration_factor = 1.0 / (1.0 + np.log1p(strategy.usage_count))
        
        return base_score * context_similarity * exploration_factor

    def _calculate_context_similarity(self, context1: Dict[str, Any], context2: Dict[str, Any]) -> float:
        """コンテキスト間の類似度を計算する。

        Args:
            context1: 比較するコンテキスト1
            context2: 比較するコンテキスト2

        Returns:
            類似度スコア
        """
        # LLMを使用してコンテキストの意味的類似性を計算
        similarity_prompt = {
            "context1": self._prepare_context_for_json(context1),
            "context2": self._prepare_context_for_json(context2)
        }
        response = self.llm_client.calculate_context_similarity(similarity_prompt)
        return float(response["similarity_score"])

    def _extract_operator_state(self, operator: Type[BaseOperator]) -> Dict[str, Any]:
        """オペレーターの状態を抽出する。

        Args:
            operator: 対象のオペレーター

        Returns:
            オペレーターの状態
        """
        return {
            "name": operator.__name__,
            "attributes": {
                name: value for name, value in vars(operator).items()
                if not name.startswith("_")
            },
            "methods": {
                name: str(method) for name, method in operator.__dict__.items()
                if callable(method) and not name.startswith("_")
            }
        }

    def _analyze_evolution_pattern(self, pattern: EvolutionPattern) -> Dict[str, Any]:
        """進化パターンを分析する。

        Args:
            pattern: 分析する進化パターン

        Returns:
            分析結果
        """
        # LLMを使用してパターンを分析
        analysis_prompt = {
            "pattern": {
                "initial_state": pattern.initial_state,
                "evolved_state": pattern.evolved_state,
                "performance_improvement": pattern.performance_improvement,
                "context": pattern.context
            },
            "meta_knowledge": self.meta_knowledge
        }
        
        return self.llm_client.analyze_evolution_pattern(analysis_prompt)

    def _update_context_dependencies(self, pattern: EvolutionPattern, analysis: Dict[str, Any]) -> None:
        """コンテキスト依存関係を更新する。

        Args:
            pattern: 進化パターン
            analysis: パターンの分析結果
        """
        for factor in analysis.get("context_factors", []):
            if factor not in self.meta_knowledge["context_dependencies"]:
                self.meta_knowledge["context_dependencies"][factor] = []
            
            self.meta_knowledge["context_dependencies"][factor].append({
                "pattern": pattern.pattern_name,
                "impact": analysis["factor_impacts"][factor]
            })

    def _find_similar_patterns(
        self,
        operator: Type[BaseOperator],
        context: Dict[str, Any]
    ) -> List[EvolutionPattern]:
        """類似の進化パターンを検索する。

        Args:
            operator: 対象のオペレーター
            context: 現在のコンテキスト

        Returns:
            類似パターンのリスト
        """
        operator_state = self._extract_operator_state(operator)
        
        similar_patterns = []
        for pattern in self.evolution_patterns:
            similarity_score = self._calculate_pattern_similarity(
                operator_state,
                pattern.initial_state,
                context,
                pattern.context
            )
            if similarity_score > 0.7:  # 類似度閾値
                similar_patterns.append(pattern)
        
        return similar_patterns

    def _calculate_pattern_similarity(
        self,
        state1: Dict[str, Any],
        state2: Dict[str, Any],
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """パターン間の類似度を計算する。

        Args:
            state1: 比較する状態1
            state2: 比較する状態2
            context1: 比較するコンテキスト1
            context2: 比較するコンテキスト2

        Returns:
            類似度スコア
        """
        # LLMを使用してパターンの類似性を計算
        similarity_prompt = {
            "state1": state1,
            "state2": state2,
            "context1": context1,
            "context2": context2
        }
        response = self.llm_client.calculate_pattern_similarity(similarity_prompt)
        return float(response["similarity_score"]) 

    def _prepare_context_for_json(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """JSONシリアライズ用にコンテキストを準備する。

        Args:
            context: 準備するコンテキスト

        Returns:
            JSONシリアライズ可能なコンテキスト
        """
        prepared_context = {}
        for key, value in context.items():
            if isinstance(value, (GenerationStrategy, EvolutionPattern)):
                prepared_context[key] = value.to_dict()
            elif isinstance(value, dict):
                prepared_context[key] = self._prepare_context_for_json(value)
            elif isinstance(value, list):
                prepared_context[key] = [
                    item.to_dict() if isinstance(item, (GenerationStrategy, EvolutionPattern)) else item
                    for item in value
                ]
            else:
                prepared_context[key] = value
        return prepared_context 