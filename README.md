# AI支援型マルチタスク対話システム

## 概要
このシステムは、複数のAIプロバイダー（OpenAI、Claude、Google AI）を利用した対話システムです。
CUI、HTML、音声の3つのインターフェースをサポートしています。

## 環境構築

### 必要条件
- Python 3.8以上
- pip（Pythonパッケージマネージャー）

### セットアップ手順

1. リポジトリのクローン
```bash
git clone <repository-url>
cd <repository-name>
```

2. 仮想環境の作成と有効化
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Unix/MacOS
source venv/bin/activate
```

3. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

4. 環境変数の設定
- `.env.example`ファイルを`.env`にコピー
```bash
cp .env.example .env
```
- `.env`ファイルを編集し、必要なAPIキーを設定

5. アプリケーションの起動
```bash
python main.py
```

初回起動時に必要なディレクトリとDBが自動的に作成されます。

## 使用方法
起動時に以下のインターフェースから選択できます：
- CUI: コマンドライン対話モード
- HTML: Webブラウザベースの対話モード
- 音声: 音声インターフェース（現在開発中）

## 注意事項
- `.env`ファイルは決してGitHubにコミットしないでください
- APIキーは適切に管理し、公開しないように注意してください

## セキュリティ注意事項

- 本リポジトリをクローンして使用する際は、必ず`.env.example`を参考に`.env`ファイルを作成してください
- APIキーなどの機密情報は`.env`ファイルに保存し、決してGitHubにコミットしないでください
- `data/chroma_db/`ディレクトリは自動的に作成されます 