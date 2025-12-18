# Obsidian LLM Session Plugin

Claude Code用のプラグインで、Obsidian Vault内でのLLMセッション管理を効率化します。

## 機能

### スキル

| スキル | 説明 |
|--------|------|
| **session-logger** | セッション内容をLLM/ディレクトリに保存 |
| **context-reader** | contexts/ディレクトリからプロジェクト状況を把握 |
| **research-workflow** | Context7 MCPを優先した調査ワークフロー |

### コマンド

| コマンド | 説明 |
|----------|------|
| `/save-session` | 現在のセッションを保存 |
| `/update-context` | 重要な決定事項をcontextsに記録 |

## インストール

```bash
# マーケットプレイスを追加
/plugin marketplace add oratta/obsidian-llm-session-plugin

# プラグインをインストール
/plugin install obsidian-llm-session-rules@oratta
```

## 使い方

### セッション開始時

プラグインがcontexts/ディレクトリを自動で読み込み、プロジェクトの現状を把握します。

### 調査時

技術的な調査はContext7 MCPを最優先で使用します。見つからない場合のみWeb検索を使用。

### セッション終了時

```
/save-session
```

または「このセッションを保存して」と伝えると、LLM/ディレクトリに会話ログを保存します。

### 重要な決定をした時

```
/update-context
```

または「コンテキストを更新して」と伝えると、contexts/ディレクトリに記録します。

## ディレクトリ構造

```
your-vault/
├── LLM/                    # セッションログ保存先
│   └── 2025-01-15_1430_機能追加.md
├── docs/contexts/          # プロジェクトコンテキスト
│   ├── prd.md
│   └── 決定事項.md
└── ...
```

## ライセンス

MIT
