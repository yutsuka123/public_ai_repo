# 3. chat/tasks.py
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# main.pyから直接インポート
from main import AITask, AI_MODEL_CONFIGS, TASK_AI_RECEIVE

# Reception AI の設定を取得（エラーハンドリング付き）
try:
    cfg = next(cfg for cfg in AI_MODEL_CONFIGS if cfg.id == str(TASK_AI_RECEIVE))
    ai_receive_task = AITask(cfg)
    ai_receive_task.start()
except StopIteration:
    print(f"エラー: TASK_AI_RECEIVE({TASK_AI_RECEIVE})の設定が見つかりません")
    sys.exit(1)
except Exception as e:
    print(f"エラー: Reception AIの初期化に失敗しました - {e}")
    sys.exit(1)

def process_message(message: str) -> str:
    """
    メッセージを処理してAIの応答を返す
    """
    try:
        # AIモデルの設定
        ai_config = AIModelConfig(
            id=str(TASK_AI_RECEIVE),
            name="Reception AI",
            provider=Provider.OPENAI
        )
        
        # AIタスクの初期化
        ai_task = AITask(ai_config)
        
        # 応答の生成
        response = ai_task.respond(message)
        return response
        
    except Exception as e:
        logger.error(f"メッセージ処理中にエラーが発生: {e}")
        return f"エラーが発生しました: {str(e)}"