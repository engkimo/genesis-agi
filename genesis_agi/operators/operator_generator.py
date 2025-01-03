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

    def generate_operator(
        self,
        task_description: str,
        context: Dict[str, Any],
        generation_strategy: Optional[Dict[str, Any]] = None
    ) -> Type[BaseOperator]:
        """タスクの説明からオペレーターを生成する。

        Args:
            task_description: タスクの説明
            context: 現在のコンテキスト
            generation_strategy: オペレーター生成戦略

        Returns:
            生成されたオペレータークラス
        """
        # LLMにオペレーターの仕様を生成させる
        operator_spec = self._generate_operator_spec(task_description, context, generation_strategy)
        
        # オペレーターコードの生成
        operator_code = self._generate_operator_code(operator_spec)
        
        # オペレーターの動的生成と検証
        operator_class = self._create_operator_class(operator_code, operator_spec["name"])
        
        # 生成履歴の保存
        self.operator_specs[operator_spec["name"]] = operator_spec
        
        return operator_class

    def _generate_operator_spec(
        self,
        task_description: str,
        context: Dict[str, Any],
        generation_strategy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """オペレーターの仕様を生成する。

        Args:
            task_description: タスクの説明
            context: 現在のコンテキスト
            generation_strategy: オペレーター生成戦略

        Returns:
            オペレーターの仕様
        """
        prompt = {
            "task": task_description,
            "context": context,
            "objective": context.get("objective", ""),
            "completed_tasks": context.get("completed_tasks", []),
            "current_state": context.get("current_state", {}),
            "generation_strategy": generation_strategy or {}
        }
        
        # LLMに仕様の生成を依頼
        response = self.llm_client.generate_operator_spec(prompt)
        
        return response

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

    def _create_operator_class(self, code: str, operator_name: str) -> Type[BaseOperator]:
        """オペレーターのコードからクラスを生成する。

        Args:
            code: Pythonコード
            operator_name: オペレーター名

        Returns:
            生成されたオペレータークラス

        Raises:
            ValueError: オペレータークラスの生成に失敗した場合
        """
        try:
            # コードの実行環境を準備
            namespace = {"BaseOperator": BaseOperator}
            
            # コードの実行
            exec(code, namespace)
            
            # 生成されたクラスを取得
            for name, obj in namespace.items():
                if (
                    isinstance(obj, type) and 
                    issubclass(obj, BaseOperator) and 
                    obj != BaseOperator
                ):
                    return obj
            
            # クラスが見つからない場合は、デフォルトのクラスを生成
            class_def = f"""
class {operator_name}(BaseOperator):
    def execute(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        return {{
            "status": "success",
            "message": "Default implementation"
        }}
"""
            exec(class_def, namespace)
            return namespace[operator_name]

        except Exception as e:
            raise ValueError(f"Failed to create operator class: {str(e)}\nCode: {code}")

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

    def evolve_operator(
        self,
        operator_type: str,
        performance_data: Dict[str, Any],
        evolution_strategy: Optional[Dict[str, Any]] = None
    ) -> Type[BaseOperator]:
        """オペレーターを進化させる。

        Args:
            operator_type: オペレーターの種類
            performance_data: パフォーマンスデータ
            evolution_strategy: 進化戦略

        Returns:
            進化したオペレータークラス
        """
        original_spec = self.operator_specs[operator_type]
        
        # 進化の提案をLLMに依頼
        evolution_prompt = {
            "original_spec": original_spec,
            "performance_data": performance_data,
            "evolution_history": self.evolution_history,
            "evolution_strategy": evolution_strategy or {}
        }
        
        response = self.llm_client.propose_operator_evolution(evolution_prompt)
        
        # 新しい仕様でオペレーターを再生成
        evolved_spec = {**original_spec, **response["improvements"]}
        evolved_code = self._generate_operator_code(evolved_spec)
        evolved_operator = self._create_operator_class(evolved_code, f"Evolved{operator_type}")
        
        # 進化の履歴を記録
        self.evolution_history.append({
            "operator_name": operator_type,
            "original_spec": original_spec,
            "evolved_spec": evolved_spec,
            "performance_data": performance_data,
            "improvements": response["improvements"],
            "evolution_strategy": evolution_strategy
        })
        
        # 仕様を更新
        self.operator_specs[operator_type] = evolved_spec
        
        return evolved_operator 