# Python 專屬規則

疊在 SKILL.md 之上；本檔只講 Python 才有的細節。

## 哪些成員算非 private

- 名字不以底線開頭的模組層 function、class、常數，以及 class 裡不以底線開頭的方法與屬性。
- 單底線開頭（`_foo`）視為 private，不寫；雙底線同理。
- 有 `__all__` 時以它為準：列在裡面的一定要寫，沒列的照底線規則。
- dataclass 與 NamedTuple 的每個欄位視為非 private 成員，一行說明即可。

## 外殼

留 docstring（`"""..."""`），放在 `def`／`class` 底下第一行，這是 IDE hover 與 `help()` 唯一會讀的位置。
模組層契約放檔案第一行的模組 docstring。

清掉：`:param:`、`:returns:`、`:raises:`、`Args:`、`Returns:`、`Raises:` 這些 Sphinx／Google 段落，
把內容融進【行為】【會 throw】。型別交給型別註解，不在 docstring 重複。

簡單成員一行 docstring。

## AI-NOTES 標記

`#region AI-NOTES` 到 `#endregion`，井字號後不留空格（VS Code 與 PyCharm 都會折疊，
而且 SKILL.md 那條剝區塊的 sed 認得 `#region`）。
內容一律 `#` 行註解，放在檔案最後、`if __name__ == "__main__":` 之後。

## 驗證

`python3 -m py_compile <檔>`；有型別註解的專案再跑 `pyright` 或 `mypy`。
