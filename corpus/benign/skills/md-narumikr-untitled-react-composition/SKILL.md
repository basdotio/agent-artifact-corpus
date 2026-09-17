---
name: react-composition
description:
  スケールするReactコンポジションパターン。多数のブールpropを持つコンポーネントのリファクタリング、柔軟なコンポーネントライブラリの構築、再利用可能なAPIの設計に使用する。Compound components、render props、コンテキストプロバイダー、またはコンポーネントアーキテクチャに関するタスクで起動する。React 19 APIの変更を含む。
---

# React Composition Patterns

柔軟でメンテナブルなReactコンポーネントを構築するためのコンポジションパターン。Compound
componentsの使用、stateのリフトアップ、内部のコンポジションにより、ブールpropの増殖を避ける。これらのパターンはコードベースのスケールに伴い、人間とAIエージェントの両方が扱いやすくなる。

## 適用タイミング

以下の場合にこのガイドラインを参照する：

- 多数のブールpropを持つコンポーネントのリファクタリング
- 再利用可能なコンポーネントライブラリの構築
- 柔軟なコンポーネントAPIの設計
- コンポーネントアーキテクチャのレビュー
- Compound componentsやコンテキストプロバイダーの利用

## ルールカテゴリ（優先度順）

| 優先度 | カテゴリ                  | 影響度 | プレフィックス  |
| ------ | ------------------------- | ------ | --------------- |
| 1      | Component Architecture    | HIGH   | `architecture-` |
| 2      | State Management          | MEDIUM | `state-`        |
| 3      | Implementation Patterns   | MEDIUM | `patterns-`     |
| 4      | React 19 APIs             | MEDIUM | `react19-`      |

## クイックリファレンス

### 1. Component Architecture（HIGH）

- `architecture-avoid-boolean-props` - 振る舞いのカスタマイズにブールpropを追加しない；コンポジションを使う
- `architecture-compound-components` - 共有コンテキストで複雑なコンポーネントを構造化する

### 2. State Management（MEDIUM）

- `state-decouple-implementation` - プロバイダーだけがstateの管理方法を知っている唯一の場所
- `state-context-interface` - 依存性注入のためにstate、actions、metaを持つジェネリックインターフェースを定義する
- `state-lift-state` - 兄弟コンポーネントからのアクセスのためにstateをプロバイダーに移動する

### 3. Implementation Patterns（MEDIUM）

- `patterns-explicit-variants` - ブールモードの代わりに明示的なバリアントコンポーネントを作成する
- `patterns-children-over-render-props` - renderXプロップの代わりにchildrenでコンポジションを行う
- `patterns-polymorphic-as-prop` - ポリモーフィックコンポーネント用に`as`プロップで異なる要素としてレンダリングする
- `patterns-slot-pattern` - ラッパーなしのコンポジションのためにSlot/asChildでpropsを子要素にマージする
- `patterns-controlled-uncontrolled` - 最大の再利用性のためにcontrolledとuncontrolledの両モードをサポートする

### 4. React 19 APIs（MEDIUM）

> **⚠️ React 19以降のみ。** React 18以前を使用している場合はこのセクションをスキップする。

- `react19-api-changes` - `forwardRef`を使わない；`useContext()`の代わりに`use()`を使う

## 使い方

詳細な説明とコード例は個別のリファレンスファイルを参照する：

```
references/architecture-avoid-boolean-props.md
references/state-context-interface.md
```

各リファレンスファイルには以下が含まれる：

- なぜ重要かの簡単な説明
- 誤ったコード例と説明
- 正しいコード例と説明
- 追加コンテキストと参考資料

## 詳細リファレンス

- **Component Architecture**: `references/architecture-avoid-boolean-props.md`, `references/architecture-compound-components.md`
- **State Management**: `references/state-decouple-implementation.md`, `references/state-context-interface.md`, `references/state-lift-state.md`
- **Implementation Patterns**: `references/patterns-explicit-variants.md`, `references/patterns-children-over-render-props.md`, `references/patterns-polymorphic-as-prop.md`, `references/patterns-slot-pattern.md`, `references/patterns-controlled-uncontrolled.md`
- **React 19**: `references/react19-api-changes.md`
- **Anti-patterns**: `references/anti-patterns.md`

## 例

- **Before/After比較**: `examples/before-after-examples.md`
  - モノリシックコンポーネントからCompound componentsへ
  - ブールpropから明示的バリアントへ
  - プロップドリリングからプロバイダーベースのstateへ
  - Render propsからchildrenコンポジションへ
- **デザインシステムパターン**: `examples/design-system-patterns.md`
  - ポリモーフィックTextコンポーネント
  - Slotトリガーを持つDialog
  - Controlled/Uncontrolled Tabs
  - Compound + Slot + Controlledパターンの組み合わせ
