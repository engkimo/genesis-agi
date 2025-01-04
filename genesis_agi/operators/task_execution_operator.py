"""Task execution operator for Genesis AGI."""
from typing import Any, Dict, Literal
from pydantic import BaseModel, Field
import json
from genesis_agi.llm.client import LLMClient
from genesis_agi.models.task import Task
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class TaskMetrics(BaseModel):
    """タスク実行のメトリクス。"""
    execution_time: float = Field(ge=0, description="実行時間（秒）")
    quality_score: float = Field(ge=0, le=1, description="品質スコア（0-1）")
    progress_score: float = Field(ge=0, le=1, description="進捗スコア（0-1）")
    confidence_score: float = Field(ge=0, le=1, description="信頼度スコア（0-1）")


class TaskResult(BaseModel):
    """タスク実行の結果。"""
    status: Literal["success", "failed"] = Field(description="タスクの実行状態")
    output: str = Field(description="実行結果の詳細な説明")
    metrics: TaskMetrics = Field(description="実行のメトリクス")
    details: Dict[str, Any] = Field(default_factory=dict, description="追加の詳細情報")


class TaskExecutionOperator:
    """タスクを実行するオペレーター。"""

    def __init__(self, llm_client: LLMClient):
        """初期化。

        Args:
            llm_client: LLMクライアント
        """
        self.llm_client = llm_client

    def execute(self, task: Task, context: Dict[str, Any]) -> Dict[str, Any]:
        """タスクを実行する。

        Args:
            task: 実行するタスク
            context: 実行コンテキスト

        Returns:
            実行結果
        """
        try:
            logger.debug(f"タスク実行開始: {task.name}")
            logger.debug(f"コンテキスト: {context}")

            # タスクの実行
            messages = [
                ChatCompletionSystemMessageParam(
                    role="system",
                    content="""あなたはタスク実行の専門家です。与えられたタスクを実行し、結果を報告してください。
                    結果は必ず以下のJSON形式で返してください：
                    {
                        "status": "success",
                        "output": "実行結果の説明（得られた情報、気づき、次のステップなど）",
                        "metrics": {
                            "execution_time": 1.5,
                            "quality_score": 0.85,
                            "progress_score": 0.7,
                            "confidence_score": 0.8
                        },
                        "details": {
                            "findings": ["発見1", "発見2"],
                            "next_steps": ["次のステップ1", "次のステップ2"],
                            "challenges": ["課題1", "課題2"],
                            "recommendations": ["推奨事項1", "推奨事項2"]
                        }
                    }
                    
                    タスクが成功したと判断する基準（以下のいずれかを満たす）：
                    1. 何らかの有用な情報や気づきが得られた（quality_score > 0.3）
                    2. タスクの方向性が明確になった（progress_score > 0.3）
                    3. 次のステップが具体化できた（confidence_score > 0.3）
                    
                    各スコアの意味：
                    - quality_score: 得られた情報や結果の質
                    - progress_score: タスクの目標に対する進捗
                    - confidence_score: 結果の信頼性
                    
                    いずれかのスコアが0.3以上であれば、タスクは部分的に成功したとみなします。"""
                ),
                ChatCompletionUserMessageParam(
                    role="user",
                    content=f"""
                    タスク: {task.description}
                    
                    コンテキスト情報:
                    - 目的: {context.get("objective", "未設定")}
                    - これまでの進捗: {json.dumps([{
                        "task": r.get("task", {}).get("description", ""),
                        "status": r.get("result", {}).get("status", ""),
                        "output": r.get("result", {}).get("output", "")
                    } for r in context.get("task_history", [])], ensure_ascii=False, indent=2)}
                    - 現在の状態: {json.dumps(context.get("current_state", {}), ensure_ascii=False, indent=2)}
                    
                    このタスクを実行し、結果を指定されたJSON形式で返してください。
                    部分的な進展や気づきでも、有用な情報が得られた場合は"success"として報告してください。
                    """
                )
            ]

            logger.debug("LLMにリクエストを送信")
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7,
                seed=42
            )
            logger.debug(f"LLMからの応答を受信: {response}")

            content = response.choices[0].message.content
            if not content:
                raise ValueError("LLMからの応答が空です")
            
            logger.debug(f"応答内容: {content}")
            result_json = json.loads(content)
            logger.debug(f"パース済み結果: {result_json}")

            # メトリクスの初期化と検証
            metrics = result_json.get("metrics", {})
            metrics.setdefault("execution_time", 1.0)
            metrics.setdefault("quality_score", 0.5)
            metrics.setdefault("progress_score", 0.5)
            metrics.setdefault("confidence_score", 0.5)
            
            # 成功判定（より寛容な基準）
            quality_score = metrics.get("quality_score", 0)
            progress_score = metrics.get("progress_score", 0)
            confidence_score = metrics.get("confidence_score", 0)
            
            # いずれかのスコアが0.3以上であれば成功
            is_successful = (
                quality_score >= 0.3 or
                progress_score >= 0.3 or
                confidence_score >= 0.3
            )
            
            result_json["status"] = "success" if is_successful else "failed"
            if not is_successful:
                result_json["output"] = (
                    f"タスクの評価スコアが基準を下回っています: "
                    f"quality={quality_score:.2f}, "
                    f"progress={progress_score:.2f}, "
                    f"confidence={confidence_score:.2f}"
                )

            # 詳細情報の追加
            result_json.setdefault("details", {
                "findings": [],
                "next_steps": [],
                "challenges": [],
                "recommendations": []
            })

            logger.debug(f"最終結果: {result_json}")
            return result_json

        except Exception as e:
            logger.error(f"タスク実行中にエラーが発生: {str(e)}")
            return {
                "status": "failed",
                "output": f"タスクの実行中にエラーが発生しました: {str(e)}",
                "metrics": {
                    "execution_time": 0,
                    "quality_score": 0,
                    "progress_score": 0,
                    "confidence_score": 0
                },
                "details": {
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            }

    def validate(self, task: Task) -> bool:
        """タスクが実行可能かどうかを検証する。

        Args:
            task: 検証するタスク

        Returns:
            実行可能な場合はTrue
        """
        return True  # 基本的にすべてのタスクを実行可能とする 