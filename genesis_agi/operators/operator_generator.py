"""オペレーター生成モジュール。"""
from typing import Any, Dict, List, Optional, Type
import logging
import inspect
import json
from genesis_agi.llm.client import LLMClient
from genesis_agi.operators.operator_registry import OperatorRegistry
from genesis_agi.utils.cache import Cache
from genesis_agi.operators.base_operator import BaseOperator

logger = logging.getLogger(__name__)


class OperatorGenerator:
    """オペレーターを動的に生成するジェネレーター。"""

    def __init__(
        self,
        llm_client: LLMClient,
        registry: OperatorRegistry,
        cache: Optional[Cache] = None
    ):
        """初期化。"""
        self.llm_client = llm_client
        self.registry = registry
        self.cache = cache

    def generate_operator(
        self,
        task_description: str,
        current_context: Dict[str, Any],
        generation_strategy: Dict[str, Any]
    ) -> Type[BaseOperator]:
        """タスクに適したオペレーターを生成する。

        Args:
            task_description: タスクの説明
            current_context: 現在のコンテキスト
            generation_strategy: 生成戦略

        Returns:
            生成されたオペレータークラス

        Raises:
            ValueError: タスクの説明が無効な場合
            RuntimeError: オペレーターの生成に失敗した場合
        """
        if not task_description:
            raise ValueError("タスクの説明が必要です")

        try:
            # キャッシュをチェック
            cache_key = f"operator:{task_description}"
            if self.cache:
                cached_operator = self._load_from_cache(cache_key)
                if cached_operator:
                    logger.info(f"キャッシュからオペレーターを読み込みました: {cached_operator.__name__}")
                    return cached_operator

            # オペレータータイプを生成
            operator_type = self._generate_operator_type(task_description)
            logger.debug(f"生成されたオペレータータイプ: {operator_type}")

            # 既存のオペレーターをチェック
            if self.registry.has_operator(operator_type):
                existing_operator = self.registry.get_operator(operator_type)
                if existing_operator:
                    logger.info(f"既存のオペレーターを使用: {operator_type}")
                    return existing_operator

            # オペレーターコードを生成
            operator_code = self._generate_operator_code(
                task_description,
                current_context,
                generation_strategy
            )
            logger.debug("オペレーターコードを生成しました")

            # オペレータークラスを動的に生成
            operator_class = self._create_operator_class(operator_code)
            if not operator_class:
                raise RuntimeError("オペレータークラスの生成に失敗しました")

            # オペレーターを登録
            try:
                self.registry.register_operator(
                    operator_class,
                    description=task_description
                )
                logger.info(f"新しいオペレーターを登録しました: {operator_type}")
            except Exception as e:
                logger.error(f"オペレーターの登録に失敗: {str(e)}")
                raise RuntimeError(f"オペレーターの登録に失敗: {str(e)}") from e

            # キャッシュに保存
            if self.cache:
                self._save_to_cache(cache_key, operator_class)
                logger.debug(f"オペレーターをキャッシュに保存: {operator_type}")

            return operator_class

        except Exception as e:
            error_msg = f"オペレーターの生成に失敗: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _generate_operator_type(self, task_description: str) -> str:
        """タスクの説明からオペレータータイプを生成する。

        Args:
            task_description: タスクの説明

        Returns:
            オペレータータイプ
        """
        # LLMを使用してオペレータータイプを生成
        messages = [
            {"role": "system", "content": "あなたはオペレーター名の生成の専門家です。"},
            {"role": "user", "content": f"""
            以下のタスクに適したオペレーター名を生成してください。
            名前は英語で、CamelCase形式で、最後に'Operator'を付けてください。
            
            タスク: {task_description}
            """}
        ]
        
        response = self.llm_client.chat_completion(messages)
        operator_type = response.choices[0].message.content.strip()
        
        # 'Operator'で終わっていない場合は追加
        if not operator_type.endswith('Operator'):
            operator_type += 'Operator'
        
        return operator_type

    def _generate_operator_code(
        self,
        task_description: str,
        current_context: Dict[str, Any],
        generation_strategy: Dict[str, Any]
    ) -> str:
        """オペレーターのコードを生成する。

        Args:
            task_description: タスクの説明
            current_context: 現在のコンテキスト
            generation_strategy: 生成戦略

        Returns:
            生成されたコード
        """
        messages = [
            {"role": "system", "content": "あなたはPythonコードジェネレーターの専門家です。"},
            {"role": "user", "content": f"""
            以下の要件に基づいて、BaseOperatorを継承したオペレータークラスを生成してください。

            タスク: {task_description}
            コンテキスト: {json.dumps(current_context, ensure_ascii=False)}
            生成戦略: {json.dumps(generation_strategy, ensure_ascii=False)}

            以下の要件を満たすコードを生成してください：
            1. BaseOperatorを継承すること
            2. 必要なメソッドをすべて実装すること（execute, validate_input, get_required_inputs）
            3. エラーハンドリングを適切に行うこと
            4. ログ出力を適切に行うこと
            5. 型ヒントを使用すること
            6. __init__メソッドでtask_idとparamsを受け取り、super().__init__()を呼び出すこと

            以下のテンプレートに従ってください：

            '''
            from typing import Any, Dict, List
            import logging
            from genesis_agi.operators.base_operator import BaseOperator

            logger = logging.getLogger(__name__)

            class DataAnalysisOperator(BaseOperator):
                def __init__(self, task_id: str, params: Dict[str, Any] = None):
                    super().__init__(task_id, params)
                    self.data = None
                    self.analysis_results = dict()

                def execute(self) -> Dict[str, Any]:
                    try:
                        logger.info(f"タスク {self.task_id} の実行を開始")
                        
                        # 入力データの取得
                        input_data = self.params.get("input_data", dict())
                        if not self.validate_input(input_data):
                            logger.error("入力データが不正です")
                            return self.prepare_result(None, status="error")
                        
                        # データの分析
                        self.data = input_data.get("dataset")
                        if self.data is None:
                            logger.error("データセットが見つかりません")
                            return self.prepare_result(None, status="error")
                        
                        # 分析結果の生成
                        self.analysis_results = dict(
                            summary="データ分析の結果をここに記述",
                            statistics=dict(),
                            visualizations=[]
                        )
                        
                        logger.info(f"タスク {self.task_id} の実行が完了")
                        return self.prepare_result(self.analysis_results)
                        
                    except Exception as e:
                        logger.error(f"実行エラー: {str(e)}")
                        return self.prepare_result(None, status="error")

                def validate_input(self, input_data: Dict[str, Any]) -> bool:
                    required_inputs = self.get_required_inputs()
                    return all(key in input_data for key in required_inputs)

                def get_required_inputs(self) -> List[str]:
                    return ["dataset", "analysis_type", "visualization_options"]
            '''

            上記のテンプレートを参考に、与えられたタスクに適したオペレーターを生成してください。
            """}
        ]
        
        response = self.llm_client.chat_completion(messages)
        return response.choices[0].message.content.strip()

    def _create_operator_class(self, code: str) -> Type[BaseOperator]:
        """コードからオペレータークラスを生成する。

        Args:
            code: オペレーターのコード

        Returns:
            生成されたオペレータークラス

        Raises:
            ValueError: コードが不正な場合
        """
        try:
            # 名前空間を準備
            namespace = {}
            
            # 必要なインポートを追加
            exec('from genesis_agi.operators.base_operator import BaseOperator', namespace)
            exec('import logging', namespace)
            
            # コードを実行
            exec(code, namespace)
            
            # クラスを取得
            for name, obj in namespace.items():
                if (isinstance(obj, type) and 
                    issubclass(obj, BaseOperator) and 
                    obj != BaseOperator):
                    return obj
            
            raise ValueError('有効なオペレータークラスが見つかりません')
            
        except Exception as e:
            logger.error(f'オペレータークラスの生成に失敗: {str(e)}')
            raise ValueError(f'オペレータークラスの生成に失敗: {str(e)}')

    def _load_from_cache(self, key: str) -> Optional[Type[BaseOperator]]:
        """キャッシュからオペレーターを読み込む。"""
        if not self.cache:
            return None
        
        cached_data = self.cache.get(key)
        if cached_data:
            try:
                return self._create_operator_class(cached_data)
            except Exception as e:
                logger.warning(f'キャッシュからのオペレーター読み込みに失敗: {str(e)}')
        return None

    def _save_to_cache(self, key: str, operator_class: Type[BaseOperator]) -> None:
        """オペレーターをキャッシュに保存する。"""
        if not self.cache:
            return
        
        try:
            code = inspect.getsource(operator_class)
            self.cache.set(key, code)
        except Exception as e:
            logger.warning(f'オペレーターのキャッシュ保存に失敗: {str(e)}') 