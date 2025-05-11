"""
AI支援型マルチタスク対話システム (Single-file Version)

起動時にインターフェースを選択: CUI / HTML / 音声。
CUIモードでは従来の対話ループ、HTMLモードではDjangoチャットアプリを起動、
音声モードは未実装となっています。
"""
import abc
import sys
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from openai import OpenAI
import subprocess
from pathlib import Path
from core.db_manager import ConversationDBManager
from dotenv import load_dotenv
import os
from errors.error_codes import ErrorCode, ErrorHandler
import logging
import logging.handlers
import time
import webbrowser
import chromadb

# 環境変数の読み込み
load_dotenv()

# ロガーの設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ログディレクトリの作成
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# ファイルハンドラの設定
file_handler = logging.handlers.RotatingFileHandler(
    log_dir / "main.log",
    maxBytes=1024*1024,  # 1MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
)
logger.addHandler(file_handler)

# コンソールハンドラの追加
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(
    logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
)
logger.addHandler(console_handler)

# --- Provider Enum ---
class Provider(Enum):
    """
    AIプロバイダーの列挙型
    
    Attributes:
        OPENAI: OpenAIプロバイダー
    """
    OPENAI = "openai"

# --- Interface & Task ID Definitions ---
IF_CUI = 1
IF_HTML = 2
IF_VOICE = 3
TASK_LOOP = 11
TASK_AI_RECEIVE = 12
TASK_CMD_MGR = 13
TASK_PROGRESS_AI = 14
TASK_DISPLAY = 15
TASK_INTERNAL_IF = 16
TASK_FILE_IO = 17   #ファイル読み書きを行う
TASK_AI_COMMAND1 = 21
TASK_AI_COMMAND2 = 22
TASK_AI_COMMAND3 = 23
TASK_AI_COMMAND4 = 24
TASK_AI_DB = 25 #データベースを読み書きする Langchainを想定する。
TASK_AI_GEN1 = 31
TASK_AI_GEN2 = 32
TASK_AI_GEN3 = 33
TASK_AI_CODE1 = 34
TASK_AI_CODE2 = 35
TASK_AI_VOICE = 36
TASK_AI_IMAGE = 37
TASK_AI_SPARE1 = 38
TASK_AI_SPARE2 = 39


# --- Client Factories ---
from anthropic import Anthropic
import google.generativeai as genai

# --- Internal IF Definitions ---
API_PREFIX = "@@@MY_AGENT_API_0419@@@"
API_SUFFIX = "@@@"
@dataclass
class APIPayload:
    src: str
    dst: str
    order: str
    f: str
    data: str

class InternalIFTask:
    """
    内部IFタスク (ID=16):
    - 各AIタスクは send() で他タスクへAPI文字列を送信。
    - recv() で解析して APIPayload を取得し次処理へ。
    """
    def __init__(self): self.id = TASK_INTERNAL_IF; self.name = "Internal IF"
    def send(self, src, dst, order, f, data):
        msg = ",".join([
            API_PREFIX,
            f"=src{src}", f"=dst{dst}", f"=order{order}",
            f"=f{f}", f"=data{data}", "=end", API_SUFFIX
        ])
        print(f"[{self.name}] send: {msg}")
        return msg
    def recv(self, message):
        m = re.search(re.escape(API_PREFIX)+r"(.*?)"+re.escape(API_SUFFIX), message)
        if not m: return None
        parts = m.group(1).split(","); kv={}
        for p in parts:
            if p.startswith("=src"): kv['src']=p[4:]
            elif p.startswith("=dst"): kv['dst']=p[4:]
            elif p.startswith("=order"): kv['order']=p[6:]
            elif p.startswith("=f"): kv['f']=p[2:]
            elif p.startswith("=data"): kv['data']=p[5:]
        return APIPayload(**kv)

# --- Task Base & Manager ---
class BaseTask(abc.ABC):
    def __init__(self, task_id: int, name: str): self.id=task_id; self.name=name; self._running=False
    @abc.abstractmethod
    def start(self): pass
    @abc.abstractmethod
    def stop(self): pass
    @abc.abstractmethod
    def status(self)->str: pass
    def info(self)->str: return f"[{self.id}] {self.name} - {self.status()}"

class TaskManager:
    def __init__(self): self.tasks={}
    def register(self, task:BaseTask): self.tasks[task.id]=task; print(f"Registered {task.info()}")
    def start_all(self): [t.start() for t in self.tasks.values()]
    def stop_all(self): [t.stop() for t in self.tasks.values()]
    def show_status(self): [print(t.info()) for t in self.tasks.values()]

# AIモデルの設定クラスを修正
class AIModelConfig:
    """
    AIモデルの設定クラス
    
    Attributes:
        id (str): モデルID
        name (str): モデル名
        provider (Provider): AIプロバイダー
        api_key (str): APIキー
        model_name (str): モデル名（OpenAIのモデル識別子）
    """
    def __init__(self, id: str, name: str, provider: Provider):
        self.id = id
        self.name = name
        self.provider = provider
        self.api_key = get_provider_api_key(provider)
        
        # モデル名の取得と検証
        model_name = os.getenv("MODEL_NAME", "gpt-4.1").strip()  # 余分な空白やコメントを削除
        logger.debug(f"環境変数から取得したモデル名: {model_name}")
        
        # コメントが含まれている場合は削除
        if "#" in model_name:
            model_name = model_name.split("#")[0].strip()
            logger.warning(f"モデル名からコメントを削除しました: {model_name}")
        
        self.model_name = model_name

class AITask(BaseTask):
    def __init__(self, cfg: AIModelConfig):
        super().__init__(int(cfg.id), cfg.name)
        self.cfg = cfg
        self.client = None
        # DBマネージャーをインスタンス化
        self.db_manager = ConversationDBManager()
        self._init_client()

    def _init_client(self):
        """クライアントの初期化"""
        key = self.cfg.api_key
        if not self.cfg.model_name or not key:
            return ErrorHandler.log_error(
                ErrorCode.E50001,
                "APIキーまたはモデル名が設定されていません"
            )
        
        try:
            if self.cfg.provider == Provider.OPENAI:
                self.client = OpenAI(api_key=key)
                print(f"OpenAIクライアントを初期化しました: {self.cfg.model_name}")
            else:
                return ErrorHandler.log_error(
                    ErrorCode.E50003,
                    f"プロバイダー {self.cfg.provider} は未対応です"
                )
        except Exception as e:
            return ErrorHandler.log_error(
                ErrorCode.E50001,
                str(e)
            )

    def start(self):
        self._running = True
        print(f"{self.name}: init (model={self.cfg.model_name})")

    def stop(self):
        self._running = False
        print(f"{self.name}: stopped")

    def status(self) -> str:
        return 'running' if self._running else 'stopped'

    def respond(self, text: str) -> str:
        """AIに対して応答を要求する"""
        try:
            if self.cfg.provider == Provider.OPENAI:
                # 過去の会話履歴を取得して整形
                conversations = self.db_manager.get_all_conversations()
                messages = []
                
                # システムメッセージを追加
                messages.append({
                    "role": "system",
                    "content": "あなたは過去の会話を記憶できるアシスタントです。"
                })
                
                # 過去の会話を追加（最新の5件）
                for conv in conversations[-5:]:
                    # 会話テキストからユーザーとAIの発言を分離
                    if "User:" in conv["text"] and "AI:" in conv["text"]:
                        user_msg, ai_msg = conv["text"].split("AI:", 1)
                        user_content = user_msg.replace("User:", "").strip()
                        ai_content = ai_msg.strip()
                        
                        messages.append({"role": "user", "content": user_content})
                        messages.append({"role": "assistant", "content": ai_content})
                
                # 現在の質問を追加
                messages.append({"role": "user", "content": text})
                
                logger.debug(f"送信するメッセージ履歴: {len(messages)}件")
                
                # OpenAI APIにリクエスト
                response = self.client.chat.completions.create(
                    model=self.cfg.model_name,
                    messages=messages
                )
                
                return response.choices[0].message.content
                
            else:
                return ErrorHandler.log_error(
                    ErrorCode.E50003,
                    f"プロバイダー {self.cfg.provider} は未対応です"
                )
                
        except Exception as e:
            logger.error(f"AI応答生成エラー: {e}")
            return str(e)

class CUIInterfaceTask(BaseTask):
    def __init__(self, ai: AITask):
        """
        CUIInterfaceTaskの初期化メソッド

        @param ai: AITaskのインスタンス
        @type ai: AITask
        """
        super().__init__(IF_CUI, "CUI Interface")
        self.aiTask = ai
        self.db_manager = ConversationDBManager()  # DB管理クラスのインスタンス化

    def start(self):
        """
        CUIインターフェースを開始するメソッド
        'exit'と入力することで終了する
        """
        self._running = True
        print("CUIInterface: enter 'exit' to quit")
        
        while True:
            try:
                inp = input(">> ")
                if inp.strip().lower() == "exit":
                    break

                # プライバシーレベルの入力
                print("プライバシーレベルを選択してください（1:一般, 2:仕事, 3:プライベート, 4:極秘, 5:その他）:")
                privacy_map = {
                    "1": "一般", "2": "仕事", "3": "プライベート",
                    "4": "極秘", "5": "その他"
                }
                privacy_level = privacy_map.get(input("選択: ").strip(), "一般")

                # AIの応答を取得
                response = self.aiTask.respond(inp)
                print("AI:", response)

                # 会話を保存
                self.db_manager.save_conversation(
                    inp, response, tags=[privacy_level]
                )

            except Exception as e:
                print(f"[Error] {e}")
                break
    def stop(self): self._running=False
    def status(self)->str: return 'waiting' if self._running else 'stopped'

def start_django_server():
    """
    Djangoサーバーを起動し、ブラウザで単独ウィンドウを開く関数
    """
    django_path = Path(__file__).parent / 'manage.py'
    try:
        # Djangoサーバーを起動
        subprocess.Popen([sys.executable, str(django_path), 'runserver'])
        logger.info("Djangoサーバーを起動しました")
        
        # 少し待ってからブラウザを起動（サーバーの起動を待つ）
        time.sleep(2)
        
        # ブラウザを新しいウィンドウで開く
        url = "http://localhost:8000/chat/"
        
        if sys.platform == 'win32':
            # Windowsの場合
            try:
                # Chromeで新しいウィンドウを開く
                chrome_path = 'C:/Program Files/Google Chrome/Application/chrome.exe'
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                webbrowser.get('chrome').open_new(url)
            except:
                # Chromeが見つからない場合はデフォルトブラウザで開く
                webbrowser.open_new(url)
        elif sys.platform == 'darwin':
            # macOSの場合
            try:
                # Chromeで開く
                chrome_path = 'open -a /Applications/Google\ Chrome.app %s'
                webbrowser.get(chrome_path).open_new(url)
            except:
                webbrowser.open_new(url)
        else:
            # その他のプラットフォーム
            webbrowser.open_new(url)
            
        logger.info(f"ブラウザを起動しました: {url}")
        
        print("チャットページを開きました。サーバーを停止するには Ctrl+C を押してください。")
        
    except Exception as e:
        error_msg = f"サーバー起動エラー: {e}"
        logger.error(error_msg)
        print(error_msg)

def get_provider_api_key(provider: Provider) -> str:
    """
    指定されたプロバイダーのAPIキーを環境変数から取得
    """
    if provider == Provider.OPENAI:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI APIキーが設定されていません")
            raise ValueError("OpenAIの認証情報が設定されていません")
        logger.debug("OpenAI APIキーが正常に読み込まれました")
        return api_key
    
    logger.error(f"未対応のプロバイダーです: {provider}")
    raise ValueError(f"未対応のプロバイダーです: {provider}")

# AIモデルの設定
AI_MODEL_CONFIGS = [
    AIModelConfig(
        id=str(TASK_AI_RECEIVE),  # "12"
        name="Reception AI",
        provider=Provider.OPENAI
    ),
]

# デバッグ用のログ出力を追加
logger.debug(f"利用可能なAIモデル設定:")
for cfg in AI_MODEL_CONFIGS:
    logger.debug(f"- ID: {cfg.id}, 名前: {cfg.name}, プロバイダー: {cfg.provider}")

# 環境変数の確認関数を修正
def check_environment():
    """環境変数とシステム設定の確認"""
    logger.info("========== 環境変数とシステム設定を確認中 ==========")
    
    # .envファイルの存在確認
    env_path = Path(".env")
    if not env_path.exists():
        logger.error(".envファイルが見つかりません")
        return False
    
    # OpenAI APIキーの確認
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI APIキーが設定されていません")
        return False
    
    # APIキーの形式確認
    if not api_key.startswith("sk-"):
        logger.error("OpenAI APIキーの形式が正しくありません")
        return False
    
    # モデル名の確認と検証
    model_name = os.getenv("MODEL_NAME")
    logger.info(f"設定されているモデル名: {model_name}")
    
    valid_models = [
        "gpt-4-0125-preview",
        "gpt-4-turbo-preview",
        "gpt-4",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo",
    ]
    
    if not model_name:
        logger.warning("MODEL_NAMEが設定されていません。デフォルト値を使用します")
        model_name = "gpt-4-0125-preview"
    
    if model_name not in valid_models:
        logger.warning(
            f"警告: モデル名 '{model_name}' は未検証です\n"
            f"有効なモデル一覧: {', '.join(valid_models)}"
        )
    
    logger.info("==========================================")
    return True

# アプリケーション起動時に環境変数をチェック
if not check_environment():
    logger.error("環境変数の設定に問題があります。.envファイルを確認してください。")
    sys.exit(1)

def get_available_models():
    """
    .envファイルから利用可能なモデル一覧を取得して詳細情報を返す
    
    Returns:
        dict: モデル情報の辞書
        {
            "model_name": {
                "description": "モデルの説明",
                "number": "モデル番号",
                "available": bool,
                "status": "利用可能/利用不可"
            }
        }
    """
    models = {}
    
    # 環境変数からモデル定義を取得
    for key in os.environ:
        if key.startswith("MODEL_"):
            try:
                number = int(key.split("_")[1])
                value = os.getenv(key, "").strip('"')
                if ":" in value:
                    model_name, description = value.split(":", 1)
                    models[model_name.strip()] = {
                        "description": description.strip(),
                        "number": number
                    }
            except (ValueError, IndexError) as e:
                logger.warning(f"モデル定義の解析エラー ({key}): {e}")
    
    if not models:
        logger.warning("モデル定義が見つかりません")
        return {}
    
    # APIキーの取得
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI APIキーが設定されていません")
        return models
    
    # 各モデルの利用可能性をテスト
    logger.info("=== モデル利用可能性テスト ===")
    for model_name in models:
        is_available = test_model_availability(model_name, api_key)
        models[model_name].update({
            "available": is_available,
            "status": "利用可能" if is_available else "利用不可"
        })
        status_mark = "✓" if is_available else "×"
        logger.info(f"[{models[model_name]['number']}] {model_name}: {status_mark}")
    
    return models

def test_model_availability(model_name: str, api_key: str) -> bool:
    """
    指定されたモデルの利用可能性をテスト
    """
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "テスト"}],
            max_tokens=5
        )
        logger.info(f"モデル {model_name} は利用可能です")
        return True
    except Exception as e:
        logger.error(f"モデル {model_name} は利用できません: {str(e)}")
        return False

def main():
    try:
        # HTMLモードを強制的に有効化
        logger.info("HTMLモードで起動します")
        
        # 利用可能なモデル一覧を取得
        available_models = get_available_models()
        if not available_models:
            logger.error("利用可能なモデルが設定されていません")
            sys.exit(1)
        
        # APIキーの取得
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OpenAI APIキーが設定されていません")
            sys.exit(1)
        
        # モデルの利用可能性をテスト
        logger.info("=== モデル利用可能性テスト ===")
        model_status = {}
        for i, model in enumerate(available_models, 1):
            is_available = test_model_availability(model, api_key)
            model_status[model] = is_available
            status = "✓" if is_available else "×"
            logger.info(f"[{i}] {model}: {status}")
        
        # Djangoサーバー起動
        start_django_server()
        
        # サーバープロセスが終了するまで待機
        try:
            while True:
                input("サーバーを停止するには Ctrl+C を押してください...\n")
        except KeyboardInterrupt:
            print("\nサーバーを停止します。")
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
    finally:
        sys.exit(0)

if __name__ == "__main__":
    try:
        logger.info("メモリシステムの初期化を開始")
        db_manager = ConversationDBManager()
        
        # メモリシステムの状態を確認
        memory_status = db_manager.verify_memory_persistence()
        if memory_status:
            logger.info("記憶システムは正常に動作しています")
            logger.info("保存されている会話を確認します")
            conversations = db_manager.get_all_conversations()
            logger.info(f"保存されている会話数: {len(conversations)}")
        else:
            logger.warning("記憶システムに問題が見つかりました")
            
        main()
    except Exception as e:
        logger.error(f"起動時エラー: {e}")
        sys.exit(1)