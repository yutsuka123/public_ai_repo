from django.apps import AppConfig
from pathlib import Path
from dotenv import load_dotenv
import os


class ChatConfig(AppConfig):
    """
    Chatアプリケーションの設定クラス
    
    Attributes:
        default_auto_field (str): Djangoのデフォルトの自動フィールド
        name (str): アプリケーション名
        path (Path): アプリケーションのパス
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    path = Path(__file__).resolve().parent
    
    def ready(self):
        """
        アプリケーション起動時の初期化処理
        AIタスクの初期化などを行う
        """
        # 環境変数の読み込み
        load_dotenv()
        
        # より一般的なエラーメッセージを使用
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("必要な認証情報が設定されていません")
            
        # タスクの初期化と明示的な使用
        from . import tasks
        tasks.ai_receive_task.start()  # タスクを明示的に初期化

def get_api_key():
    """APIキーを安全に取得する
    
    Returns:
        str: APIキー
        
    Raises:
        ValueError: APIキーが設定されていない場合
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("認証情報が設定されていません")
    return api_key 