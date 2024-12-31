"""Prompt management for Genesis AGI."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """プロンプトテンプレート。"""

    name: str = Field(..., description="テンプレート名")
    content: str = Field(..., description="テンプレートの内容")
    version: int = Field(default=1, description="バージョン番号")
    metrics: Dict[str, float] = Field(
        default_factory=dict, description="プロンプトのパフォーマンスメトリクス"
    )
    improvement_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="改善履歴"
    )


class PromptManager:
    """プロンプト管理クラス。"""

    def __init__(self) -> None:
        """初期化。"""
        self.templates: Dict[str, PromptTemplate] = {}
        self.performance_history: List[Dict[str, Any]] = []

    def register_template(self, name: str, content: str) -> None:
        """プロンプトテンプレートを登録する。

        Args:
            name: テンプレート名
            content: テンプレートの内容
        """
        if name not in self.templates:
            self.templates[name] = PromptTemplate(name=name, content=content)
        else:
            current = self.templates[name]
            self.templates[name] = PromptTemplate(
                name=name,
                content=content,
                version=current.version + 1,
                metrics=current.metrics.copy(),
                improvement_history=current.improvement_history.copy(),
            )

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """プロンプトテンプレートを取得する。

        Args:
            name: テンプレート名

        Returns:
            プロンプトテンプレート
        """
        return self.templates.get(name)

    def record_performance(
        self, template_name: str, metrics: Dict[str, float]
    ) -> None:
        """プロンプトのパフォーマンスを記録する。

        Args:
            template_name: テンプレート名
            metrics: パフォーマンスメトリクス
        """
        if template := self.templates.get(template_name):
            # メトリクスの更新（移動平均）
            for key, value in metrics.items():
                if key in template.metrics:
                    template.metrics[key] = (template.metrics[key] * 0.7) + (value * 0.3)
                else:
                    template.metrics[key] = value

            # パフォーマンス履歴の記録
            self.performance_history.append(
                {
                    "template_name": template_name,
                    "version": template.version,
                    "metrics": metrics,
                }
            )

    def improve_template(
        self, template_name: str, performance_data: Dict[str, Any]
    ) -> Optional[str]:
        """プロンプトテンプレートを改善する。

        Args:
            template_name: テンプレート名
            performance_data: パフォーマンスデータ

        Returns:
            改善されたプロンプト
        """
        if template := self.templates.get(template_name):
            # 改善履歴を記録
            template.improvement_history.append(
                {
                    "version": template.version,
                    "metrics": template.metrics.copy(),
                    "performance_data": performance_data,
                }
            )

            # TODO: LLMを使用してプロンプトを改善
            # 現在は仮の実装
            return template.content

        return None

    def analyze_template_performance(
        self, template_name: str
    ) -> Optional[Dict[str, Any]]:
        """プロンプトのパフォーマンスを分析する。

        Args:
            template_name: テンプレート名

        Returns:
            パフォーマンス分析結果
        """
        if template := self.templates.get(template_name):
            relevant_history = [
                h
                for h in self.performance_history
                if h["template_name"] == template_name
            ]
            
            if not relevant_history:
                return None

            # 基本的な統計情報を計算
            metrics_summary = {}
            for metric in template.metrics.keys():
                values = [h["metrics"].get(metric, 0) for h in relevant_history]
                if values:
                    metrics_summary[metric] = {
                        "average": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "trend": "improving"
                        if values[-1] > values[0]
                        else "declining",
                    }

            return {
                "template_name": template_name,
                "current_version": template.version,
                "metrics_summary": metrics_summary,
                "improvement_count": len(template.improvement_history),
            }

        return None 