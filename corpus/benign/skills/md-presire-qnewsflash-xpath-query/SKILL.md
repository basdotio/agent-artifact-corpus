# XPath Query Skill

qNewsFlash プロジェクトのための XPath/Web スクレイピングスキル。
libxml2 を用いたニュースサイト解析のベストプラクティスを提供。

---

## 概要

このスキルは、qNewsFlash がニュースサイトから
記事を抽出するための XPath クエリ技術をカバーします。

**対象ライブラリ**: libxml2 2.10+ / libxml2 2.12+
**XPath バージョン**: XPath 1.0 (libxml2 標準)

---

## XPath 1.0 基礎

### ロケーションパス

```
/           - ルートから開始
//          - 任意の深さ
.           - 現在のノード
..          - 親ノード
@           - 属性
*           - 任意の要素
@*          - 任意の属性
node()      - 任意のノード
```

### 述語 (Predicates)

```xpath
//div[@class='news']           # class属性が'news'のdiv
//li[1]                        # 最初のli要素
//li[last()]                   # 最後のli要素
//li[position() < 3]           # 最初の2つのli要素
//a[contains(@href, 'news')]   # href属性に'news'を含むa要素
//p[text()='Breaking']         # テキストが'Breaking'のp要素
//div[@class!='hidden']        # class属性が'hidden'でないdiv
```

### 関数

```xpath
# 文字列関数
text()                         # テキストノード
contains(s1, s2)               # s1がs2を含む
starts-with(s1, s2)            # s1がs2で始まる
ends-with(s1, s2)              # s1がs2で終わる (XPath 2.0 - libxml2では使用不可)
normalize-space(s)             # 空白を正規化
string-length(s)               # 文字列長
concat(s1, s2, ...)            # 文字列結合
substring(s, start, len)       # 部分文字列
translate(s, from, to)         # 文字置換

# 数値関数
count(node-set)                # ノード数
sum(node-set)                  # 合計値
number(value)                  # 数値変換

# ブール関数
not(boolean)                   # 否定
true(), false()                # 真偽値
```

---

## 高度な XPath パターン

### 軸 (Axes)

```xpath
# 子孫軸
//div/descendant::p            # div内の全てのp (//div//p と同等)
//div/descendant-or-self::*    # div自身とその子孫すべて

# 祖先軸
//p/ancestor::div              # pの祖先であるdiv
//p/ancestor-or-self::div      # p自身または祖先のdiv

# 兄弟軸
//h1/following-sibling::p      # h1の後ろにある兄弟p要素
//h2/preceding-sibling::p      # h2の前にある兄弟p要素

# その他
//div/following::*             # 文書順でdivより後の全要素
//div/preceding::*             # 文書順でdivより前の全要素
//p/parent::div                # pの親div
//div/child::p                 # divの直接の子p
```

### Union (和集合)

```xpath
# 複数のパスを結合
//h1/text() | //h2/text()      # h1またはh2のテキスト
//div[@class='news'] | //div[@class='flash']
//meta[@name='title'] | //title
```

### 条件分岐

```xpath
# contains と starts-with の組み合わせ
//a[starts-with(@href, 'https') and contains(@href, 'news')]

# 複数クラスの一致
//div[contains(@class, 'news') and contains(@class, 'breaking')]

# テキスト内容でのフィルタリング
//li[contains(., '速報')]      # テキストに'速報'を含むli

# 否定条件
//div[not(contains(@class, 'hidden'))]
//a[not(starts-with(@href, '#'))]
```

### 属性値の操作

```xpath
# 複数属性の取得
//img/@src | //img/@alt

# 属性値の部分一致
//a[contains(@href, 'article')]
//a[starts-with(@href, '/news/')]

# 属性の存在確認
//div[@data-id]                # data-id属性を持つdiv
//a[not(@rel)]                 # rel属性を持たないa
```

---

## RSS/Atom フィード対応

### RSS 2.0

```xpath
# チャンネル情報
/channel/title/text()
/channel/link/text()
/channel/description/text()
/channel/lastBuildDate/text()

# アイテム一覧
/channel/item
/channel/item/title/text()
/channel/item/link/text()
/channel/item/description/text()
/channel/item/pubDate/text()
/channel/item/category/text()
/channel/item[enclosure]       # 添付ファイルを持つアイテム
```

### RSS 1.0 (RDF)

```xpath
# 名前空間が必要な場合
/rdf:RDF/channel/title
/rdf:RDF/item/title
/rdf:RDF/item/link

# デフォルト名前空間なし
//channel/title
//item/title
```

### Atom

```xpath
# フィード情報
/feed/title/text()
/feed/subtitle/text()
/feed/updated/text()

# エントリ一覧
/feed/entry
/feed/entry/title/text()
/feed/entry/link/@href
/feed/entry/content/text()
/feed/entry/summary/text()
/feed/entry/published/text()
/feed/entry/updated/text()
/feed/entry/author/name/text()
```

### qNewsFlash での RSS 処理例

```cpp
QStringList parseRssItems(htmlDocPtr doc) {
    QStringList items;
    xmlXPathContextPtr ctx = xmlXPathNewContext(doc);
    
    // RSS 2.0 を試行
    xmlXPathObjectPtr result = xmlXPathEvalExpression(
        BAD_CAST "//item", ctx
    );
    
    if (result && result->nodesetval && result->nodesetval->nodeNr > 0) {
        for (int i = 0; i < result->nodesetval->nodeNr; i++) {
            xmlNodePtr item = result->nodesetval->nodeTab[i];
            
            // コンテキストをアイテムに設定
            xmlXPathSetContextNode(item, ctx);
            
            // タイトル取得
            xmlXPathObjectPtr titleResult = xmlXPathEvalExpression(
                BAD_CAST "title/text()", ctx
            );
            if (titleResult && titleResult->stringval) {
                items << QString::fromUtf8((char*)titleResult->stringval);
            }
            xmlXPathFreeObject(titleResult);
        }
    }
    
    xmlXPathFreeObject(result);
    xmlXPathFreeContext(ctx);
    return items;
}
```

---

## libxml2 実装

### ヘッダファイル

```cpp
#include <libxml/parser.h>
#include <libxml/xpath.h>
#include <libxml/HTMLparser.h>
#include <libxml/HTMLtree.h>
#include <libxml/encoding.h>
#include <libxml/xmlstring.h>
```

### 初期化とクリーンアップ

```cpp
// アプリケーション開始時に1回呼ぶ
void initLibXml2() {
    xmlInitParser();
    LIBXML_TEST_VERSION;  // バージョンチェック
}

// アプリケーション終了時に1回呼ぶ
void cleanupLibXml2() {
    xmlCleanupParser();
    xmlMemoryDump();  // デバッグ用: メモリリーク確認
}
```

### HTML パース (推奨: htmlReadMemory)

```cpp
// 推奨: htmlReadMemory はエンコーディング自動検出あり
htmlDocPtr parseHtml(const QString &html, const QString &url = "") {
    htmlDocPtr doc = htmlReadMemory(
        html.toUtf8().constData(),
        html.toUtf8().size(),
        url.toUtf8().constData(),
        "UTF-8",
        HTML_PARSE_RECOVER |      // エラー回復
        HTML_PARSE_NOERROR |      // エラーメッセージ抑制
        HTML_PARSE_NOWARNING |    // 警告抑制
        HTML_PARSE_NONET          // ネットワークアクセス禁止
    );
    return doc;
}

// 旧方式: htmlParseMemory (エンコーディング検出なし)
htmlDocPtr parseHtmlLegacy(const QString &html) {
    htmlDocPtr doc = htmlParseMemory(
        html.toUtf8().constData(),
        html.toUtf8().size()
    );
    return doc;
}
```

### XML パース (RSS 用)

```cpp
xmlDocPtr parseXml(const QString &xml, const QString &url = "") {
    xmlDocPtr doc = xmlReadMemory(
        xml.toUtf8().constData(),
        xml.toUtf8().size(),
        url.toUtf8().constData(),
        "UTF-8",
        XML_PARSE_RECOVER |
        XML_PARSE_NOERROR |
        XML_PARSE_NOWARNING
    );
    return doc;
}
```

### XPath 評価 (単一値)

```cpp
QString evaluateXPath(htmlDocPtr doc, const QString &xpath) {
    if (!doc) return QString();
    
    xmlXPathContextPtr ctx = xmlXPathNewContext(doc);
    if (!ctx) return QString();
    
    QString value;
    xmlXPathObjectPtr result = xmlXPathEvalExpression(
        BAD_CAST xpath.toUtf8().constData(), ctx
    );
    
    if (result) {
        if (result->type == XPATH_NODESET &&
            result->nodesetval &&
            result->nodesetval->nodeNr > 0) {
            // ノードセットからコンテンツ取得
            xmlChar *content = xmlNodeGetContent(
                result->nodesetval->nodeTab[0]
            );
            if (content) {
                value = QString::fromUtf8((char*)content);
                xmlFree(content);
            }
        } else if (result->type == XPATH_STRING) {
            // 文字列として直接結果
            value = QString::fromUtf8((char*)result->stringval);
        }
        xmlXPathFreeObject(result);
    }
    
    xmlXPathFreeContext(ctx);
    return value;
}
```

### XPath 評価 (複数値)

```cpp
QStringList evaluateXPathMultiple(htmlDocPtr doc, const QString &xpath) {
    if (!doc) return QStringList();
    
    xmlXPathContextPtr ctx = xmlXPathNewContext(doc);
    if (!ctx) return QStringList();
    
    QStringList values;
    xmlXPathObjectPtr result = xmlXPathEvalExpression(
        BAD_CAST xpath.toUtf8().constData(), ctx
    );
    
    if (result && result->type == XPATH_NODESET && result->nodesetval) {
        for (int i = 0; i < result->nodesetval->nodeNr; i++) {
            xmlChar *content = xmlNodeGetContent(
                result->nodesetval->nodeTab[i]
            );
            if (content) {
                values << QString::fromUtf8((char*)content);
                xmlFree(content);
            }
        }
    }
    
    xmlXPathFreeObject(result);
    xmlXPathFreeContext(ctx);
    return values;
}
```

### 属性値取得

```cpp
QString evaluateXPathAttribute(htmlDocPtr doc, const QString &xpath) {
    if (!doc) return QString();
    
    xmlXPathContextPtr ctx = xmlXPathNewContext(doc);
    if (!ctx) return QString();
    
    QString value;
    xmlXPathObjectPtr result = xmlXPathEvalExpression(
        BAD_CAST xpath.toUtf8().constData(), ctx
    );
    
    if (result && result->type == XPATH_NODESET && 
        result->nodesetval && result->nodesetval->nodeNr > 0) {
        xmlNodePtr node = result->nodesetval->nodeTab[0];
        if (node->type == XML_ATTRIBUTE_NODE) {
            xmlChar *attrValue = xmlNodeGetContent(node);
            if (attrValue) {
                value = QString::fromUtf8((char*)attrValue);
                xmlFree(attrValue);
            }
        }
    }
    
    xmlXPathFreeObject(result);
    xmlXPathFreeContext(ctx);
    return value;
}
```

### 相対 XPath 評価

```cpp
QString evaluateRelativeXPath(xmlXPathContextPtr ctx, xmlNodePtr node, 
                              const QString &xpath) {
    QString value;
    xmlXPathSetContextNode(node, ctx);
    
    xmlXPathObjectPtr result = xmlXPathEvalExpression(
        BAD_CAST xpath.toUtf8().constData(), ctx
    );
    
    if (result && result->nodesetval && result->nodesetval->nodeNr > 0) {
        xmlChar *content = xmlNodeGetContent(result->nodesetval->nodeTab[0]);
        if (content) {
            value = QString::fromUtf8((char*)content);
            xmlFree(content);
        }
    }
    
    xmlXPathFreeObject(result);
    return value;
}
```

### 完全な実装例: ニュース抽出

```cpp
struct NewsItem {
    QString title;
    QString url;
    QString date;
    QString description;
};

QList<NewsItem> extractNews(htmlDocPtr doc, const QJsonObject &config) {
    QList<NewsItem> items;
    if (!doc) return items;
    
    QString listXpath = config["flashxpath"].toString();
    QString titleXpath = config["titlexpath"].toString();
    QString urlXpath = config["urlxpath"].toString();
    QString dateXpath = config["datexpath"].toString();
    QString descXpath = config["paraxpath"].toString();
    
    xmlXPathContextPtr ctx = xmlXPathNewContext(doc);
    if (!ctx) return items;
    
    // リストアイテムを取得
    xmlXPathObjectPtr listResult = xmlXPathEvalExpression(
        BAD_CAST listXpath.toUtf8().constData(), ctx
    );
    
    if (listResult && listResult->nodesetval) {
        for (int i = 0; i < listResult->nodesetval->nodeNr; i++) {
            xmlNodePtr itemNode = listResult->nodesetval->nodeTab[i];
            NewsItem item;
            
            // 相対XPathで各フィールドを取得
            xmlXPathSetContextNode(itemNode, ctx);
            
            xmlXPathObjectPtr titleResult = xmlXPathEvalExpression(
                BAD_CAST titleXpath.toUtf8().constData(), ctx
            );
            if (titleResult && titleResult->stringval) {
                item.title = QString::fromUtf8((char*)titleResult->stringval);
            }
            xmlXPathFreeObject(titleResult);
            
            xmlXPathObjectPtr urlResult = xmlXPathEvalExpression(
                BAD_CAST urlXpath.toUtf8().constData(), ctx
            );
            if (urlResult && urlResult->nodesetval && 
                urlResult->nodesetval->nodeNr > 0) {
                xmlChar *url = xmlNodeGetContent(urlResult->nodesetval->nodeTab[0]);
                if (url) {
                    item.url = QString::fromUtf8((char*)url);
                    xmlFree(url);
                }
            }
            xmlXPathFreeObject(urlResult);
            
            // 日時と説明も同様に取得...
            if (!dateXpath.isEmpty()) {
                item.date = evaluateRelativeXPath(ctx, itemNode, dateXpath);
            }
            if (!descXpath.isEmpty()) {
                item.description = evaluateRelativeXPath(ctx, itemNode, descXpath);
            }
            
            items.append(item);
        }
    }
    
    xmlXPathFreeObject(listResult);
    xmlXPathFreeContext(ctx);
    return items;
}
```

### RAII ラッパー

```cpp
class XmlDocGuard {
public:
    explicit XmlDocGuard(htmlDocPtr doc) : m_doc(doc) {}
    ~XmlDocGuard() { if (m_doc) xmlFreeDoc(m_doc); }
    
    htmlDocPtr get() const { return m_doc; }
    operator bool() const { return m_doc != nullptr; }
    
private:
    htmlDocPtr m_doc;
    Q_DISABLE_COPY(XmlDocGuard)
};

class XPathContextGuard {
public:
    explicit XPathContextGuard(xmlXPathContextPtr ctx) : m_ctx(ctx) {}
    ~XPathContextGuard() { if (m_ctx) xmlXPathFreeContext(m_ctx); }
    
    xmlXPathContextPtr get() const { return m_ctx; }
    operator bool() const { return m_ctx != nullptr; }
    
private:
    xmlXPathContextPtr m_ctx;
    Q_DISABLE_COPY(XPathContextGuard)
};

// 使用例
void processHtml(const QString &html) {
    XmlDocGuard doc(parseHtml(html));
    if (!doc) return;
    
    XPathContextGuard ctx(xmlXPathNewContext(doc.get()));
    if (!ctx) return;
    
    QString title = evaluateXPath(doc.get(), "//title/text()");
    qDebug() << "Title:" << title;
}
```

---

## エンコーディング処理

### 文字コード変換フロー

```
Webサイト (Shift-JIS/EUC-JP等)
    ↓ HTTP レスポンス
QByteArray (生データ)
    ↓ QString::fromUtf8() または QTextCodec
QString (UTF-16)
    ↓ toUtf8()
QByteArray (UTF-8)
    ↓ libxml2
パース処理
```

### 日本語サイト対応

```cpp
// 文字コード検出
QString detectEncoding(const QByteArray &data, const QString &contentType) {
    // Content-Type ヘッダから検出
    if (contentType.contains("charset=", Qt::CaseInsensitive)) {
        int pos = contentType.indexOf("charset=", 0, Qt::CaseInsensitive);
        QString charset = contentType.mid(pos + 8).split(';').first().trimmed();
        return charset.toUpper();
    }
    
    // HTML meta タグから検出
    QString html = QString::fromUtf8(data);
    QRegularExpression re("<meta[^>]+charset=[\"']?([^\"'\\s>]+)", 
                          QRegularExpression::CaseInsensitiveOption);
    QRegularExpressionMatch match = re.match(html);
    if (match.hasMatch()) {
        return match.captured(1).toUpper();
    }
    
    return "UTF-8";  // デフォルト
}

// エンコーディングを考慮した HTML 取得
QString decodeHtml(const QByteArray &data, const QString &encoding) {
    if (encoding == "UTF-8" || encoding == "UTF8") {
        return QString::fromUtf8(data);
    } else if (encoding == "SHIFT_JIS" || encoding == "SHIFT-JIS" || 
               encoding == "SJIS") {
#if QT_VERSION >= QT_VERSION_CHECK(6, 0, 0)
        QStringDecoder decoder("Shift-JIS");
        return decoder.decode(data);
#else
        QTextCodec *codec = QTextCodec::codecForName("Shift-JIS");
        return codec ? codec->toUnicode(data) : QString::fromUtf8(data);
#endif
    } else if (encoding == "EUC-JP") {
#if QT_VERSION >= QT_VERSION_CHECK(6, 0, 0)
        QStringDecoder decoder("EUC-JP");
        return decoder.decode(data);
#else
        QTextCodec *codec = QTextCodec::codecForName("EUC-JP");
        return codec ? codec->toUnicode(data) : QString::fromUtf8(data);
#endif
    }
    return QString::fromUtf8(data);
}
```

---

## パフォーマンス最適化

### 大規模 HTML 処理の Tips

```cpp
// 1. パースオプションの最適化
htmlDocPtr parseHtmlOptimized(const QString &html) {
    return htmlReadMemory(
        html.toUtf8().constData(),
        html.toUtf8().size(),
        nullptr,
        "UTF-8",
        HTML_PARSE_RECOVER |
        HTML_PARSE_NOERROR |
        HTML_PARSE_NOWARNING |
        HTML_PARSE_NONET |
        HTML_PARSE_COMPACT      // メモリ効率優先
    );
}

// 2. XPath コンテキストの再利用
class XPathEvaluator {
public:
    XPathEvaluator(htmlDocPtr doc) : m_doc(doc) {
        m_ctx = xmlXPathNewContext(doc);
    }
    
    ~XPathEvaluator() {
        if (m_ctx) xmlXPathFreeContext(m_ctx);
    }
    
    QString evaluate(const QString &xpath) {
        return evaluateXPath(m_doc, xpath);
    }
    
private:
    htmlDocPtr m_doc;
    xmlXPathContextPtr m_ctx;
};

// 3. 不要なパースの回避
class HtmlCache {
public:
    htmlDocPtr getOrParse(const QString &url, const QString &html) {
        if (m_cache.contains(url)) {
            return m_cache[url];
        }
        htmlDocPtr doc = parseHtml(html);
        m_cache[url] = doc;
        return doc;
    }
    
    ~HtmlCache() {
        for (auto doc : m_cache.values()) {
            if (doc) xmlFreeDoc(doc);
        }
    }
    
private:
    QMap<QString, htmlDocPtr> m_cache;
};
```

### メモリ使用量の監視

```cpp
void logMemoryUsage() {
#ifdef LIBXML_MEMORY_DEBUG
    xmlMemoryDump();
#endif
    qDebug() << "libxml2 memory allocated:" << xmlMemUsed() << "bytes";
}
```

---

## qNewsFlash 用 XPath パターン

### 時事ドットコム (Jiji)

```xpath
# 速報一覧
//ul[contains(@class, 'newsList')]/li

# 各アイテムからの相対パス
.//a/text()                    # タイトル
.//a/@href                     # URL
.//span[@class='date']/text()  # 日時

# 記事本文 (記事ページ)
//div[@class='ArticleText']/p/text()
/html/head/meta[@name='description']/@content
```

### 47NEWS (共同通信)

```xpath
# 速報一覧
//div[@class='newsList']/ul/li

# 各アイテムからの相対パス
.//a[@class='headline']/text() # タイトル
.//a/@href                     # URL
.//time/@datetime              # 日時

# 記事本文
//div[@class='article-body']//p
```

### 汎用ニュースサイト

```xpath
# タイトル (複数パターン試行)
/html/head/meta[@property='og:title']/@content
/html/head/meta[@name='title']/@content
//h1/text()

# 本文 (複数パターン試行)
/html/head/meta[@name='description']/@content
/html/head/meta[@property='og:description']/@content
//div[@class='article-body']//p/text()

# 公開日時
/html/head/meta[@property='article:published_time']/@content
//time/@datetime
//span[@class='publish-date']/text()

# 画像
/html/head/meta[@property='og:image']/@content
//img[@class='main-image']/@src
```

---

## 設定ファイル構造

### qNewsFlash.json

```json
{
  "jijiflash": {
    "url": "https://www.jiji.com/news/flash/",
    "flashxpath": "//ul[@class='newsList']/li",
    "titlexpath": ".//a/text()",
    "urlxpath": ".//a/@href",
    "datexpath": ".//span[@class='date']/text()",
    "paraxpath": ".//p[@class='summary']/text()"
  },
  "kyodoflash": {
    "url": "https://www.47news.jp/flash/",
    "flashxpath": "//div[@class='newsList']/ul/li",
    "titlexpath": ".//a/text()",
    "urlxpath": ".//a/@href",
    "datexpath": ".//time/@datetime"
  },
  "newsapi": {
    "rssurl": "https://example.com/rss.xml",
    "itemxpath": "//item",
    "titlexpath": "title/text()",
    "linkxpath": "link/text()",
    "datexpath": "pubDate/text()",
    "descxpath": "description/text()"
  }
}
```

---

## Webサイト構造変更対応

### デバッグ手順

1. **HTML ソースを取得**
   ```bash
   curl -s "https://example.com/news" > debug.html
   ```

2. **ブラウザ開発者ツールで構造確認**
   - F12 → Elements タブ
   - 右クリック → Copy → Copy XPath

3. **新しい XPath 式を作成**
   - 構造の変更を確認
   - クラス名変更に注意

4. **設定ファイルを更新**
   ```json
   {
     "jijiflash": {
       "flashxpath": "//NEW-CLASS-NAME/..."
     }
   }
   ```

### テスト方法

```cpp
void testXPath(const QString &url, const QString &xpath) {
    qDebug() << "Testing URL:" << url;
    qDebug() << "XPath:" << xpath;
    
    QString html = fetchHtml(url);
    htmlDocPtr doc = parseHtml(html);
    
    xmlXPathContextPtr ctx = xmlXPathNewContext(doc);
    xmlXPathObjectPtr result = xmlXPathEvalExpression(
        BAD_CAST xpath.toUtf8().constData(), ctx
    );
    
    if (result && result->nodesetval) {
        qDebug() << "Matched" << result->nodesetval->nodeNr << "nodes";
        for (int i = 0; i < qMin(5, result->nodesetval->nodeNr); i++) {
            xmlChar *content = xmlNodeGetContent(result->nodesetval->nodeTab[i]);
            qDebug() << "  [" << i << "]" << QString::fromUtf8((char*)content);
            xmlFree(content);
        }
    } else {
        qDebug() << "No matches found";
    }
    
    xmlXPathFreeObject(result);
    xmlXPathFreeContext(ctx);
    xmlFreeDoc(doc);
}
```

---

## トラブルシューティング

### マッチしない場合

| 原因 | 対処法 |
|------|--------|
| JavaScript 動的生成 | ブラウザのソース表示で確認、curl で取得 |
| クラス名変更 | 開発者ツールで最新構造確認 |
| 大文字小文字 | `translate(@class, 'ABC', 'abc')` で正規化 |
| 空白を含むクラス | `contains(@class, 'news')` を使用 |
| 名前空間 | `local-name()` を使用 |

### 文字化け

| 原因 | 対処法 |
|------|--------|
| エンコーディング不一致 | Content-Type ヘッダ確認 |
| meta charset 未設定 | HTML 先頭で charset 確認 |
| 変換エラー | QTextCodec/QStringDecoder のエラー処理 |

### メモリリーク

```cpp
// 必須の解放処理
xmlXPathFreeObject(result);    // XPath 結果
xmlXPathFreeContext(ctx);      // XPath コンテキスト
xmlFreeDoc(doc);               // ドキュメント
xmlFree(content);              // xmlChar* コンテンツ

// 以下も必要に応じて
xmlFreeNode(node);             // 個別ノード
xmlFreeDtd(dtd);               // DTD
```

---

## 参考リンク

- [libxml2 Documentation](https://gitlab.gnome.org/GNOME/libxml2)
- [libxml2 API Reference](http://xmlsoft.org/html/)
- [XPath 1.0 Specification](https://www.w3.org/TR/xpath-10/)
- [MDN XPath Guide](https://developer.mozilla.org/en-US/docs/Web/XPath)
- [libxml2 Tutorial](http://xmlsoft.org/tutorial/)
