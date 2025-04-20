"""
エラーコード定義ファイル
"""
from enum import Enum, auto

class ErrorCode(Enum):
    """エラーコードの定義
    
    命名規則:
    E + 分類番号2桁 + 連番3桁
    分類番号:
        10: システム全般
        20: API関連
        30: データベース
        40: ユーザーインターフェース
        50: AI/ML処理
    """
    # システムエラー (E10xxx)
    E10001 = "システム初期化エラー"
    E10002 = "設定ファイル読み込みエラー"
    E10003 = "予期せぬシステムエラー"
    E10004 = "サーバー内部エラー"
    
    # API関連エラー (E20xxx)
    E20001 = "APIキー未設定"
    E20002 = "APIリクエストエラー"
    E20003 = "APIレスポンスエラー"
    E20004 = "API認証エラー"
    
    # AI/ML処理エラー (E50xxx)
    E50001 = "AIクライアント初期化エラー"
    E50002 = "AI応答生成エラー"
    E50003 = "未対応のAIプロバイダー"
    E50004 = "モデル設定エラー"
    
    # ユーザーインターフェースエラー (E40xxx)
    E40001 = "無効な入力"
    E40002 = "必須パラメータの欠落"
    E40003 = "不正なリクエスト形式"

class ErrorHandler:
    """エラーハンドリングクラス"""
    
    @staticmethod
    def log_error(error_code: ErrorCode, detail: str = None) -> str:
        """エラーをログに記録し、エラーメッセージを返す
        
        Args:
            error_code (ErrorCode): エラーコード
            detail (str, optional): 詳細メッセージ
            
        Returns:
            str: フォーマットされたエラーメッセージ
        """
        error_msg = f"[{error_code.name}] {error_code.value}"
        if detail:
            error_msg += f" - {detail}"
            
        # TODO: ログファイルへの書き込み処理を実装
        print(f"Error: {error_msg}")  # 一時的な実装
        
        return error_msg 