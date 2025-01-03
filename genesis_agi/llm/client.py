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
                    "最適な生成戦略を提案してください。"
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
                    "最適な進化戦略を提案してください。"
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
                    "提供された2つのコンテキストを分析し、0から1の範囲で類似度スコアを算出してください。"
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
                    "0から1の範囲で類似度スコアを算出してください。"
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
                    "およびコンテキストを分析し、パターンの特徴と効果を評価してください。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt, ensure_ascii=False, indent=2),
            },
        ]

        response = self._call_openai(messages, temperature=0.5)
        return self.parse_json_response(response) 