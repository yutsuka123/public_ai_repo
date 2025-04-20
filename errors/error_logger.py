"""
エラーログ管理モジュール
"""
import logging
from datetime import datetime
from pathlib import Path

class ErrorLogger:
    """エラーログ管理クラス"""
    
    def __init__(self):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger("error_logger")
        self.logger.setLevel(logging.ERROR)
        
        # ファイルハンドラの設定
        log_file = log_dir / f"error_{datetime.now():%Y%m%d}.log"
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        self.logger.addHandler(handler)
    
    def log(self, error_code, detail=None):
        """エラーをログファイルに記録"""
        msg = f"[{error_code.name}] {error_code.value}"
        if detail:
            msg += f" - {detail}"
        self.logger.error(msg) 