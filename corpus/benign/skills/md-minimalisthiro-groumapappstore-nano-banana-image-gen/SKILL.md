---
name: nano-banana-image-gen
description: 「画像を生成して」「画像を作って」「アイコンを作って」「バナーを作って」など、画像生成の依頼時に、Nano Banana 2（Gemini 3.1 Flash Image）APIを使って画像を自動生成する。
---

# Nano Banana 2 画像生成スキル

## 目的

ユーザーから画像生成を依頼されたときに、Nano Banana 2（Gemini 3.1 Flash Image）APIを使って自動的に画像を生成する。

## 生成手順の参照

具体的な画像生成の手順（コマンド実行方法・保存先・アスペクト比の決定方法）は、以下のファイルを Read ツールで読み込んでから実行してください：

`/Users/kanekohiroki/Desktop/groumapapp_store/.claude/skills/nano-banana-image-gen/HOW_TO_GENERATE.md`

## 「画像を生成して」のデフォルトスタイル

ユーザーが「画像を生成して」「画像を作って」と依頼した場合（ロゴ・アイコン・バナーなどの具体的な種別指定がない場合）、以下のスタイルをプロンプトに必ず含める：

- **スタイル**: ビジネス系フラットベクターイラスト（clean flat vector business illustration）
- **線画**: クリーンでシンプルな線（clean simple outlines）
- **配色**: 落ち着いたブルー、グレー、ホワイト基調（muted blue, gray, and white color palette）
- **人物**: 適度にデフォルメされたビジネスパーソン（stylized business people）
- **背景**: 白またはシンプルな背景（white or simple clean background）
- **全体の雰囲気**: プロフェッショナルで清潔感のあるビジネスイラスト

プロンプト例:
`"Clean flat vector business illustration of [シーンの内容], stylized business people, muted blue gray and white color palette, simple clean outlines, white background, professional corporate style, no gradients, minimal shading"`

**適用条件**:
- 適用する: 「画像を生成して」「画像を作って」「〇〇の画像を生成して」など、画像の種別指定がない汎用的な依頼
- 適用しない: 「ロゴを作って」「アイコンを作って」「バナーを作って」「写真風に」「水彩画で」など、具体的な種別やスタイル指定がある依頼

## プロンプト作成のコツ

- スタイルを明示する（例: "flat design", "minimalist", "photorealistic", "watercolor"）
- 色を指定する（例: "blue and white color scheme"）
- 背景を指定する（例: "on a transparent background", "white background"）
- テキストを含める場合は引用符で囲む（例: 'with the text "GrouMap"'）
