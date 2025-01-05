"""データベース初期化スクリプト。"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from genesis_agi.models.operator import Base

def init_db():
    """データベースを初期化する。"""
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if database_url is None:
        raise ValueError("DATABASE_URLが設定されていません")
    
    engine = create_engine(database_url)
    
    # テーブルの作成
    Base.metadata.create_all(engine)
    
    print("データベースの初期化が完了しました")

if __name__ == "__main__":
    init_db() 