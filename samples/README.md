# サンプルファイル

このディレクトリには、教科書翻訳アプリの開発・テスト用サンプルファイルを格納します。

## ディレクトリ構成

```
samples/
├── pdf/           # サンプルPDFファイル
│   ├── horizontal/  # 横書き教科書サンプル
│   └── vertical/    # 縦書き教科書サンプル
├── json/          # MarkerによるOCR解析結果のJSONサンプル
│   ├── horizontal/  # 横書きJSON（Phase 1開発用）
│   └── vertical/    # 縦書きJSON（Phase 2/3開発用）
└── README.md      # このファイル
```

## JSONサンプルの用途

### Phase 1: 横書き対応
- `json/horizontal/` 内のサンプルを使用
- テキスト抽出ロジックのテスト
- 翻訳フローの検証

### Phase 2: シンプルな縦書き対応
- `json/vertical/single-column/` 内のサンプルを使用
- Few-shot学習のコンテキストとして活用
- 縦書きテキスト抽出の検証

### Phase 3: 複雑な縦書き対応
- `json/vertical/multi-column/` 内のサンプルを使用
- カラム検出アルゴリズムのテスト
- 複雑なレイアウト処理の検証

## サンプルファイルの命名規則

### PDFファイル
- `[書字方向]_[ページ数]p_[説明].pdf`
- 例: `horizontal_10p_math_textbook.pdf`
- 例: `vertical_5p_japanese_literature.pdf`

### JSONファイル
- `[書字方向]_[レイアウト]_[説明].json`
- 例: `horizontal_simple_science.json`
- 例: `vertical_single_column_history.json`
- 例: `vertical_multi_column_newspaper.json`

## JSONファイルの必須フィールド

```json
{
  "pages": [
    {
      "page_number": 1,
      "paragraphs": [
        {
          "direction": "horizontal" | "vertical",
          "box": [x, y, x2, y2],
          "contents": "テキスト内容",
          "role": "section_headings" | "body_text" | "caption"
        }
      ],
      "figures": [
        {
          "box": [x, y, x2, y2],
          "order": 1
        }
      ]
    }
  ]
}
```

## 使用上の注意

1. **著作権**: サンプルファイルは開発・テスト目的のみで使用
2. **個人情報**: 個人を特定できる情報を含むファイルは格納しない
3. **ファイルサイズ**: PDFは最大50MB、JSONは最大10MBまで
4. **バージョン管理**: Gitにコミットする場合は `.gitignore` で除外を検討

## Few-shot学習用サンプル

Phase 2の縦書き対応では、以下のサンプルをFew-shot学習のコンテキストとして使用:

- `json/vertical/osaka_gas_sample.json` - 縦書き構造の標準サンプル
- 最初の1-2ページ分の抽出データを推奨
- Claude APIへのプロンプトに含めて構造理解を促進
