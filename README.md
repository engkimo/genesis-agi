# Genesis AGI

BabyAGIにインスパイアされた、タスク管理・実行システム。Airflowライクなオペレーターパターンを採用し、柔軟なタスク定義と実行を可能にします。

## 特徴

- タスクの自己生成と管理
- Airflowライクなオペレーターパターン
- 柔軟なタスク定義と実行フロー
- 拡張可能なオペレーター構造
- モダンな開発環境（uv, ruff, black, mypy）

## 技術スタック

- Python 3.9+
- uv: 高速なPythonパッケージマネージャー
- Ruff: 高速なPythonリンター
- Black: コードフォーマッター
- MyPy: 静的型チェッカー
- Pytest: テストフレームワーク
- Pydantic: データバリデーション

## インストール

uvを使用してインストール：

```bash
# uvのインストール（まだ入っていない場合）
pip install uv

# 依存関係のインストール
uv pip install -r requirements.txt
```

## 開発環境のセットアップ

### コード品質ツール

プロジェクトでは以下のコード品質ツールを使用しています：

```bash
# コードフォーマット
black .

# リント
ruff check .
ruff format .

# 型チェック
mypy .

# テスト実行
pytest
```

### VS Code設定

`.vscode/settings.json`が提供されており、以下の機能が自動的に有効になります：

- 保存時の自動フォーマット（Black）
- インポートの自動整理（Ruff）
- 型チェック（MyPy）
- リンティング

## プロジェクト構造

```
genesis_agi/
├── __init__.py
├── operators/
│   ├── __init__.py
│   └── base_operator.py      # 基底オペレータークラス
└── ... (その他のモジュール)
```

## オペレーターの使用方法

基本的なオペレーターの実装例：

```python
from genesis_agi.operators import BaseOperator

class CustomOperator(BaseOperator):
    def __init__(self, task_id: str, custom_param: str, **kwargs) -> None:
        super().__init__(task_id, **kwargs)
        self.custom_param = custom_param

    def execute(self) -> str:
        return f"Task {self.task_id} completed with {self.custom_param}"
```

## 設定ファイル

### pyproject.toml

プロジェクトの主要な設定は`pyproject.toml`で管理されています：

- プロジェクトのメタデータ
- Ruffの設定（リンター）
- Blackの設定（フォーマッター）
- MyPyの設定（型チェッカー）

### requirements.txt

必要な依存関係が記載されています：

- 本番環境の依存関係
- 開発環境の依存関係（リンター、フォーマッター等）

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。