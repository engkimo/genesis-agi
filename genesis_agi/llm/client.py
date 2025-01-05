"""LLMクライアント。"""
from typing import Any, Dict, List, Optional, Union
import json
import logging
import os
from openai import OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam
)

logger = logging.getLogger(__name__)


class LLMClient:
    """LLMクライアント。"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """初期化。

        Args:
            api_key: OpenAI APIキー（Noneの場合は環境変数から取得）
            model: 使用するモデル名
        """
        self.model = model
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        self.client = OpenAI()

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> ChatCompletion:
        """ChatGPT APIを使用してチャット補完を実行する。

        Args:
            messages: メッセージリスト
            temperature: 温度パラメータ
            max_tokens: 最大トークン数

        Returns:
            ChatCompletion
        """
        try:
            # メッセージの型を変換
            formatted_messages: List[ChatCompletionMessageParam] = []
            for msg in messages:
                if msg["role"] == "system":
                    formatted_messages.append(
                        ChatCompletionSystemMessageParam(
                            role="system",
                            content=msg["content"]
                        )
                    )
                elif msg["role"] == "user":
                    formatted_messages.append(
                        ChatCompletionUserMessageParam(
                            role="user",
                            content=msg["content"]
                        )
                    )

            # APIリクエストを実行
            response = self.client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens if max_tokens is not None else None
            )
            
            return response

        except Exception as e:
            logger.error(f"チャット補完の実行中にエラーが発生: {str(e)}")
            raise

    def parse_json_response(self, response: ChatCompletion) -> Any:
        """ChatCompletionのレスポンスからJSONデータを抽出する。

        Args:
            response: ChatCompletionのレスポンス

        Returns:
            パースされたJSONデータ
        """
        try:
            content = response.choices[0].message.content
            if not content:
                return []
            
            # JSONデータを探す
            start_idx = content.find("[")
            end_idx = content.rfind("]")
            
            if start_idx == -1 or end_idx == -1:
                # リストが見つからない場合は辞書を探す
                start_idx = content.find("{")
                end_idx = content.rfind("}")
                
                if start_idx == -1 or end_idx == -1:
                    logger.warning("JSONデータが見つかりません")
                    return []
            
            json_str = content[start_idx:end_idx + 1]
            return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSONのパースに失敗: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"レスポンスの処理中にエラーが発生: {str(e)}")
            return []

    def _create_messages(self, system_content: str, user_content: str) -> List[ChatCompletionMessageParam]:
        """メッセージリストを作成する。

        Args:
            system_content: システムメッセージの内容
            user_content: ユーザーメッセージの内容

        Returns:
            メッセージリスト
        """
        return [
            ChatCompletionSystemMessageParam(
                role="system",
                content=system_content
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=user_content
            )
        ]

    def generate_strategy(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """生成戦略を生成する。

        Args:
            prompt: プロンプト

        Returns:
            生成された戦略
        """
        messages = self._create_messages(
            system_content="あなたはオペレーター生成戦略の専門家です。",
            user_content=f"""
            以下の情報に基づいて、最適な生成戦略を提案してください：

            タスク: {prompt['task']}
            コンテキスト: {prompt['context']}
            既知の戦略: {prompt['known_strategies']}
            実行履歴: {prompt['history']}
            """
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        strategy_text = response.choices[0].message.content
        if not strategy_text:
            strategy_text = "デフォルトの戦略を使用します。"
        
        # 戦略をパースして返す
        return {
            "strategy_type": "adaptive",  # デフォルトの戦略タイプ
            "parameters": {
                "description": strategy_text,
                "complexity": "medium",
                "focus_areas": ["error_handling", "performance_optimization"]
            }
        }

    def generate_operator_code(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """オペレーターコードを生成する。

        Args:
            prompt: プロンプト

        Returns:
            生成されたコード
        """
        messages = self._create_messages(
            system_content="あなたはPythonオペレーターの生成の専門家です。",
            user_content=f"""
            以下の情報に基づいて、オペレーターコードを生成してください：

            タスク: {prompt['task']}
            コンテキスト: {prompt['context']}
            戦略: {prompt['strategy']}
            既知のオペレーター: {prompt['known_operators']}
            """
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        operator_code = response.choices[0].message.content
        if not operator_code:
            operator_code = "class DefaultOperator(BaseOperator): pass"
        
        # クラス名を抽出（最初のclassステートメントから）
        class_name = "CustomOperator"  # デフォルト値
        for line in operator_code.split("\n"):
            if line.startswith("class "):
                class_name = line.split()[1].split("(")[0]
                break

        return {
            "code": operator_code,
            "class_name": class_name
        }

    def evolve_operator(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """オペレーターを進化させる。

        Args:
            prompt: プロンプト

        Returns:
            進化したコード
        """
        messages = self._create_messages(
            system_content="あなたはPythonオペレーターの最適化の専門家です。",
            user_content=f"""
            以下の情報に基づいて、オペレーターを改善してください：

            元のコード: {prompt['original_code']}
            パフォーマンス: {prompt['performance']}
            改善戦略: {prompt['strategy']}
            改善フォーカス: {prompt['improvement_focus']}
            """
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        evolved_code = response.choices[0].message.content
        if not evolved_code:
            evolved_code = prompt['original_code']
        
        # クラス名を抽出
        class_name = "EvolvedOperator"  # デフォルト値
        for line in evolved_code.split("\n"):
            if line.startswith("class "):
                class_name = line.split()[1].split("(")[0]
                break

        return {
            "code": evolved_code,
            "class_name": class_name
        }

    def analyze_task(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """タスクを分析する。

        Args:
            prompt: プロンプト

        Returns:
            分析結果
        """
        messages = self._create_messages(
            system_content="あなたはタスク分析の専門家です。",
            user_content=f"""
            以下のタスクを分析し、必要なオペレータータイプとパラメータを特定してください：

            タスク: {prompt.get('description', '')}
            コンテキスト: {prompt.get('context', '')}
            生成戦略: {prompt.get('generation_strategy', '')}
            """
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        analysis_text = response.choices[0].message.content
        if not analysis_text:
            analysis_text = "デフォルトの分析結果を使用します。"
        
        # 分析結果をパースして返す
        return {
            "required_operator_type": "DataAnalysisOperator",  # デフォルトのオペレータータイプ
            "required_params": {
                "description": analysis_text,
                "priority": 1.0,
                "estimated_complexity": 0.5
            }
        }

    def generate_tasks(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        """新しいタスクを生成する。

        Args:
            prompt: プロンプト

        Returns:
            生成されたタスク
        """
        # コンテキストを要約して短くする
        execution_history_summary = []
        if "execution_history" in prompt:
            # 直近の5つの実行履歴のみを使用
            history = prompt["execution_history"][-5:] if isinstance(prompt["execution_history"], list) else []
            for item in history:
                task_name = ""
                if isinstance(item, dict):
                    task_name = str(item.get("task", ""))
                elif isinstance(item, str):
                    task_name = str(item)
                
                if len(task_name) > 100:
                    task_name = task_name[:100]
                
                execution_history_summary.append({
                    "task": task_name,
                    "status": item.get("status", "unknown") if isinstance(item, dict) else "unknown"
                })

        current_state_summary = {
            "total_tasks": prompt.get("current_state", {}).get("total_tasks", 0),
            "successful_tasks": prompt.get("current_state", {}).get("successful_tasks", 0),
            "failed_tasks": prompt.get("current_state", {}).get("failed_tasks", 0)
        }

        context_str = str(prompt.get("context", ""))
        if len(context_str) > 200:
            context_str = context_str[:200]

        messages = self._create_messages(
            system_content="あなたはタスク生成の専門家です。",
            user_content=f"""
            以下の情報に基づいて、新しいタスクを生成してください：

            目的: {prompt.get('objective', '')}
            コンテキスト: {context_str}
            直近の実行履歴: {execution_history_summary}
            現在の状態: {current_state_summary}
            """
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        task_text = response.choices[0].message.content
        if not task_text:
            task_text = "デフォルトのタスクを生成します。"

        return {
            "tasks": [
                {
                    "description": task_text,
                    "operator_type": "DataAnalysisOperator",
                    "priority": 1.0,
                    "params": {}
                }
            ]
        }

    def prioritize_tasks(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの優先順位付けを行う。

        Args:
            context: コンテキスト

        Returns:
            優先順位付けの結果
        """
        # コンテキストを要約して短くする
        current_tasks_summary = [
            {
                "id": task.get("id", "unknown"),
                "description": str(task.get("description", ""))[:100] if task.get("description") else ""
            }
            for task in context.get("current_tasks", [])
        ]

        # 完了タスクの要約を作成
        completed_tasks = context.get("completed_tasks", [])[-5:]  # 直近5つのタスクを取得
        completed_tasks_summary = []
        for task in completed_tasks:
            if isinstance(task, str):
                completed_tasks_summary.append(task[:100])
            elif isinstance(task, dict):
                task_str = str(task.get("task_name", "")) if task.get("task_name") else str(task)
                completed_tasks_summary.append(task_str[:100])

        messages = self._create_messages(
            system_content="あなたはタスクの優先順位付けの専門家です。",
            user_content=f"""
            以下の情報に基づいて、タスクの優先順位を決定してください：

            目的: {context.get('objective', '')}
            現在のタスク: {current_tasks_summary}
            直近の完了タスク: {completed_tasks_summary}
            """
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        priority_text = response.choices[0].message.content
        if not priority_text:
            # デフォルトの優先順位を返す
            return {
                "priorities": [
                    {"task_id": task.get("id", "unknown"), "priority": 1.0}
                    for task in context.get("current_tasks", [])
                ]
            }

        return {
            "priorities": [
                {"task_id": task.get("id", "unknown"), "priority": 1.0}
                for task in context.get("current_tasks", [])
            ]
        }

    def evaluate_objective_completion(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """目的の達成状況を評価する。

        Args:
            context: コンテキスト

        Returns:
            評価結果
        """
        messages = self._create_messages(
            system_content="あなたは目的達成の評価の専門家です。",
            user_content=f"""
            以下の情報に基づいて、目的の達成状況を評価してください：

            目的: {context['objective']}
            実行履歴: {context['execution_history']}
            パフォーマンス指標: {context['performance_metrics']}
            """
        )

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )

        evaluation_text = response.choices[0].message.content
        if not evaluation_text:
            return {"is_achieved": False}

        return {
            "is_achieved": False,  # デフォルトではFalse
            "completion_rate": 0.0,
            "analysis": evaluation_text
        } 