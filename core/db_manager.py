from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader
from datetime import datetime
from dotenv import load_dotenv
import os
from core.privacy_analyzer import PrivacyAnalyzer
from typing import List
import logging
import traceback
import chromadb

load_dotenv()  # .envファイルから環境変数を読み込む

logger = logging.getLogger(__name__)

class ConversationDBManager:
    def __init__(self, persist_directory=None):
        """DBマネージャーの初期化"""
        try:
            # 環境変数の検証
            self._verify_environment()
            
            # DBディレクトリの初期化
            self.persist_directory = (
                persist_directory or
                os.getenv('CHROMA_DB_DIR', './data/chroma_db')
            )
            self._initialize_directory()
            self.privacy_analyzer = PrivacyAnalyzer()
            self.text_splitter = CharacterTextSplitter()
            
            # 初期設定の実行
            self._setup_initial_config()
            
        except Exception as e:
            logger.error(f"DB初期化エラー: {e}")
            raise

    def _verify_environment(self):
        """環境変数の検証"""
        required_vars = ["OPENAI_API_KEY", "MODEL_NAME"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"必要な環境変数が設定されていません: {', '.join(missing_vars)}")
            logger.error("1. .env.exampleを.envにコピー")
            logger.error("2. 必要な値を設定してください")
            raise ValueError("環境変数の設定が不完全です")

    def _initialize_directory(self):
        """DBディレクトリの初期化"""
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            logger.info(f"DBディレクトリを初期化: {self.persist_directory}")
            
            # 必要なサブディレクトリの作成
            for subdir in ['collections', 'indexes']:
                os.makedirs(
                    os.path.join(self.persist_directory, subdir),
                    exist_ok=True
                )
                
        except Exception as e:
            logger.error(f"ディレクトリ初期化エラー: {e}")
            raise

    def _setup_initial_config(self):
        """初期設定の実行"""
        try:
            collection_name = os.getenv('CHROMA_COLLECTION_NAME', 'conversations')
            # 新しい PersistentClient API を利用して永続化ディレクトリを指定
            client = chromadb.PersistentClient(path=self.persist_directory)
            self.db = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=OpenAIEmbeddings()
            )
            logger.info(f"ChromaDBコレクションを初期化: {collection_name}")
        except Exception as e:
            logger.error(f"初期設定エラー: {e}")
            raise

    def save_conversation(self, message: str, response: str) -> bool:
        """
        会話を保存する
        
        Args:
            message: ユーザーのメッセージ
            response: AIの応答
        Returns:
            bool: 保存が成功したかどうか
        """
        try:
            # メッセージと応答を結合
            conversation_text = f"User: {message}\nAI: {response}"
            logger.info(f"会話の保存を開始します。テキスト長: {len(conversation_text)}")
            logger.debug(f"会話内容:\n{conversation_text[:200]}...")  # 最初の200文字をログ
            
            # プライバシーレベルの分析
            try:
                privacy_level = self.privacy_analyzer.analyze_privacy_level(conversation_text)
                logger.info(f"プライバシーレベル: {privacy_level}")
            except Exception as e:
                logger.error(f"プライバシー分析でエラー: {str(e)}")
                privacy_level = "low"  # デフォルト値を設定
            
            # Chromaへの保存処理
            try:
                logger.debug("Chromaへの保存を開始")
                self.db.add_texts(
                    texts=[conversation_text],
                    metadatas=[{
                        "privacy_level": privacy_level,
                        "timestamp": datetime.now().isoformat(),
                        "message_length": len(message),
                        "response_length": len(response)
                    }]
                )
                # 永続化は自動で行われるため、manual persist() 呼び出しを削除しました
                logger.info("会話の保存に成功しました")
                return True
                
            except ImportError as e:
                logger.error(f"必要なパッケージが不足しています: {str(e)}")
                logger.error("pip install tiktokenを実行してください")
                return False
            except Exception as e:
                logger.error(f"Chromaへの保存中にエラーが発生: {str(e)}")
                logger.error(f"エラーの詳細: {type(e).__name__}")
                logger.error(f"エラーのトレースバック:\n{traceback.format_exc()}")
                return False
                
        except Exception as e:
            logger.error(f"会話の保存処理中に予期せぬエラーが発生: {str(e)}")
            logger.error(f"エラーの詳細: {type(e).__name__}")
            logger.error(f"エラーのトレースバック:\n{traceback.format_exc()}")
            return False

    def get_all_conversations(self):
        """全ての会話履歴を取得"""
        try:
            # ChromaDBから会話を取得
            results = self.db.get()
            
            if not results or not results['ids']:
                logger.warning("保存されている会話が見つかりません")
                return []
            
            # 会話履歴を整形して返す
            conversations = []
            for i in range(len(results['ids'])):
                conversations.append({
                    "id": results['ids'][i],
                    "text": results['documents'][i],
                    "metadata": results['metadatas'][i]
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"会話履歴の取得に失敗: {e}")
            return []

    def load_knowledge_base(self, directory_path):
        """
        ドキュメントを読み込んでナレッジベースとして保存
        
        Args:
            directory_path (str): ドキュメントが格納されているディレクトリパス
        """
        loader = DirectoryLoader(directory_path, glob="**/*.txt")
        documents = loader.load()
        texts = self.text_splitter.split_documents(documents)
        
        # ナレッジベースとしてマーク
        metadatas = [{"type": "knowledge", "source": doc.metadata["source"]} for doc in texts]
        
        self.db.add_documents(texts, metadatas=metadatas)
        # 永続化は自動で行われるため、manual persist() 呼び出しを削除しました

    def search_conversations(self, query: str, privacy_level: str = None, 
                           tags: List[str] = None, limit: int = 5):
        """
        会話履歴を検索
        
        Args:
            query: 検索クエリ
            privacy_level: プライバシーレベルでフィルタ
            tags: タグでフィルタ
            limit: 返す結果の数
        """
        try:
            # フィルタ条件の構築
            filter_dict = {}
            if privacy_level:
                filter_dict["privacy_level"] = privacy_level
            if tags:
                tag_conditions = [f"tags LIKE '%{tag}%'" for tag in tags]
                filter_dict["$or"] = tag_conditions
            
            # 類似度検索の実行
            results = self.db.similarity_search_with_score(
                query,
                k=limit,
                filter=filter_dict if filter_dict else None
            )
            
            # 結果の整形
            conversations = []
            for doc, score in results:
                conversations.append({
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity_score": score
                })
            
            return conversations
            
        except Exception as e:
            print(f"会話の検索に失敗: {e}")
            raise

    def search_knowledge(self, query, k=5):
        """
        ナレッジベースから関連情報を検索
        """
        results = self.db.similarity_search(
            query,
            k=k,
            filter={"type": "knowledge"}
        )
        return results 

    def get_conversations(self, limit=50, offset=0, privacy_level=None, 
                         keyword=None, start_date=None, end_date=None):
        """
        条件に合う会話履歴を取得
        """
        query = "SELECT * FROM conversations WHERE 1=1"
        params = []
        
        if privacy_level:
            query += " AND privacy_level = ?"
            params.append(privacy_level)
            
        if keyword:
            query += " AND (user_input LIKE ? OR ai_response LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
            
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
            
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        return self.execute_query(query, params)

    def delete_conversations(self, memory_ids):
        """
        指定されたIDの会話を削除
        """
        query = "DELETE FROM conversations WHERE id IN ({})".format(
            ",".join("?" * len(memory_ids))
        )
        self.execute_query(query, memory_ids)

    def get_recent_conversations(self, limit: int = 10, 
                               privacy_level: str = None):
        """
        最近の会話を取得
        """
        try:
            filter_dict = {}
            if privacy_level:
                filter_dict["privacy_level"] = privacy_level
            
            # タイムスタンプでソートして取得
            results = self.db.get(
                limit=limit,
                filter=filter_dict if filter_dict else None,
                sort="timestamp"
            )
            
            return results
            
        except Exception as e:
            print(f"最近の会話の取得に失敗: {e}")
            raise

    def verify_memory_persistence(self):
        """記憶の永続性を確認"""
        try:
            # 保存されている全ての会話を取得
            results = self.db.get()
            
            if not results or not results['ids']:
                logger.warning("保存されている会話が見つかりません")
                return False
            
            logger.info(f"保存されている会話数: {len(results['ids'])}")
            logger.info("最新の会話:")
            
            # 最新の5件を表示
            for i in range(min(5, len(results['ids']))):
                logger.info(f"ID: {results['ids'][i]}")
                logger.info(f"内容: {results['documents'][i][:100]}...")  # 最初の100文字
                logger.info(f"メタデータ: {results['metadatas'][i]}")
                logger.info("---")
            
            return True
            
        except Exception as e:
            logger.error(f"記憶の確認に失敗: {e}")
            return False

print("パッケージのインポートに成功しました")

def start_django_server():
    """
    Djangoサーバーを起動する関数
    """
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'runserver'])
    except Exception as e:
        print(f"サーバー起動エラー: {e}") 