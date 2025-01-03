"""LLMクライアント。"""
import json
from typing import Any, Dict, List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from genesis_agi.context.context_manager import ContextManager
from genesis_agi.operators import Task
from genesis_agi.utils.cache import Cache


class LLMClient:
    """LLMクライアント。"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        cache: Optional[Cache] = None,
        context_manager: Optional[ContextManager] = None,
    ):
        """初期化。

        Args:
            api_key: OpenAI APIキー
            model: 使用するモデル名
            cache: キャッシュ
            context_manager: コンテキストマネージャー
        """
        self.api_key = api_key
        self.model = model
        self.cache = cache
        self.context_manager = context_manager or ContextManager()
        self.client = OpenAI(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    def _call_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """OpenAI APIを呼び出す。

        Args:
            messages: メッセージリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数

        Returns:
            生成されたテキスト
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def parse_json_response(self, response: str) -> Any:
        """JSONレスポンスをパースする。

        Args:
            response: JSONレスポンス

        Returns:
            パースされたデータ

        Raises:
            ValueError: JSONのパースに失敗した場合
        """
        try:
            # レスポンスからコードブロックを抽出
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end]
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end != -1:
                    response = response[start:end]

            # 空白を削除
            response = response.strip()

            # JSONをパース
            return json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nResponse: {response}")

    def generate_improvement_suggestions(
        self,
        task: Task,
        task_history: List[Dict[str, Any]],
        performance_metrics: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """改善提案を生成する。

        Args:
            task: タスク
            task_history: タスク実行履歴
            performance_metrics: パフォーマンス指標

        Returns:
            改善提案のリスト
        """
        # キャッシュをチェック
        cache_key = f"improvement_suggestions:{task.id}"
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # プロンプトの構築
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムの改善を提案するアシスタントです。"
                    "タスクの実行履歴とパフォーマンス指標を分析し、"
                    "システムの改善提案を生成してください。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": task.dict(),
                        "task_history": task_history,
                        "performance_metrics": performance_metrics,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            },
        ]

        # 関連するコンテキストを追加
        context = self.context_manager.get_relevant_context(task.description)
        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"関連するコンテキスト情報:\n{json.dumps(context, ensure_ascii=False, indent=2)}",
                }
            )

        # 改善提案の生成
        response = self._call_openai(messages, temperature=0.7)
        suggestions = self.parse_json_response(response)

        # キャッシュに保存
        if self.cache:
            self.cache.set(cache_key, suggestions, ttl=3600)  # 1時間キャッシュ

        return suggestions

    def update_prompt_template(self, template_name: str, new_template: str) -> None:
        """プロンプトテンプレートを更新する。

        Args:
            template_name: テンプレート名
            new_template: 新しいテンプレート
        """
        self.context_manager.update_prompt_template(template_name, new_template)

    def update_parameters(self, parameter_name: str, new_value: Any) -> None:
        """パラメータを更新する。

        Args:
            parameter_name: パラメータ名
            new_value: 新しい値
        """
        if parameter_name == "temperature":
            if not isinstance(new_value, (int, float)) or not 0 <= new_value <= 1:
                raise ValueError("Temperature must be a float between 0 and 1")
        elif parameter_name == "max_tokens":
            if not isinstance(new_value, int) or new_value <= 0:
                raise ValueError("max_tokens must be a positive integer")

        self.context_manager.update_parameter(parameter_name, new_value)

    def update_strategy(self, strategy_name: str, new_strategy: Dict[str, Any]) -> None:
        """戦略を更新する。

        Args:
            strategy_name: 戦略名
            new_strategy: 新しい戦略
        """
        self.context_manager.update_strategy(strategy_name, new_strategy)

    def analyze_task(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """タスクを分析する。

        Args:
            prompt: タスク分析のためのプロンプト

        Returns:
            分析結果
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムのタスク分析の専門家です。"
                    "提供されたタスクの説明とコンテキストを分析し、"
                    "必要なオペレータータイプとパラメータを特定してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "required_operator_type": "必要なオペレーターの種類",\n'
                    '  "required_params": {\n'
                    '    "param1": "値1",\n'
                    '    "param2": "値2"\n'
                    "  },\n"
                    '  "task_analysis": {\n'
                    '    "complexity": "タスクの複雑さ（low/medium/high）",\n'
                    '    "dependencies": ["依存するタスクやリソース"],\n'
                    '    "expected_duration": "予想される実行時間（秒）"\n'
                    "  }\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.5)
        return self.parse_json_response(response)

    def optimize_generation_strategy(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """オペレーター生成戦略を最適化する。

        Args:
            prompt: 最適化のためのプロンプト

        Returns:
            最適化された生成戦略
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムのオペレーター生成戦略を最適化する専門家です。"
                    "タスクの説明、コンテキスト、これまでの戦略の成功率を分析し、"
                    "最適な生成戦略を提案してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "strategy_name": "戦略名",\n'
                    '  "parameters": {\n'
                    '    "data_collection": { ... },\n'
                    '    "analysis_methods": { ... },\n'
                    '    "optimization_targets": { ... }\n'
                    "  },\n"
                    '  "expected_outcomes": { ... }\n'
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.7)
        return self.parse_json_response(response)

    def generate_evolution_strategy(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """進化戦略を生成する。

        Args:
            prompt: 戦略生成のためのプロンプト

        Returns:
            生成された進化戦略
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムのオペレーター進化戦略を生成する専門家です。"
                    "オペレーターの現在の状態、パフォーマンスデータ、コンテキストを分析し、"
                    "最適な進化戦略を提案してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "strategy": {\n'
                    '    "evolution_type": "進化の種類",\n'
                    '    "modifications": [ ... ],\n'
                    '    "expected_improvements": { ... }\n'
                    "  }\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.7)
        return self.parse_json_response(response)

    def calculate_context_similarity(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """コンテキスト間の類似度を計算する。

        Args:
            prompt: 類似度計算のためのプロンプト

        Returns:
            類似度スコアを含む結果
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたは2つのコンテキスト間の意味的類似性を評価する専門家です。"
                    "提供された2つのコンテキストを分析し、0から1の範囲で類似度スコアを算出してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "similarity_score": 0.85,\n'
                    '  "analysis": {\n'
                    '    "common_features": [ ... ],\n'
                    '    "differences": [ ... ]\n'
                    "  }\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.3)
        return self.parse_json_response(response)

    def calculate_pattern_similarity(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """パターン間の類似度を計算する。

        Args:
            prompt: 類似度計算のためのプロンプト

        Returns:
            類似度スコアを含む結果
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたは進化パターン間の類似性を評価する専門家です。"
                    "提供された2つのパターン（状態とコンテキスト）を分析し、"
                    "0から1の範囲で類似度スコアを算出してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "similarity_score": 0.75,\n'
                    '  "pattern_analysis": {\n'
                    '    "state_similarity": { ... },\n'
                    '    "context_similarity": { ... },\n'
                    '    "key_differences": [ ... ]\n'
                    "  }\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.3)
        return self.parse_json_response(response)

    def analyze_evolution_pattern(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """進化パターンを分析する。

        Args:
            prompt: パターン分析のためのプロンプト

        Returns:
            分析結果
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたは進化パターンを分析する専門家です。"
                    "提供されたパターンの初期状態、進化後の状態、パフォーマンス改善、"
                    "およびコンテキストを分析し、パターンの特徴と効果を評価してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "is_successful": true,\n'
                    '  "analysis": {\n'
                    '    "improvement_factors": [ ... ],\n'
                    '    "context_factors": [ ... ],\n'
                    '    "factor_impacts": { ... }\n'
                    "  },\n"
                    '  "recommendations": [ ... ]\n'
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.5)
        return self.parse_json_response(response)

    def generate_operator_spec(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """オペレーターの仕様を生成する。

        Args:
            prompt: 仕様生成のためのプロンプト

        Returns:
            生成された仕様
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムのオペレーター仕様を生成する専門家です。"
                    "タスクの説明とコンテキストを分析し、必要なオペレーターの仕様を生成してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "operator_name": "オペレーター名",\n'
                    '  "description": "オペレーターの説明",\n'
                    '  "required_inputs": {\n'
                    '    "input1": "説明1",\n'
                    '    "input2": "説明2"\n'
                    "  },\n"
                    '  "expected_outputs": {\n'
                    '    "output1": "説明1",\n'
                    '    "output2": "説明2"\n'
                    "  },\n"
                    '  "processing_logic": "処理ロジックの説明",\n'
                    '  "potential_next_tasks": ["次のタスク1", "次のタスク2"]\n'
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.7)
        return self.parse_json_response(response)

    def generate_operator_code(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """オペレーターのコードを生成する。

        Args:
            prompt: コード生成のためのプロンプト

        Returns:
            生成されたコード
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはPythonコードを生成する専門家です。"
                    "オペレーターの仕様に基づいて、実装コードを生成してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "code": "生成されたPythonコード",\n'
                    '  "dependencies": ["必要なパッケージ1", "必要なパッケージ2"],\n'
                    '  "test_cases": ["テストケース1", "テストケース2"]\n'
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.7)
        return self.parse_json_response(response)

    def propose_operator_evolution(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """オペレーターの進化を提案する。

        Args:
            prompt: 進化提案のためのプロンプト

        Returns:
            進化の提案
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムのオペレーター進化を提案する専門家です。"
                    "現在のオペレーターの状態とパフォーマンスデータを分析し、改善案を提案してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "improvements": {\n'
                    '    "logic_updates": ["更新1", "更新2"],\n'
                    '    "parameter_adjustments": {"param1": "新しい値1"},\n'
                    '    "new_features": ["機能1", "機能2"]\n'
                    "  }\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.7)
        return self.parse_json_response(response)

    def prioritize_tasks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの優先順位付けを行う。

        Args:
            context: 優先順位付けのためのコンテキスト情報
                - objective: システムの目標
                - current_tasks: 現在のタスクリスト
                - completed_tasks: 完了したタスクリスト
                - execution_history: 実行履歴

        Returns:
            優先順位付けの結果
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはタスクの優先順位付けを行う専門家です。"
                    "提供されたタスクリストとコンテキストを分析し、"
                    "各タスクの優先度を決定してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "priorities": [\n'
                    "    {\n"
                    '      "task_id": "タスクID",\n'
                    '      "priority": 優先度（0-1の範囲）,\n'
                    '      "reasoning": "優先度の理由"\n'
                    "    },\n"
                    "    ...\n"
                    "  ],\n"
                    '  "analysis": {\n'
                    '    "dependencies": {"タスクID": ["依存タスクID", ...]},\n'
                    '    "critical_path": ["タスクID", ...],\n'
                    '    "bottlenecks": ["タスクID", ...]\n'
                    "  }\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.3)
        return self.parse_json_response(response)

    def evaluate_objective_completion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """目標の達成状況を評価する。

        Args:
            context: 評価のためのコンテキスト情報
                - objective: システムの目標
                - execution_history: 実行履歴
                - performance_metrics: パフォーマンス指標

        Returns:
            評価結果
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムの目標達成状況を評価する専門家です。"
                    "提供された目標、実行履歴、パフォーマンス指標を分析し、"
                    "目標が達成されたかどうかを判断してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "is_achieved": true/false,\n'
                    '  "completion_rate": 0.0-1.0,\n'
                    '  "analysis": {\n'
                    '    "completed_objectives": ["達成された目標1", ...],\n'
                    '    "remaining_objectives": ["残りの目標1", ...],\n'
                    '    "blockers": ["ブロッカー1", ...]\n'
                    "  },\n"
                    '  "recommendations": [\n'
                    '    {\n'
                    '      "action": "推奨アクション",\n'
                    '      "priority": "high/medium/low",\n'
                    '      "expected_impact": "期待される影響"\n'
                    "    },\n"
                    "    ...\n"
                    "  ]\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(context, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.3)
        return self.parse_json_response(response)

    def suggest_new_tasks(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """新しいタスクを提案する。

        Args:
            prompt: タスク提案のためのプロンプト情報
                - objective: システムの目標
                - current_context: 現在のコンテキスト
                - execution_history: 実行履歴

        Returns:
            提案されたタスクのリスト
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "あなたはAIシステムのタスク生成の専門家です。"
                    "システムの目標、現在のコンテキスト、実行履歴を分析し、"
                    "次に実行すべき新しいタスクを提案してください。\n\n"
                    "応答は必ず以下のJSON形式で返してください：\n"
                    "{\n"
                    '  "suggested_tasks": [\n'
                    "    {\n"
                    '      "description": "タスクの説明",\n'
                    '      "operator_type": "使用するオペレーターの種類",\n'
                    '      "priority": 優先度（0-1の範囲）,\n'
                    '      "params": {\n'
                    '        "param1": "値1",\n'
                    '        "param2": "値2"\n'
                    "      },\n"
                    '      "expected_outcomes": ["期待される結果1", "期待される結果2"],\n'
                    '      "dependencies": ["依存タスク1", "依存タスク2"]\n'
                    "    },\n"
                    "    ...\n"
                    "  ],\n"
                    '  "analysis": {\n'
                    '    "current_progress": "現在の進捗状況の分析",\n'
                    '    "gaps": ["未対応の領域1", "未対応の領域2"],\n'
                    '    "opportunities": ["改善機会1", "改善機会2"]\n'
                    "  }\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.7)
        return self.parse_json_response(response) 