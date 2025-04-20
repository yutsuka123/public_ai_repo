"""
OpenAI APIの設定と初期化を行うモジュール

環境変数から安全にAPIキーを取得し、OpenAIクライアントを初期化します。
"""
from dotenv import load_dotenv
import os
from enum import Enum
import openai

# 環境変数の読み込み
load_dotenv()

class Provider(Enum):
    """
    利用可能なAIプロバイダーの列挙型
    """
    OPENAI = "openai"

def get_openai_api_key():
    """
    OpenAI APIキーを環境変数から安全に取得する
    
    Returns:
        str: OpenAI APIキー
        
    Raises:
        ValueError: APIキーが設定されていない場合
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI APIキーが設定されていません")
    return api_key

# OpenAIクライアントの初期化
openai.api_key = get_openai_api_key() 