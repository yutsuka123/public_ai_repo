# 2. chat/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
from main import AITask, AI_MODEL_CONFIGS, TASK_AI_RECEIVE, get_available_models, test_model_availability
from core.db_manager import ConversationDBManager
from errors.error_codes import ErrorCode, ErrorHandler
from errors.error_logger import ErrorLogger
import traceback
import sys
import logging.handlers
from pathlib import Path
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# ファイルハンドラの設定
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
file_handler = logging.handlers.RotatingFileHandler(
    log_dir / "chat.log",
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

# AIタスクのグローバルインスタンスを作成
try:
    cfg = next(cfg for cfg in AI_MODEL_CONFIGS if cfg.id == str(TASK_AI_RECEIVE))
    ai_task = AITask(cfg)
    ai_task.start()
    db_manager = ConversationDBManager()
    logger.info("DB初期化成功 - 保存ディレクトリ: ./data/chroma_db")
    
    # 永続性の確認
    if db_manager.verify_memory_persistence():
        logger.info("メモリの永続性が確認できました")
    else:
        logger.warning("メモリの永続性が確認できません")
        
except StopIteration:
    logger.error(f"AI初期化エラー: 設定が見つかりません (TASK_AI_RECEIVE={TASK_AI_RECEIVE})")
    ai_task = None
    db_manager = None
except Exception as e:
    logger.error(f"AI初期化エラー: {str(e)}\n{traceback.format_exc()}")
    ai_task = None
    db_manager = None

# 環境変数の確認
def check_environment():
    """環境変数とシステム設定の確認"""
    logger.info("環境変数とシステム設定を確認中...")
    
    # OpenAI APIキーの確認
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OpenAI APIキーが設定されていません")
        return False
    logger.info("OpenAI APIキーが設定されています")
    
    # モデル名の確認
    model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
    logger.info(f"使用するモデル: {model_name}")
    
    # Pythonパスの確認
    logger.debug(f"Pythonパス: {sys.path}")
    logger.debug(f"現在の作業ディレクトリ: {os.getcwd()}")
    
    return True

# アプリケーション起動時の初期化
if not check_environment():
    logger.error("環境変数の確認に失敗しました")
else:
    logger.info("環境変数の確認が完了しました")

@csrf_exempt
def chat_view(request):
    """チャットビュー
    
    GET: チャット画面の表示
    POST: AIからの応答を取得
    """
    if request.method == 'POST':
        logger.info("POSTリクエスト受信")
        try:
            # リクエストの内容をログ
            logger.debug(f"リクエストボディ: {request.POST}")
            
            message = request.POST.get('message', '')
            logger.info(f"受信メッセージ: {message}")
            
            if not message:
                error_msg = ErrorHandler.log_error(
                    ErrorCode.E40001,
                    "メッセージが空です"
                )
                logger.warning(f"無効な入力: {error_msg}")
                return JsonResponse({
                    'error': error_msg,
                    'error_code': 'E40001'
                }, status=400)

            # AIタスクの状態確認
            if not ai_task:
                error_msg = ErrorHandler.log_error(
                    ErrorCode.E50001,
                    "AIタスクが初期化されていません"
                )
                logger.error(error_msg)
                return JsonResponse({
                    'error': error_msg,
                    'error_code': 'E50001'
                }, status=500)

            # AI応答の生成
            logger.info("AI応答を生成中...")
            response = ai_task.respond(message)
            logger.info(f"AI応答生成完了: {response[:100]}...")  # 最初の100文字のみログ

            # エラーチェック
            if response.startswith('[Error]'):
                error_msg = ErrorHandler.log_error(
                    ErrorCode.E50002,
                    response
                )
                logger.error(f"AI応答エラー: {error_msg}")
                return JsonResponse({
                    'error': error_msg,
                    'error_code': 'E50002'
                }, status=500)

            # 会話の保存（タグの自動判定を利用）
            if db_manager:
                try:
                    logger.info("会話の保存を開始します...")
                    save_success = db_manager.save_conversation(message, response)
                    if save_success:
                        logger.info("会話の保存が完了しました")
                    else:
                        logger.warning("会話の保存に失敗しました")
                except Exception as e:
                    logger.error(f"会話の保存中にエラー: {e}")
                    logger.error(traceback.format_exc())
            else:
                logger.warning("DBマネージャーが初期化されていないため、会話を保存できません")

            return JsonResponse({'response': response})

        except Exception as e:
            error_detail = f"予期せぬエラー:\n{traceback.format_exc()}"
            logger.error(error_detail)
            error_msg = ErrorHandler.log_error(
                ErrorCode.E10003,
                str(e)
            )
            return JsonResponse({
                'error': error_msg,
                'error_code': 'E10003',
                'detail': str(e)
            }, status=500)
    
    # GETリクエストの場合
    logger.info("チャット画面を表示")
    
    # 利用可能なモデル一覧を取得
    available_models = get_available_models()
    model_status = {}
    
    # APIキーの取得
    api_key = os.getenv("OPENAI_API_KEY")
    
    # モデルの利用可能性をテスト
    for i, model in enumerate(available_models, 1):
        is_available = test_model_availability(model, api_key)
        model_status[model] = {
            'number': i,
            'available': 'true' if is_available else 'false',  # JavaScriptのブール値として文字列で渡す
            'status': "利用可能" if is_available else "利用不可"
        }
    
    context = {
        'models': model_status
    }
    return render(request, 'chat/chat.html', context)

@csrf_exempt
def chat_api(request):
    """チャットAPIエンドポイント"""
    if request.method != 'POST':
        return JsonResponse({
            'error': 'POSTメソッドのみ許可されています',
            'error_code': 'E40003'
        }, status=405)

    try:
        # リクエストボディをログに記録
        logger.info(f"リクエストボディ: {request.body.decode('utf-8')}")
        
        data = json.loads(request.body)
        message = data.get('message', '')
        
        if not message:
            return JsonResponse({
                'error': 'メッセージが空です',
                'error_code': 'E40001'
            }, status=400)

        if not ai_task:
            error_msg = ErrorHandler.log_error(
                ErrorCode.E50001,
                "AIシステムが初期化されていません。環境変数を確認してください。"
            )
            return JsonResponse({
                'error': error_msg,
                'error_code': 'E50001',
                'detail': 'OpenAI APIキーと必要な環境変数を確認してください。'
            }, status=500)

        # AIの応答を取得
        response = ai_task.respond(message)
        
        # エラーチェック
        if isinstance(response, str) and response.startswith('[Error]'):
            return JsonResponse({
                'error': response,
                'error_code': 'E50002'
            }, status=500)
        
        # 会話を保存
        if db_manager:
            try:
                logger.info("会話の保存を開始します...")
                save_success = db_manager.save_conversation(message, response)
                if save_success:
                    logger.info("会話の保存が完了しました")
                else:
                    logger.warning("会話の保存に失敗しました")
            except Exception as e:
                logger.error(f"会話の保存中にエラー: {e}")
                logger.error(traceback.format_exc())
        else:
            logger.warning("DBマネージャーが初期化されていないため、会話を保存できません")
        
        return JsonResponse({
            'response': response,
            'status': 'success'
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSONデコードエラー: {str(e)}")
        return JsonResponse({
            'error': '不正なJSONフォーマット',
            'error_code': 'E40003'
        }, status=400)
    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'error': str(e),
            'error_code': 'E10003'
        }, status=500)

@csrf_exempt
def select_model(request):
    """モデル選択APIエンドポイント"""
    if request.method != 'POST':
        return JsonResponse({
            'error': 'POSTメソッドのみ許可されています',
            'error_code': 'E40003'
        }, status=405)

    try:
        data = json.loads(request.body)
        model_name = data.get('model_name')
        
        if not model_name:
            return JsonResponse({
                'error': 'モデル名が指定されていません',
                'error_code': 'E40001'
            }, status=400)

        # セッションにモデル名を保存
        request.session['selected_model'] = model_name
        logger.info(f"モデルを選択: {model_name}")
        
        return JsonResponse({
            'status': 'success',
            'message': f'モデル {model_name} を選択しました'
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSONデコードエラー: {str(e)}")
        return JsonResponse({
            'error': '不正なJSONフォーマット',
            'error_code': 'E40003'
        }, status=400)
    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}\n{traceback.format_exc()}")
        return JsonResponse({
            'error': str(e),
            'error_code': 'E10003'
        }, status=500)

@csrf_exempt
def memory_view(request):
    """記憶の確認・管理画面を表示"""
    if request.method == 'GET':
        # 記憶一覧の取得
        memories = db_manager.get_conversations(
            limit=50,  # デフォルトの表示件数
            offset=int(request.GET.get('offset', 0)),
            privacy_level=request.GET.get('privacy_level'),
            keyword=request.GET.get('keyword'),
            start_date=request.GET.get('start_date'),
            end_date=request.GET.get('end_date')
        )
        return render(request, 'chat/memory.html', {'memories': memories})

@csrf_exempt
def delete_memory(request):
    """選択された記憶を削除"""
    if request.method == 'POST':
        try:
            memory_ids = json.loads(request.body)['memory_ids']
            db_manager.delete_conversations(memory_ids)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"記憶削除エラー: {e}")
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def search_memory(request):
    """会話履歴を検索"""
    try:
        query = request.GET.get('query', '')
        privacy_level = request.GET.get('privacy_level')
        tags = request.GET.getlist('tags[]')
        
        results = db_manager.search_conversations(
            query=query,
            privacy_level=privacy_level,
            tags=tags
        )
        
        return JsonResponse({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"会話履歴の検索に失敗: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
def get_recent_memory(request):
    """最近の会話履歴を取得"""
    try:
        limit = int(request.GET.get('limit', 10))
        privacy_level = request.GET.get('privacy_level')
        
        results = db_manager.get_recent_conversations(
            limit=limit,
            privacy_level=privacy_level
        )
        
        return JsonResponse({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"最近の会話履歴の取得に失敗: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
