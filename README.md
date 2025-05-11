public_ai_repo



If you find this project useful, please consider giving it a star.

Overview (EN)

public_ai_repo is a lightweight playground for experimenting with OpenAI / LangChain‑powered multimodal agents on both edge devices and the cloud. The goal is to provide a minimal yet extensible scaffold that lets you prototype conversational or tool‑using agents in minutes and then deploy them to resource‑constrained hardware such as the ESP32.

Key Features

Agents: conversational, tool‑calling, streaming responses

Embeddings: adapters for FAISS and Qdrant

Integrations: MQTT, WebSocket, FastAPI, SQLite persistence

Developer productivity: Ruff + Black formatters, pytest, GitHub Actions CI

Quick Start

# Clone the repository
git clone https://github.com/yutsuka123/public_ai_repo.git
cd public_ai_repo

# Install dependencies (Poetry recommended)
poetry install --with dev

# Run a simple chat CLI
poetry run python -m ai_repo.cli

Project Structure

public_ai_repo/
 ├─ ai_repo/            # Core library
 │   ├─ agents/         # Agent logic
 │   ├─ providers/      # Model back‑ends (OpenAI, Ollama, etc.)
 │   ├─ interfaces/     # CLI, REST, MQTT adapters
 │   └─ utils/          # Shared helpers
 ├─ examples/           # Sample notebooks and scripts
 ├─ tests/              # pytest test‑suite
 └─ scripts/            # Utility scripts

Roadmap

Replace custom queue with asyncio.TaskGroup

Add a speech‑to‑text endpoint (Whisper or Vosk)

Publish a Docker image for quick trials

Provide an ESP‑IDF component example

public_ai_repo（日本語）

概要（JP）

public_ai_repo は OpenAI / LangChain を活用したマルチモーダル・エージェント を、クラウドとエッジ双方で手軽に試すための軽量プレイグラウンドです。会話型エージェントやツール呼び出しエージェントを数分でプロトタイプし、ESP32 などのリソース制約環境へ展開することを目指しています。

主な特徴

エージェント: 会話型、ツール呼び出し、ストリーミング応答

ベクトル検索: FAISS / Qdrant アダプタ

連携: MQTT、WebSocket、FastAPI、SQLite 永続化

開発体験: Ruff・Black フォーマッタ、pytest、GitHub Actions CI

クイックスタート

# リポジトリをクローン
git clone https://github.com/yutsuka123/public_ai_repo.git
cd public_ai_repo

# 依存関係をインストール（Poetry 推奨）
poetry install --with dev

# チャット CLI を起動
poetry run python -m ai_repo.cli

ディレクトリ構成

public_ai_repo/
 ├─ ai_repo/            # コアライブラリ
 │   ├─ agents/         # エージェントロジック
 │   ├─ providers/      # モデルバックエンド（OpenAI, Ollama など）
 │   ├─ interfaces/     # CLI・REST・MQTT アダプタ
 │   └─ utils/          # 共有ヘルパー
 ├─ examples/           # サンプルノートブック・スクリプト
 ├─ tests/              # pytest テストスイート
 └─ scripts/            # ユーティリティスクリプト

今後の展望

独自キューを asyncio.TaskGroup に置き換え

音声入力（Whisper / Vosk）エンドポイントの追加

動作確認用 Docker イメージの配布

ESP‑IDF コンポーネント例の提供

## Considerations for Future Implementation / 今後の検討事項

| Purpose / 目的 | Recommended Tools / 推奨ツール／ライブラリ | Notes / 補足 |
|---|---|---|
| RAG-style AI Generation / RAG 型生成 AI | Vector DB: pgvector (PostgreSQL 16) or Pinecone<br>Embeddings: OpenAI API / Sentence-Transformers | Integratable directly from Django + LangChain<br>Django + LangChain から直接呼び出せる |
| API Layer Separation / API レイヤ分離 | FastAPI (see §3) | Divide roles: Django for frontend & admin, FastAPI for lightweight API for easier maintenance<br>Django ＝フロント & 管理、FastAPI ＝軽量 API と役割分担すると保守が楽 |
| Asynchronous Tasks / 非同期タスク | Celery + Redis / RabbitMQ | Execute chat responses and embedding generation in background<br>チャット応答や埋め込み生成をバックグラウンド実行 |
| Messaging / メッセージング | Apache Kafka / Amazon SQS | Scales well with increasing users<br>ユーザ数が増えてもスケールしやすい |
| Environment Management / 環境管理 | Poetry (dependency resolution)<br>Docker Compose (development) | Deployable to ECS Fargate / Kubernetes in production<br>本番は ECS Fargate / Kubernetes へそのまま載せ換え可 |
| Testing / テスト | PyTest + Coverage<br>Playwright (E2E) | Automatic testing of generative AI using "golden answer" approach<br>生成 AI 部は「ゴールデン回答」方式で自動テスト |
| Monitoring & Logging / 監視 & ログ | OpenTelemetry + Prometheus + Grafana | Visualize OpenAI usage and latency<br>OpenAI の usage/latency を可視化 |

License

This project is licensed under the MIT License. See the LICENSE file for details.