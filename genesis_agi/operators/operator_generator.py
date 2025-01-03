"""オペレーターの動的生成と進化を管理するモジュール。"""
from typing import Dict, Any, List, Type, Optional
import inspect
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.base_operator import BaseOperator
from genesis_agi.operators.operator_registry import OperatorRegistry


class OperatorGenerator:
    """オペレーターの動的生成と進化を管理するクラス。"""

    def __init__(self, llm_client: LLMClient, registry: OperatorRegistry):
        """初期化。

        Args:
            llm_client: LLMクライアント
            registry: オペレーターレジストリ
        """
        self.llm_client = llm_client
        self.registry = registry
        self.operator_specs: Dict[str, Dict[str, Any]] = {}
        self.evolution_history: List[Dict[str, Any]] = []

    def generate_operator(self, task_description: str, context: Dict[str, Any]) -> Type[BaseOperator]:
        """タスクの説明からオペレーターを生成する。

        Args:
            task_description: タスクの説明
            context: 現在のコンテキスト

        Returns:
            生成されたオペレータークラス
        """
        # LLMにオペレーターの仕様を生成させる
        operator_spec = self._generate_operator_spec(task_description, context)
        
        # オペレーターコードの生成
        operator_code = self._generate_operator_code(operator_spec)
        
        # オペレーターの動的生成と検証
        operator_class = self._create_operator_class(operator_code)
        
        # 生成履歴の保存
        self.operator_specs[operator_spec["name"]] = operator_spec
        
        return operator_class

    def _generate_operator_spec(self, task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """オペレーターの仕様を生成する。

        Args:
            task_description: タスクの説明
            context: 現在のコンテキスト

        Returns:
            オペレーターの仕様
        """
        prompt = {
            "task": task_description,
            "context": context,
            "objective": context.get("objective", ""),
            "completed_tasks": context.get("completed_tasks", []),
            "current_state": context.get("current_state", {})
        }
        
        # LLMに仕様の生成を依頼
        response = self.llm_client.generate_operator_spec(prompt)
        
        return {
            "name": response["operator_name"],
            "description": response["description"],
            "inputs": response["required_inputs"],
            "outputs": response["expected_outputs"],
            "logic": response["processing_logic"],
            "next_tasks": response["potential_next_tasks"]
        }

    def _generate_operator_code(self, spec: Dict[str, Any]) -> str:
        """オペレーターのコードを生成する。

        Args:
            spec: オペレーターの仕様

        Returns:
            生成されたPythonコード
        """
        prompt = {
            "spec": spec,
            "base_class": inspect.getsource(BaseOperator),
            "example_operators": self._get_example_operators()
        }
        
        # LLMにコードの生成を依頼
        response = self.llm_client.generate_operator_code(prompt)
        return response["code"]

    def _create_operator_class(self, code: str) -> Type[BaseOperator]:
        """オペレーターのコードからクラスを生成する。

        Args:
            code: Pythonコード

        Returns:
            生成されたオペレータークラス
        """
        # コードの実行環境を準備
        namespace = {"BaseOperator": BaseOperator}
        
        # コードの実行
        exec(code, namespace)
        
        # 生成されたクラスを取得
        operator_class = next(
            obj for name, obj in namespace.items()
            if isinstance(obj, type) and issubclass(obj, BaseOperator)
        )
        
        return operator_class

    def evolve_operator(self, operator_name: str, performance_data: Dict[str, Any]) -> Type[BaseOperator]:
        """オペレーターを進化させる。

        Args:
            operator_name: オペレーターの名前
            performance_data: パフォーマンスデータ

        Returns:
            進化したオペレータークラス
        """
        original_spec = self.operator_specs[operator_name]
        
        # 進化の提案をLLMに依頼
        evolution_prompt = {
            "original_spec": original_spec,
            "performance_data": performance_data,
            "evolution_history": self.evolution_history
        }
        
        response = self.llm_client.propose_operator_evolution(evolution_prompt)
        
        # 新しい仕様でオペレーターを再生成
        evolved_spec = {**original_spec, **response["improvements"]}
        evolved_code = self._generate_operator_code(evolved_spec)
        evolved_operator = self._create_operator_class(evolved_code)
        
        # 進化の履歴を記録
        self.evolution_history.append({
            "operator_name": operator_name,
            "original_spec": original_spec,
            "evolved_spec": evolved_spec,
            "performance_data": performance_data,
            "improvements": response["improvements"]
        })
        
        # 仕様を更新
        self.operator_specs[operator_name] = evolved_spec
        
        return evolved_operator

    def _get_example_operators(self) -> List[str]:
        """既存のオペレーターのコードを取得する。

        Returns:
            オペレーターのコードのリスト
        """
        example_codes = []
        for operator_class in self.registry._operators.values():
            example_codes.append(inspect.getsource(operator_class))
        return example_codes

    def analyze_operator_chain(self, execution_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """オペレーターチェーンの分析を行う。

        Args:
            execution_history: 実行履歴

        Returns:
            分析結果
        """
        prompt = {
            "execution_history": execution_history,
            "operator_specs": self.operator_specs,
            "evolution_history": self.evolution_history
        }
        
        # LLMにチェーンの分析を依頼
        response = self.llm_client.analyze_operator_chain(prompt)
        
        return {
            "efficiency": response["efficiency_score"],
            "bottlenecks": response["bottlenecks"],
            "improvement_suggestions": response["suggestions"],
            "optimal_chain": response["optimal_chain"]
        } 