import { defineConfig, globalIgnores } from "eslint/config";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier/flat";

export default defineConfig([
  // 型情報を使うルール。any の受け渡しや、待たれずに捨てられる Promise を検出する
  {
    files: ["**/*.ts"],
    extends: [tseslint.configs.recommendedTypeCheckedOnly],
    languageOptions: { parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname } },
  },
  // 循環的複雑度の上限。超えたら関数を分ける
  { rules: { complexity: ["error", { max: 10 }] } },
  // 書式は Prettier に任せる。最後に置いて書式ルールを無効化する
  prettier,
  // lib/jev.mjs は共通 Jev クライアントの同梱コピー。元と揃えるため検査しない
  globalIgnores(["node_modules/**", "coverage/**", "lib/jev.mjs"]),
]);
