# Genesis AGI

自己改善型タスク管理システム。DAGライクなオペレーターパターンを採用し、柔軟なタスク管理と実行を実現します。

## 特徴

- 🤖 自己改善型タスク管理
- 🧠 OpenAI GPTを活用したタスク生成と実行
- 📊 パフォーマンス分析と自動最適化
- 💾 分散キャッシング対応（Redis/ファイルシステム）
- 🔍 セマンティック検索機能
- 📝 詳細なログ記録とアーティファクト管理

## 必要条件

- Python 3.9以上
- OpenAI APIキー
- uv（パッケージマネージャー）

## インストール

1. リポジトリのクローン:
```bash
git clone https://github.com/yourusername/genesis-agi.git
cd genesis-agi
```

2. 環境変数の設定:
```bash
cp .env.example .env
# .envファイルを編集し、OPENAI_API_KEYを設定
```

3. 依存関係のインストール:
```bash
uv venv
source .venv/bin/activate  # Linuxの場合
.venv/Scripts/activate     # Windowsの場合
uv sync
```

## プロジェクト構造

```
genesis-agi/
├── genesis_agi/
│   ├── operators/         # タスク実行オペレーター
│   ├── llm/              # LLMクライアント
│   ├── utils/            # ユーティリティ機能
│   └── context/          # コンテキスト管理
├── examples/             # 使用例
├── tests/               # テストコード
├── logs/               # ログファイル
├── artifacts/          # 実行アーティファクト
└── cache/             # キャッシュデータ
```

## 主要コンポーネント

### TaskManager
- タスクの生成、実行、優先順位付けを管理
- パフォーマンス分析と最適化を実行
- アーティファクトとログの管理

### オペレーター
1. **TaskCreationOperator**
   - 新しいタスクの生成
   - コンテキストに基づくタスク展開

2. **TaskExecutionOperator**
   - タスクの実行
   - 結果の評価と記録

3. **TaskPrioritizationOperator**
   - タスクの優先順位付け
   - 依存関係の管理

### ユーティリティ
- **Cache**: 分散キャッシング（Redis/ファイルシステム）
- **ContextManager**: コンテキスト管理とセマンティック検索
- **LLMClient**: OpenAI APIとの統合

## 使用方法

### 基本的な使用例

```python
from genesis_agi.llm.client import LLMClient
from genesis_agi.task_manager import TaskManager
from genesis_agi.utils.cache import Cache
from genesis_agi.operators import *

# LLMクライアントの初期化
llm_client = LLMClient(
    api_key="your-api-key",
    model="gpt-3.5-turbo"
)

# タスクマネージャーの初期化
task_manager = TaskManager(
    llm_client=llm_client,
    objective="目標の設定"
)

# オペレーターの追加
task_manager.add_operator(TaskCreationOperator(llm_client))
task_manager.add_operator(TaskExecutionOperator(llm_client))
task_manager.add_operator(TaskPrioritizationOperator(llm_client))

# タスクの実行
initial_task = task_manager.create_initial_task()
result = task_manager.execute_task(initial_task)
```

### サンプルスクリプトの実行

```bash
uv run python examples/basic_usage.py
```

## アーティファクトとログ

### ログファイル
- 場所: `./logs/genesis_agi_YYYYMMDD_HHMMSS.log`
- 内容: 実行時のすべてのログ情報

### アーティファクト
- 場所: `./artifacts/YYYYMMDD_HHMMSS/`
- ファイル:
  - `task_history.json`: タスク実行履歴
  - `current_tasks.json`: 現在のタスクリスト
  - `performance_metrics.json`: パフォーマンス指標

## キャッシュ設定

### ファイルシステムキャッシュ
```python
cache = Cache(
    backend="filesystem",
    cache_dir="./cache",
    max_size=1000
)
```

### Redisキャッシュ
```python
cache = Cache(
    backend="redis",
    redis_url="redis://localhost:6379/0"
)
```

## 開発者向け情報

### リンター設定
- Ruff: コードスタイルとエラーチェック
- Black: コードフォーマット
- 設定は`pyproject.toml`に記載

### テスト実行
```bash
uv run pytest
```

## ライセンス

MITライセンス

## 貢献

1. Forkを作成
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチをPush (`git push origin feature/amazing-feature`)
5. Pull Requestを作成