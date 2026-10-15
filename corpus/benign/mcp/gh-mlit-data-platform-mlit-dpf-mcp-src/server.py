# --- BEGIN robust import header ---
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- END robust import header ---

import json
from typing import Any, Dict, List, Optional, Union, TypeAlias

from mcp.server import Server
import mcp.types as types

import unicodedata

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions

# absolute imports from this project
from src.client import MLITClient
from src.schemas import (
    SearchBase, SearchByRect, SearchByPoint, SearchByAttr,
    GetDataParams, GetMunicipalitiesParams,
    GetAllDataInput,
    SuggestInput,
    CountDataInput, 
    MeshParams,
    FileDownloadURLsInput, FileRef,
    ZipfileDownloadURLInput,
    ThumbnailURLsInput, ThumbnailRef,
    NormalizeCodesInput, 
)
from src.config import load_settings
from src.utils import logger, new_request_id, Timer

from mcp.server.stdio import stdio_server
import anyio

try:
    from mcp.types import JSONValue
    JSONLike: TypeAlias = JSONValue
except Exception:
    JSONLike: TypeAlias = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

server = Server("MLIT-DATA-PLATFORM-mcp-mod")

# ---------- tools catalog ----------
@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name="search",
            description="""キーワードを使って検索する。検索結果の並べ替えや取得件数を設定することも可能。

                使い方:
                - キーワード検索（同義語も対象）: term="橋梁"
                - 完全一致で絞り込み: term="橋梁", phrase_match=True
                - ページング取得: first=0, size=50  ※APIの上限は一度に最大10,000件
                - 並べ替え: sort_attribute_name="DPF:updated_at", sort_order="dsc"（降順）/ "asc"（昇順）
                - 軽量レスポンス: minimal=True（主要フィールドのみ取得）

                例:
                - バス停を検索: term="バス停"
                - 橋梁を新しい更新順で取得: term="橋梁", sort_attribute_name="DPF:updated_at", sort_order="dsc"
                - ページ2相当を取得: term="道路", first=50, size=50

                注意:
                - API仕様上、term=""（空文字）でも検索は可能ですが、空間条件（矩形/円）やメタデータ条件を使った絞り込みは本ツールでは扱いません。
                空間検索は「search_by_location_rectangle / search_by_location_point_distance」、
                メタデータ検索は「search_by_attribute」を利用してください。
                - sort_order は "asc" または "dsc" を指定してください。
                - 大量件数を扱う場合はページング（first/size）を利用してください。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "検索キーワード。属性フィルタ(prefecture_code等)のみで検索する場合は空文字列\"\"を設定してください"
                    },
                    "first": {
                        "type": "integer",
                        "default": 0,
                        "description": "検索結果の開始位置(オフセット)。ページネーションに使用"
                    },
                    "size": {
                        "type": "integer",
                        "default": 50,
                        "description": "取得件数(最大500)。大量データの場合はget_all_dataを使用してください"
                    },
                    "sort_attribute_name": {
                        "type": "string",
                        "description": "ソート属性名 (例: 'DPF:year', 'DPF:title')"
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "ソート順序: 'asc'(昇順) または 'dsc'(降順)"
                    },
                    "phrase_match": {
                        "type": "boolean",
                        "default": True,
                        "description": "フレーズマッチ。true=完全一致優先, false=部分一致"
                    },
                    "minimal": {
                        "type": "boolean",
                        "default": False,
                        "description": "最小限のフィールドのみ返す(id, title, lat, lon, dataset_id)"
                    },
                },
            },
        ),
        types.Tool(
            name="search_by_location_rectangle",
            description="""矩形範囲と交差するデータを検索する。

                使い方:
                - 指定した矩形範囲（北西緯度経度と南東緯度経度）に含まれるデータを検索します。
                - 検索語（term）を組み合わせて空間＋キーワード検索も可能です。

                例:
                - 東京都内の橋梁を検索:
                term="橋梁",
                location_rectangle_top_left_lat=35.80,
                location_rectangle_top_left_lon=139.55,
                location_rectangle_bottom_right_lat=35.60,
                location_rectangle_bottom_right_lon=139.85

                - キーワードなしで矩形範囲のデータを取得:
                term="",
                location_rectangle_top_left_lat=35.7,
                location_rectangle_top_left_lon=139.6,
                location_rectangle_bottom_right_lat=35.6,
                location_rectangle_bottom_right_lon=139.7

                注意:
                - `location_rectangle_top_left_lat/lon` と `location_rectangle_bottom_right_lat/lon` の4点は必須。
                - 北西（top_left）は右下（bottom_right）よりも緯度が高く、経度が低くなるように指定。
                - termが空の場合でも矩形条件のみで検索可能。
                - phrase_match=Trueで完全一致検索。
                - size は 1回あたり最大10,000件（API制限あり）。
                - 座標は世界測地系（WGS84）を使用。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "検索キーワード。位置のみで検索する場合は省略可能"
                    },
                    "first": {
                        "type": "integer",
                        "default": 0,
                        "description": "検索結果の開始位置"
                    },
                    "size": {
                        "type": "integer",
                        "default": 50,
                        "description": "取得件数(最大500)"
                    },
                    "phrase_match": {
                        "type": "boolean",
                        "default": True,
                        "description": "フレーズマッチモード"
                    },
                    "prefecture_code": {
                        "type": "string",
                        "description": "都道府県コード (例: '13'=東京都, '27'=大阪府)。normalize_codesツールで正規化できます。位置検索と組み合わせて結果を絞り込めます"
                    },
                    "location_rectangle_top_left_lat": {
                        "type": "number",
                        "description": "矩形範囲の左上緯度 (例: 35.6895 for 東京)"
                    },
                    "location_rectangle_top_left_lon": {
                        "type": "number",
                        "description": "矩形範囲の左上経度 (例: 139.6917 for 東京)"
                    },
                    "location_rectangle_bottom_right_lat": {
                        "type": "number",
                        "description": "矩形範囲の右下緯度"
                    },
                    "location_rectangle_bottom_right_lon": {
                        "type": "number",
                        "description": "矩形範囲の右下経度"
                    },
                },
                "required": [
                    "location_rectangle_top_left_lat",
                    "location_rectangle_top_left_lon",
                    "location_rectangle_bottom_right_lat",
                    "location_rectangle_bottom_right_lon",
                ],
            },
        ),
        types.Tool(
            name="search_by_location_point_distance",
            description="""指定した地点と半径によって作成される円形範囲と交差するデータを検索する。

                使い方:
                - 緯度（lat）、経度（lon）、距離（メートル単位）を指定して円形範囲を作成。
                - term（キーワード）を組み合わせることで空間＋テキスト検索も可能。

                例:
                - 東京駅から半径500m以内のバス停を検索:
                term="バス停", location_lat=35.681236, location_lon=139.767125, location_distance=500

                - 半径5km以内の道路関連データ:
                term="道路", location_lat=35.68, location_lon=139.75, location_distance=5000

                - term="" で位置情報のみ検索:
                term="", location_lat=35.68, location_lon=139.75, location_distance=1000

                注意:
                - location_lat / location_lon / location_distance の3つは必須。
                - location_distance の単位はメートル。
                - WGS84座標系を使用。
                - phrase_match=Trueで完全一致検索。
                - 大きな半径を指定すると結果件数が増加するため、sizeで制御してください。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "検索キーワード。位置のみで検索する場合は省略可能"
                    },
                    "first": {
                        "type": "integer",
                        "default": 0,
                        "description": "検索結果の開始位置"
                    },
                    "size": {
                        "type": "integer",
                        "default": 50,
                        "description": "取得件数(最大500)"
                    },
                    "phrase_match": {
                        "type": "boolean",
                        "default": True,
                        "description": "フレーズマッチモード"
                    },
                    "prefecture_code": {
                        "type": "string",
                        "description": "都道府県コード。normalize_codesで正規化可能"
                    },
                    "location_lat": {
                        "type": "number",
                        "description": "中心地点の緯度 (例: 35.6812 for 東京駅)"
                    },
                    "location_lon": {
                        "type": "number",
                        "description": "中心地点の経度 (例: 139.7671 for 東京駅)"
                    },
                    "location_distance": {
                        "type": "number",
                        "description": "検索半径(メートル単位)。例: 1000 = 半径1km圏内"
                    },
                },
                "required": ["location_lat", "location_lon", "location_distance"],
            },
        ),
        types.Tool(
            name="search_by_attribute",
            description="""メタデータ項目を用いて検索する。例えば、カタログ名、データセット名、都道府県、市区町村等を設定して検索することが可能。
                属性フィルタで検索（GraphQL公式形のみ）: attributeFilter { attributeName: "DPF:...", is: <value> }。operatorは常に is。

                使い方:
                - 属性（attribute_name）と値（attribute_value）を指定してメタデータ検索を行う。
                - キーワード（term）を併用して、より細かい条件指定も可能。

                例:
                - 特定データセット内の検索:
                attribute_name="DPF:dataset_id", attribute_value="mlit-001", term="橋梁"

                - 東京都に属するデータ:
                attribute_name="DPF:prefecture_code", attribute_value="13"

                - データカタログ単位で検索:
                attribute_name="DPF:catalog_id", attribute_value="mlit-cat-001", term=""

                注意:
                - attribute_name には DPF:prefix を含む正式属性名を指定してください（例: "DPF:dataset_id"）。
                - attribute_value の型は文字列または数値。operator は常に "is" 固定。
                - term="" の場合でも属性条件のみで検索可能。
                - minimal=True を指定すると軽量レスポンスになります。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "検索キーワード。属性のみで検索する場合は空文字列\"\"または省略可能"
                    },
                    "first": {
                        "type": "integer",
                        "default": 0,
                        "description": "検索結果の開始位置"
                    },
                    "size": {
                        "type": "integer",
                        "default": 50,
                        "description": "取得件数(最大500)"
                    },
                    "phrase_match": {
                        "type": "boolean",
                        "default": True,
                        "description": "フレーズマッチモード"
                    },
                    "attribute_name": {
                        "type": "string",
                        "description": """属性名(必須)。ネームスペースプレフィックス付き。
                            例:
                            - DPF:dataset_id (データセットID)
                            - DPF:prefecture_code (都道府県コード)
                            - DPF:municipality_code (市区町村コード)
                            - DPF:year (年度)
                            - DPF:catalog_id (カタログID)
                            - RSDB:tenken.nendo (点検年度 - 道路施設)
                            - PLATEAU:... (PLATEAU関連属性)

                            プレフィックスがない場合、一般的な属性には自動的にDPF:が追加されます"""
                    },
                    "attribute_value": {
                        "type": "string",
                        "description": """属性値(必須)。'is'オペレータで完全一致検索します。
                            例:
                            - dataset_id: 'mlit-plateau-2023'
                            - prefecture_code: '13' (東京都)
                            - year: '2023'
                            - municipality_code: '13101' (千代田区)

                            数値コードの場合、normalize_codesで正規化してから使用することを推奨"""
                    },
                    "minimal": {
                        "type": "boolean",
                        "default": False,
                        "description": "最小限のフィールドのみ返す"
                    }
                },
                "required": ["attribute_name", "attribute_value"]
            },
        ),
        types.Tool(
            name="get_data_summary",
            description="""データセットIDとデータIDを用いて、基本情報（データID、タイトル）を取得する。

                使い方:
                - すでに dataSetID / dataID を把握している場合に、軽量にタイトル等の基本情報だけ取得します。
                - 検索結果から拾った id を入れて確認・プレビュー用途に最適。

                例:
                - タイトルだけ確認したい:
                dataset_id="cals_construction", data_id="<searchで取得したid>"

                - 詳細取得前の事前チェック:
                dataset_id="mlit-001", data_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

                注意:
                - data_id は検索API（search）の結果で得られる DataClass.id を使用してください。
                - 指定したIDに一致しない場合、totalNumber=0 となります（結果なし）。
                - サマリ用途のため、詳細な付帯情報が必要な場合は get_data を使用してください。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットID。searchツールの結果から取得"
                    },
                    "data_id": {
                        "type": "string",
                        "description": "データID。searchツールの結果から取得"
                    }
                },
                "required": ["dataset_id", "data_id"],
            },
        ),
        types.Tool(
            name="get_data",
            description="""データセットIDとデータIDを用いて、データの詳細情報を取得する。

                使い方:
                - 検索API（search）で拾った id を使って、対象データの詳細（title 以外の各種メタ情報や関連フィールド）を取得。
                - すでに対象が確定している場合、検索よりも効率的に必要情報へアクセスできます。

                例:
                - 既知IDで詳細取得:
                dataset_id="cals_construction", data_id="<searchで取得したid>"

                - データセット内の特定データを直接参照:
                dataset_id="mlit-001", data_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

                注意:
                - 引数は GraphQL の data(dataSetID:, dataID:) に対応しています。
                - data_id は search の結果（DataClass.id）を使用してください。
                - 存在しないIDを指定した場合、totalNumber=0 となり結果は返りません。
                - 詳細項目は MLIT DPF のスキーマに依存します（必要な項目はクライアント側でフィールド選択推奨）。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットID"
                    },
                    "data_id": {
                        "type": "string",
                        "description": "データID"
                    }
                },
                "required": ["dataset_id", "data_id"],
            },
        ),
        types.Tool(
            name="get_data_catalog_summary",
            description="""データカタログ・データセットの基本情報（ID、タイトル）を取得する。

                使い方:
                - すべてのカタログのIDとタイトル一覧を取得: 引数なし（内部的に IDs=null 相当）
                - 特定カタログだけの基本情報を取得: 「get_data_catalog」を minimal=True で使うか、こちらのサマリーを利用

                例:
                - 全カタログのID/タイトル:
                （引数なしで呼び出し）

                - 特定ID群のみの概要を見たい（軽量）:
                get_data_catalog を minimal=True, ids=["cals","rsdb"] で代用

                注意:
                - 返却内容はID/タイトル中心の軽量情報です。詳細なメタデータやデータセット一覧が必要な場合は「get_data_catalog」を使用してください。
                - 公式APIでは IDs=null を指定すると全件取得になります（本ツールは内部でこの挙動に合わせています）。""",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_data_catalog",
            description="""データカタログ・データセットの詳細情報を取得する。

                使い方:
                - すべてのカタログの詳細を取得（重い）: ids を指定しない（内部的に IDs=null 相当）、include_datasets=True
                - 特定カタログだけ取得（推奨）: ids=["cals","rsdb"] のように配列で指定
                - 軽量にID/タイトル等だけ取得: minimal=True
                - データセット一覧や件数も取得: include_datasets=True（データセットのメタデータ定義・件数が取得可能）

                例:
                - 全カタログのID/タイトルのみ（軽量）:
                minimal=True, include_datasets=False

                - 特定カタログ（cals, rsdb）の詳細 + データセット一覧:
                ids=["cals","rsdb"], minimal=False, include_datasets=True

                - 単一カタログのメタ情報だけ（datasets不要）:
                ids=["mlit_plateau"], minimal=False, include_datasets=False

                注意:
                - 公式仕様では `dataCatalog(IDs: [String])` で、IDs に null を渡すと全カタログが返ります。IDを指定すると対象のみ取得されます。
                - `include_datasets=True` の場合、各カタログ配下の `datasets` 情報（メタデータ定義、データ件数など）も取得します。大量になるため必要に応じてオフにしてください。
                - `minimal=True` は主要フィールド中心の軽量レスポンスです。詳細が必要な場合は False にしてください。
                - 返るフィールドは `DataCatalogClass` に準拠します（title, description, publisher, modified など多数を含み、datasets も持ちます）。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "カタログIDの配列。nullの場合は全カタログを取得"
                    },
                    "minimal": {
                        "type": "boolean",
                        "default": False,
                        "description": "最小限の情報のみ返す"
                    },
                    "include_datasets": {
                        "type": "boolean",
                        "default": True,
                        "description": "配下のデータセット情報も含める"
                    }
                }
            }
        ),
        types.Tool(
            name="get_prefecture_data",
            description="""都道府県名・都道府県コード一覧を取得する。

                使い方:
                - 引数なしで47都道府県の一覧を取得（コード/名称）。
                - 軽量にコードと正式名称のみ取得、または必要に応じて name_short / hiragana / romaji などをクライアント側でフィールド選択。

                例:
                - コードと名称だけ取得:
                （引数なしで呼び出し）

                - かな・ローマ字も含めて取得（クライアントのフィールド指定例）:
                prefecture { code_as_string name hiragana romaji }

                注意:
                - GraphQL定義: `prefecture: [PrefectureClass]`。パラメータはありません（常に全都道府県を返します）。
                - 主なフィールド: code（数値）, code_as_string（2桁文字列）, name（正式名）, name_short, hiragana, romaji, used_from / used_until。
                - 公式コードは2桁（先頭ゼロ付き）。アプリで文字列コードが必要な場合は `code_as_string` を利用してください。""",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_municipality_data",
            description="""市区町村名・市区町村コード一覧を取得する。

                使い方:
                - フィルタなし（既定）: 全国すべての市区町村を返します（大量件数）。
                - 都道府県で絞り込み: pref_codes=["13"] のように都道府県コードを指定（複数可）。
                - 市区町村コードで絞り込み: muni_codes=["13101","13102"] のように6桁コードを指定（複数可）。
                - 取得フィールドを最小化: fields=["code_as_string","name"] のように必要フィールドだけ指定（クライアント最適化）。

                例:
                - 全国の市区町村（コード/名称のみ）:
                pref_codes=[], muni_codes=[], fields=["code_as_string","name"]

                - 東京都の市区町村一覧:
                pref_codes=["13"], fields=["code_as_string","prefecture_code","name","katakana"]

                - 特定の市区町村コードを直接取得:
                muni_codes=["13101","13102"], fields=["code_as_string","name","romaji"]

                注意:
                - GraphQL仕様: `municipalities(muniCodes:[Any], prefCodes:[Any]): [MunicipalityClass]`。
                パラメータ未指定時は**全件**を返します（大量になるため fields での軽量化推奨）。:contentReference[oaicite:1]{index=1}
                - コードは数値/文字列どちらでも指定可能ですが、アプリ側で扱いやすいのは **6桁の文字列** `code_as_string` です（例: "13101"）。:contentReference[oaicite:2]{index=2}
                - 返却クラス `MunicipalityClass` には、`name`（郡名/市区町村名/政令市区名を組み合わせた正式名称）、`katakana`、`romaji`、`prefecture_code`、および有効期間（`used_from`/`used_until`）等が含まれます。:contentReference[oaicite:3]{index=3}
                - 政令指定都市の区は**独立したエントリ**として返ります（例: 札幌市中央区 など）。:contentReference[oaicite:4]{index=4}""",
            inputSchema={
                "type": "object",
                "properties": {
                    "pref_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "都道府県コードの配列 (例: ['13', '27'])"
                    },
                    "muni_codes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "市区町村コードの配列 (例: ['13101', '13102'])"
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "取得するフィールド名の配列。デフォルト: ['code_as_string', 'prefecture_code', 'name']"
                    },
                    "pref_code": {
                        "type": "string",
                        "description": "単一都道府県コード(後方互換性用)。pref_codesの使用を推奨"
                    },
                },
            },
        ),
        types.Tool(
            name="get_all_data",
            description="""条件に当てはまる大量のデータを取得する。

                使い方:
                - 大量件数をバッチで取得します。内部的に GraphQL `getAllData` を使用し、返却された `nextDataRequestToken` を用いて次バッチを自動で取得します。
                - 絞り込みは `term` / `phrase_match` と、属性（`catalog_id`, `dataset_id`, `prefecture_code`, `municipality_code`, `address`）や矩形範囲を組み合わせて指定できます。
                - 1回のバッチ件数は `size`（API上限は1000）。本ツールの既定は `size=1000`（最大値）で、`max_batches` または `max_items` で総取得量を制御します。
                - メタデータが不要な場合は `include_metadata=False` で転送量を削減できます。

                例:
                - データセット単位で全件取得（メタデータ付き）:
                term="", dataset_id="mlit-001", size=1000, max_batches=10, include_metadata=True

                - カタログIDと矩形で範囲取得（東京都心部の例）:
                term="", catalog_id="dimaps",
                location_rectangle_top_left_lat=35.80,  location_rectangle_top_left_lon=139.55,
                location_rectangle_bottom_right_lat=35.60, location_rectangle_bottom_right_lon=139.85,
                size=1000, max_batches=5

                - 都道府県コードのみで全件走査:
                term="", prefecture_code="13", size=1000, max_items=5000

                注意:
                - API仕様上、`locationFilter`（矩形など）**単独では検索不可**です。必ず `term` または `attributeFilter`（本ツールでは `catalog_id` / `dataset_id` / `prefecture_code` / `municipality_code` / `address` に相当）を併用してください。
                - 次バッチ取得時は `nextDataRequestToken` を使用し、**他の条件は無視**されます（ツール側で自動処理）。データが空になった時点で取得を停止します。
                - `size` のAPI上限は1000です（本ツールの既定値は1000）。大量取得時は `max_batches` / `max_items` を併用して制御してください。
                - 座標は WGS84。矩形は「北西（top_left）→南東（bottom_right）」の順で指定してください。
                - `include_metadata=False` にすると `id`/`title` 中心の軽量レスポンスになります。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "size": {
                        "type": "integer",
                        "default": 1000,
                        "description": "1回のリクエストで取得する件数(最大1000)。大量データの場合はバッチ処理で自動的に複数回リクエストされます"
                    },
                    "term": {
                        "type": "string",
                        "description": "検索キーワード。属性フィルタのみの場合は空文字列\"\"または省略"
                    },
                    "phrase_match": {
                        "type": "boolean",
                        "description": "フレーズマッチモード"
                    },
                    "prefecture_code": {
                        "type": "string",
                        "description": "都道府県コード。normalize_codesで正規化済みのコードを使用してください"
                    },
                    "municipality_code": {
                        "type": "string",
                        "description": "市区町村コード(5桁)。例: '13101'=千代田区"
                    },
                    "address": {
                        "type": "string",
                        "description": "住所による検索。都道府県名や市区町村名を含む文字列"
                    },
                    "catalog_id": {
                        "type": "string",
                        "description": "カタログID。get_data_catalog_summaryで確認可能"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットID"
                    },
                    "location_rectangle_top_left_lat": {
                        "type": "number",
                        "description": "矩形範囲の左上緯度"
                    },
                    "location_rectangle_top_left_lon": {
                        "type": "number",
                        "description": "矩形範囲の左上経度"
                    },
                    "location_rectangle_bottom_right_lat": {
                        "type": "number",
                        "description": "矩形範囲の右下緯度"
                    },
                    "location_rectangle_bottom_right_lon": {
                        "type": "number",
                        "description": "矩形範囲の右下経度"
                    },
                    "max_batches": {
                        "type": "integer",
                        "default": 20,
                        "description": "最大バッチ処理回数。20回 × size(1000) = 最大20,000件まで取得可能"
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "default": True,
                        "description": "メタデータを含めるか。falseにするとレスポンスサイズが小さくなります"
                    },
                    "max_items": {
                        "type": "integer",
                        "description": "取得する最大アイテム数の上限。設定するとmax_batchesより優先されます"
                    },
                },
            },
        ),
        types.Tool(
            name="get_suggest",
            description="""キーワード検索の候補を表示する。

                使い方:
                - 入力中の文字列（term）から、上位のキーワード候補を返します。候補は `name`（候補語）と `cnt`（該当件数）を含みます。
                - 完全一致寄りにしたい場合は phrase_match=True を指定します。
                - カタログ/データセット等で範囲を絞って候補を出すことも可能です（search と同様に attributeFilter 相当を利用）。

                例:
                - 単純サジェスト（全データ対象）:
                term="川", phrase_match=True
                → 上位候補（例: "川河川", "河川", ...）が name/cnt で返る。

                - 特定データセット内でのサジェスト:
                term="川", phrase_match=True, dataset_id="cals_construction"

                - カタログ単位でのサジェスト:
                term="橋", catalog_id="dimaps"

                注意:
                - term は必須です（空文字は不可）。
                - 本APIは GraphQL `suggest(term, phraseMatch, attributeFilter?)` を使用します。属性での絞り込みは
                本ツールの引数（catalog_id / dataset_id / prefecture_code / municipality_code / address）を
                内部で attributeFilter にマッピングして行います。
                - 返却される候補は name と cnt を含む配列です（例は公式サンプル参照）。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "検索キーワードの一部。例: 'バス' → 'バス停', 'バスロケ' などを提案"
                    },
                    "phrase_match": {
                        "type": "boolean",
                        "description": "フレーズマッチモード"
                    },
                    "prefecture_code": {
                        "type": "string",
                        "description": "都道府県コードで絞り込み"
                    },
                    "municipality_code": {
                        "type": "string",
                        "description": "市区町村コードで絞り込み"
                    },
                    "address": {
                        "type": "string",
                        "description": "住所で絞り込み"
                    },
                    "catalog_id": {
                        "type": "string",
                        "description": "カタログIDで絞り込み"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットIDで絞り込み"
                    },
                    "location_rectangle_top_left_lat": {
                        "type": "number",
                        "description": "矩形範囲の左上緯度"
                    },
                    "location_rectangle_top_left_lon": {
                        "type": "number",
                        "description": "矩形範囲の左上経度"
                    },
                    "location_rectangle_bottom_right_lat": {
                        "type": "number",
                        "description": "矩形範囲の右下緯度"
                    },
                    "location_rectangle_bottom_right_lon": {
                        "type": "number",
                        "description": "矩形範囲の右下経度"
                    },
                },
                "required": ["term"],
            },
        ),
        types.Tool(
            name="get_count_data",
            description="""特定のデータセットに含まれるデータや、指定した範囲、日付など、指定した検索条件に一致するデータの件数を取得する。分類ごとの集計も可能。

                使い方:
                - キーワード / メタデータ / 空間条件を組み合わせて、件数のみを高速に把握できます。
                - 集計の切り口は `slice_type` で指定:
                - "dataset": カタログ→データセットの2段階で件数を返す（全カタログ/全データセットの分布を俯瞰）
                - "attribute": 任意属性ごとの上位出現値を `slice_size` 件まで取得（最大50）。必要なら `slice_sub_attribute_name` で下位分類も可能。
                - 空間条件（矩形/円）は `location_*` 引数により内部で `locationFilter` に変換。
                - 属性条件は `catalog_id` / `dataset_id` / `prefecture_code` / `municipality_code` / `address` などを内部で `attributeFilter` に変換。

                例:
                - キーワード「橋梁」をデータセット別に件数集計:
                term="橋梁", slice_type="dataset"

                - 都道府県別トップ10 + その下でデータセット別内訳:
                term="", slice_type="attribute",
                slice_attribute_name="DPF:prefecture_code", slice_size=10,
                slice_sub_attribute_name="DPF:dataset_id", slice_sub_size=10

                - 矩形範囲（東京都心部）× カタログIDで件数:
                term="", catalog_id="dimaps",
                location_rectangle_top_left_lat=35.80,  location_rectangle_top_left_lon=139.55,
                location_rectangle_bottom_right_lat=35.60, location_rectangle_bottom_right_lon=139.85,
                slice_type="attribute", slice_attribute_name="DPF:dataset_id", slice_size=20

                - 円範囲（東京駅 半径500m）× データセット内件数:
                term="", dataset_id="cals_construction",
                location_lat=35.681236, location_lon=139.767125, location_distance=500,
                slice_type="attribute", slice_attribute_name="DPF:title", slice_size=10

                注意:
                - 公式仕様上、`locationFilter`（空間条件）**のみでは検索不可**。必ず `term` か `attributeFilter`（本ツールでは catalog_id / dataset_id / prefecture_code / municipality_code / address 等）を併用してください。
                - `slice_size` の最大は **50**。上位出現値のみが返却され、それ以外は省略されます。上位分類の `dataCount` には下位分類で表示されない分も含まれます。
                - `attributeFilter` は `is/similar/gte/gt/lte/lt` に対応し、`AND` / `OR` でネスト結合が可能（本ツールでは単純条件を主にサポート）。
                - `locationFilter` は `rectangle` / `geoDistance` のほか `union` / `intersection` に対応。ただし **同クラス内の他メンバーと同時利用不可**、かつ **入れ子（ネスト）不可**。
                - 座標は WGS84。矩形は「北西(top_left)→南東(bottom_right)」の順で指定。
                - パフォーマンス観点から、まず `get_count_data` でボリューム見積り → 必要に応じて `get_all_data` で実データ取得が推奨。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "検索キーワード。属性フィルタのみの場合は省略可能"
                    },
                    "phrase_match": {
                        "type": "boolean",
                        "description": "フレーズマッチモード"
                    },
                    "prefecture_code": {
                        "type": "string",
                        "description": "都道府県コードで絞り込み"
                    },
                    "municipality_code": {
                        "type": "string",
                        "description": "市区町村コードで絞り込み"
                    },
                    "address": {
                        "type": "string",
                        "description": "住所で絞り込み"
                    },
                    "catalog_id": {
                        "type": "string",
                        "description": "カタログIDで絞り込み"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットIDで絞り込み。集計対象の指定に必須"
                    },
                    "location_rectangle_top_left_lat": {
                        "type": "number",
                        "description": "矩形範囲の左上緯度"
                    },
                    "location_rectangle_top_left_lon": {
                        "type": "number",
                        "description": "矩形範囲の左上経度"
                    },
                    "location_rectangle_bottom_right_lat": {
                        "type": "number",
                        "description": "矩形範囲の右下緯度"
                    },
                    "location_rectangle_bottom_right_lon": {
                        "type": "number",
                        "description": "矩形範囲の右下経度"
                    },
                    "location_lat": {
                        "type": "number",
                        "description": "中心地点の緯度(円形範囲検索用)"
                    },
                    "location_lon": {
                        "type": "number",
                        "description": "中心地点の経度(円形範囲検索用)"
                    },
                    "location_distance": {
                        "type": "number",
                        "description": "検索半径(メートル単位、円形範囲検索用)"
                    },
                    "slice_type": {
                        "type": "string",
                        "description": """集計タイプ:
                        - 'attribute': 属性別に集計(最も一般的)
                        - 'dataset': データセット別に集計
                        省略時は属性指定があれば自動的に'attribute'になります"""
                    },
                    "slice_attribute_name": {
                        "type": "string",
                        "description": """集計する属性名(ネームスペース付き)。
                        例:
                        - 'DPF:year' → 年度別集計
                        - 'DPF:prefecture_code' → 都道府県別集計
                        - 'RSDB:tenken.nendo' → 点検年度別集計

                        指定すると自動的にslice_type='attribute'になります"""
                    },
                    "slice_size": {
                        "type": "integer",
                        "description": "集計結果の最大件数(1-50)。上位N件のみ取得したい場合に指定"
                    },
                    "slice_sub_attribute_name": {
                        "type": "string",
                        "description": """2段階目の集計属性名。
                        例: slice_attribute_name='DPF:prefecture_code', slice_sub_attribute_name='DPF:year'
                        → 都道府県別 × 年度別のクロス集計"""
                    },
                    "slice_sub_size": {
                        "type": "integer",
                        "description": "2段階目の集計結果の最大件数"
                    },
                },
            },
        ),
        types.Tool(
            name="get_mesh",
            description="""メッシュに含まれるデータを取得する。

                使い方:
                - 事前に `search` API で対象データを特定し、レスポンスの `dataset_id`（=dataSetID）、`id`（=dataID）、
                および `meshes[].id`（=meshID）を取得します。その上で、本APIに `meshCode`（メッシュコード）を指定して該当メッシュのオブジェクトを取得します。
                - `meshCode` は任意の次元（例: 250m など）のメッシュコードを指定可能。該当がなければ `null` が返ります。

                例:
                - 人口5次メッシュ（250m）の一枚を取得:
                dataset_id="dpf_population_data",
                data_id="8fb65cb6-a7e3-4b15-bf17-1c71be572a9f",
                mesh_id="national_sensus_250m_r2",
                mesh_code="5339452932"

                - 事前に `search` で必要パラメータを取得:
                term="人口及び世帯" → 結果の `dataset_id`, `id`, `meshes[].id` を本APIに転用

                注意:
                - GraphQL定義は `mesh(dataSetID:String!, dataID:String!, meshID:String!, meshCode:String!): JSONObject`。
                返却はJSONオブジェクトで、メッシュコードや指標（例: 総人口 等）が含まれます。該当しない場合は `null`。:contentReference[oaicite:1]{index=1}
                - `meshCode` の粒度は自由ですが、データ側に該当レコードが存在しないと取得できません（空振り時は `null`）。:contentReference[oaicite:2]{index=2}
                - 必要な `meshID` は `search` レスポンスの `meshes` 配列から選びます（例: "national_sensus_250m_r2"）。:contentReference[oaicite:3]{index=3}
                - 利用にはMLIT DPFのGraphQLエンドポイントとAPIキーが必要です。:contentReference[oaicite:4]{index=4}""",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットID"
                    },
                    "data_id": {
                        "type": "string",
                        "description": "データID"
                    },
                    "mesh_id": {
                        "type": "string",
                        "description": "メッシュID"
                    },
                    "mesh_code": {
                        "type": "string",
                        "description": "メッシュコード(標準地域メッシュコード)"
                    },
                },
                "required": ["dataset_id", "data_id", "mesh_id", "mesh_code"],
            },
        ),
        types.Tool(
            name="get_file_download_urls",
            description="""ファイルのダウンロード用URLを取得する。取得したURLがhttps://data-platform.mlit.go.jp/download/で始まる場合、URLの有効期限は60秒。

                使い方:
                - 事前に search / data API で対象データの `files`（id, original_path）を取得してから、本APIでダウンロードURLを生成します。
                - 本ツールは2通りに対応:
                (A) `files=[{id, original_path}, ...]` を直接渡す
                (B) `dataset_id` と `data_id` を渡す（ツール側で対象データの `files` を読み取り、一括でURL化）

                例:
                - 単一ファイルのURLを取得（直接指定）:
                files=[{ id:"<filesのid>", original_path:"INDEX_C.XML" }]

                - データIDから付属ファイルのURL一覧を取得（簡易）:
                dataset_id="cals_construction", data_id="<searchで取得したid>"

                注意:
                - `id` と `original_path` は、まず search / data のレスポンスに含まれる `DataClass.files` から取得してください。
                - 取得したURLが `https://data-platform.mlit.go.jp/download/` で始まる場合、**60秒以内にダウンロード開始**が必要です（期限切れに注意）。
                - 連携元サイトで直接ダウンロードできる場合は、メタデータ `DPF:downloadURLs` / `DPF:dataURLs` も併用してください。
                - `original_path` を省略すると、付属ファイルの元ファイル名・パスが用いられます（files.original_pathを参照）。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "ファイルID。get_dataの結果から取得"
                                },
                                "original_path": {
                                    "type": "string",
                                    "description": "元のファイルパス。get_dataの結果から取得"
                                }
                            },
                            "required": ["id", "original_path"]
                        },
                        "description": "ダウンロードするファイルの配列。dataset_id+data_idを指定する場合は省略可能"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットID。filesを省略する場合は必須"
                    },
                    "data_id": {
                        "type": "string",
                        "description": "データID。filesを省略する場合は必須"
                    },
                },
            },
        ),
        types.Tool(
            name="get_zipfile_download_url",
            description="""複数の付属ファイルをZIP形式で圧縮し、圧縮ファイルのダウンロードURLを取得する。URLの有効期限は60秒。

                使い方:
                - まとめて取得したい複数ファイルの `id` と、ZIP内に格納する `original_path`（パス）を指定します。
                - search / data で取得した `files` から必要な id / original_path を選択して投入してください。
                - 本ツールは2通りに対応:
                (A) `files=[{id, original_path}, ...]` を直接渡す
                (B) `dataset_id` と `data_id` を渡す（ツール側で `files` を参照しZIP作成）

                例:
                - IFCを3本まとめてZIPで取得:
                files=[
                    { id:"<id1>", original_path:"ICON/.../モデルA.ifc" },
                    { id:"<id2>", original_path:"ICON/.../モデルB.ifc" },
                    { id:"<id3>", original_path:"ICON/.../モデルC.ifc" },
                ]

                - データIDから付属ファイルをZIP化（簡易）:
                dataset_id="cals_construction", data_id="<searchで取得したid>"

                注意:
                - ZIPのダウンロードURLは **60秒間のみ有効** です。取得後すぐにダウンロード処理を開始してください。
                - GraphQLは `zipfileDownloadURL(files:[FileInputClass]): String`。`files` の `id` / `original_path` は `DataClass.files` を用います。
                - 大容量ZIPはクライアント側のタイムアウト設定にも注意してください。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "ファイルID"
                                },
                                "original_path": {
                                    "type": "string",
                                    "description": "元のファイルパス"
                                }
                            },
                            "required": ["id", "original_path"]
                        },
                        "description": "ZIP化するファイルの配列"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットID"
                    },
                    "data_id": {
                        "type": "string",
                        "description": "データID"
                    },
                },
            },
        ),
        types.Tool(
            name="get_thumbnail_urls",
            description="""データのサムネイル画像URLを取得する。取得したURLがhttps://data-platform.mlit.go.jp/download/で始まる場合、URLの有効期限は60秒。

                使い方:
                - 基本: dataset_id と data_id を指定して、そのデータに紐づくサムネイルURL一覧を取得します。
                - ファイル個別のサムネイルが欲しい場合は、search/data 結果から取得した file の id を使って絞り込みます（GraphQLの fileID に相当）。
                - 本ツールは2通りに対応:
                (A) thumbnails=[{id, original_path}, ...] を直接渡す（既にファイル情報を持っている場合に高速）
                (B) dataset_id と data_id を渡す（ツール側で対象データのサムネイルを探索）

                例:
                - データIDからサムネイルのURL一覧を取得:
                dataset_id="ndm", data_id="<searchで取得したid>"

                - 特定ファイルのサムネイルを取得（直接指定）:
                thumbnails=[{ id:"<fileのid>", original_path:"<元ファイルの相対パス>" }]

                注意:
                - 取得したURLが download ドメインで始まる場合は **60秒以内にダウンロード開始**が必要です（期限切れに注意）。
                - サムネイルが存在しないデータは **空配列** が返ります。
                - fileID を指定しない場合はデータに紐づく代表サムネイル等が返ります。必要に応じてファイルIDで絞り込んでください。
                - レスポンスは配列で、各要素は fileName / URL を含みます（GraphQL: thumbnailURLs）。""",
            inputSchema={
                "type": "object",
                "properties": {
                    "thumbnails": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "string",
                                    "description": "サムネイルID"
                                },
                                "original_path": {
                                    "type": "string",
                                    "description": "元のファイルパス"
                                }
                            },
                            "required": ["id", "original_path"]
                        },
                        "description": "取得するサムネイルの配列"
                    },
                    "dataset_id": {
                        "type": "string",
                        "description": "データセットID"
                    },
                    "data_id": {
                        "type": "string",
                        "description": "データID"
                    },
                },
            },
        ),
        # ===== normalize_codes =====
        types.Tool(
            name="normalize_codes",
            description="""入力された都道府県名・市区町村名を正規化し、正式なコードと名称を取得する。

                使用ケース:
                1. ユーザー入力('東京', 'Tokyo', '13')を正規化 → '13' + '東京都'
                2. 市区町村名から5桁コードを取得
                3. 曖昧な入力の候補一覧取得

                このツールを他の検索ツールの前に実行することで、正確なprefecture_code/municipality_codeを取得できます""",
            inputSchema={
                "type": "object",
                "properties": {
                    "prefecture": {
                        "type": "string",
                        "description": """都道府県の指定。以下の形式に対応:
                        - コード: '13', '27'
                        - 日本語: '東京都', '東京', '大阪府', '大阪'
                        - ローマ字: 'Tokyo', 'Osaka', 'Hokkaido'

                        全角数字(例: '１３')も自動的に正規化されます"""
                    },
                    "municipality": {
                        "type": "string",
                        "description": """市区町村の指定。以下の形式に対応:
                        - JISコード: '13101' (千代田区)
                        - 日本語: '千代田区', '港区'

                        注意: 市区町村を指定する場合、prefectureも併せて指定することを推奨します(同名の市区町村が複数存在する可能性があるため)"""
                    }
                }
            },
        ),
    ]


# ---------- tools handler ----------

def _is_ascii_digits(s: str) -> bool:
    return isinstance(s, str) and len(s) > 0 and all("0" <= ch <= "9" for ch in s)

async def _auto_normalize_region_args(arguments: dict, client: MLITClient) -> dict:
    """
    If prefecture_code / municipality_code look non-canonical (e.g., full-width '１３' or JP name),
    call normalize_codes and patch arguments in-place:
      - prefecture_code -> canonical numeric string (e.g., '13')
      - municipality_code -> canonical if resolvable
      - address -> set to prefecture_name if empty (helps attribute-only patterns)
    """
    args = dict(arguments)  # shallow copy

    pref_raw = args.get("prefecture_code")
    muni_raw = args.get("municipality_code")

    need_norm = False

    # Detect non-ASCII digits (full-width, JP text, romaji, etc.)
    if isinstance(pref_raw, str) and (not _is_ascii_digits(pref_raw)):
        need_norm = True
    if isinstance(muni_raw, str) and (not _is_ascii_digits(unicodedata.normalize("NFKC", muni_raw))):
        # municipality code can be 5 ascii digits; if not ascii-digits, try normalize
        need_norm = True

    if not need_norm:
        # still normalize if user passed e.g. '東京都' in prefecture_code by mistake
        if isinstance(pref_raw, str):
            nf = unicodedata.normalize("NFKC", pref_raw)
            if not _is_ascii_digits(nf):
                need_norm = True

    if need_norm:
        from src.schemas import NormalizeCodesInput
        res = await client.normalize_codes(NormalizeCodesInput(
            prefecture=pref_raw if isinstance(pref_raw, str) else None,
            municipality=muni_raw if isinstance(muni_raw, str) else None,
        ))
        if res.prefecture_code:
            args["prefecture_code"] = res.prefecture_code
        # if address missing, fill with official prefecture name (helps filter-only queries)
        if not args.get("address") and res.prefecture_name:
            args["address"] = res.prefecture_name
        if res.municipality_code:
            args["municipality_code"] = res.municipality_code
        # (Optional) you could surface res.warnings via logs for debugging:
        if res.warnings:
            logger.info("normalize_codes_warnings", extra={"warnings": res.warnings})

    return args

def validate_and_provide_hints(name: str, arguments: dict) -> Optional[str]:
    """
    Validate parameters and return helpful error message if invalid.
    Returns None if valid.
    """
    hints = {
        "error": None,
        "parameter": None,
        "provided": None,
        "expected": None,
        "examples": []
    }
    
    if name == "search":
        # Check if using attribute filters without term
        has_filters = any(arguments.get(k) for k in ["prefecture_code", "municipality_code", "dataset_id"])
        if has_filters and "term" not in arguments:
            hints["error"] = "属性フィルタを使用する場合、termパラメータが必要です"
            hints["parameter"] = "term"
            hints["expected"] = "空文字列(\"\")または検索キーワード"
            hints["examples"] = [
                {"term": "", "prefecture_code": "13"},
                {"term": "バス停", "prefecture_code": "13"}
            ]
            return json.dumps(hints, ensure_ascii=False)
    
    elif name == "search_by_attribute":
        attr_name = arguments.get("attribute_name", "")
        if attr_name and ":" not in attr_name:
            # Check if it's a known attribute
            known = ["dataset_id", "prefecture_code", "municipality_code", "year", "catalog_id"]
            if any(attr_name.lower().endswith(k) for k in known):
                hints["error"] = "属性名にネームスペースプレフィックスが必要です"
                hints["parameter"] = "attribute_name"
                hints["provided"] = attr_name
                hints["expected"] = f"DPF:{attr_name}"
                hints["examples"] = [
                    "DPF:dataset_id",
                    "DPF:prefecture_code",
                    "RSDB:tenken.nendo"
                ]
                return json.dumps(hints, ensure_ascii=False)
    
    elif name == "get_count_data":
        # Check if slice configuration makes sense
        has_slice_attr = arguments.get("slice_attribute_name")
        has_slice_type = arguments.get("slice_type")
        
        if has_slice_attr and not has_slice_type:
            # Auto-set, but inform user
            logger.info("get_count_data: slice_type not specified, defaulting to 'attribute'")
        
        if has_slice_type == "dataset" and has_slice_attr:
            hints["error"] = "slice_type='dataset'の場合、slice_attribute_nameは不要です"
            hints["parameter"] = "slice_type"
            hints["examples"] = [
                {"slice_type": "dataset"},  # No attribute needed
                {"slice_type": "attribute", "slice_attribute_name": "DPF:year"}
            ]
            return json.dumps(hints, ensure_ascii=False)
    
    return None


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
    rid = new_request_id()
    cfg = load_settings()
    client = MLITClient()

    try:
        # Pre-validation check
        validation_error = validate_and_provide_hints(name, arguments)
        if validation_error:
            return [types.TextContent(type="text", text=validation_error)]

        with Timer() as t:
            if name == "search":
                p = SearchBase.model_validate(arguments)
                data = await client.search_keyword(
                    term=p.term or "",
                    first=p.first,
                    size=p.size,
                    phrase_match=p.phrase_match,
                    sort_attribute_name=p.sort_attribute_name,
                    sort_order=p.sort_order,
                    fields=client._fields_min() if p.minimal else client._fields_basic(),
                )

            elif name == "search_by_location_rectangle":
                p = SearchByRect.model_validate({
                    "term": arguments.get("term"),
                    "first": arguments.get("first", 0),
                    "size": arguments.get("size", 50),
                    "phrase_match": arguments.get("phrase_match", True),
                    "prefecture_code": arguments.get("prefecture_code"),
                    "rectangle": {
                        "top_left_lat": arguments["location_rectangle_top_left_lat"],
                        "top_left_lon": arguments["location_rectangle_top_left_lon"],
                        "bottom_right_lat": arguments["location_rectangle_bottom_right_lat"],
                        "bottom_right_lon": arguments["location_rectangle_bottom_right_lon"],
                    }
                })
                data = await client.search_by_rectangle(
                    p.rectangle.top_left_lat, p.rectangle.top_left_lon,
                    p.rectangle.bottom_right_lat, p.rectangle.bottom_right_lon,
                    term=p.term or "",
                    first=p.first,
                    size=p.size,
                    phrase_match=p.phrase_match,
                )

            elif name == "search_by_location_point_distance":
                p = SearchByPoint.model_validate({
                    "term": arguments.get("term"),
                    "first": arguments.get("first", 0),
                    "size": arguments.get("size", 50),
                    "phrase_match": arguments.get("phrase_match", True),
                    "prefecture_code": arguments.get("prefecture_code"),
                    "point": {
                        "lat": arguments["location_lat"],
                        "lon": arguments["location_lon"],
                        "distance": arguments["location_distance"],
                    }
                })
                data = await client.search_by_point(
                    p.point.lat, p.point.lon, p.point.distance,
                    term=p.term or "",
                    first=p.first,
                    size=p.size,
                    phrase_match=p.phrase_match,
                )

            elif name == "search_by_attribute":
                # GraphQL (attribute_name + attribute_value; operator is)
                p = SearchByAttr.model_validate(arguments)
                fields = None if not p.minimal else client._fields_min()
                data = await client.search_by_attribute_raw(
                    term=p.term,
                    first=p.first,
                    size=p.size,
                    phrase_match=p.phrase_match,
                    attribute_name=p.attribute_name,
                    attribute_value=p.attribute_value,
                    fields=fields,
                )

            elif name == "get_data_summary":
                p = GetDataParams.model_validate(arguments)
                data = await client.get_data_summary(p.dataset_id, p.data_id)

            elif name == "get_data":
                p = GetDataParams.model_validate(arguments)
                data = await client.get_data(p.dataset_id, p.data_id)

            elif name == "get_data_catalog_summary":
                data = await client.get_data_catalog_summary()

            elif name == "get_data_catalog":
                ids = arguments.get("ids")
                if ids is not None and not isinstance(ids, list):
                    raise ValueError("ids must be an array of strings")
                minimal = arguments.get("minimal", False)
                include_datasets = arguments.get("include_datasets", True)
                data = await client.get_data_catalog(
                    ids=ids,
                    minimal=minimal,
                    include_datasets=include_datasets,
                )

            elif name == "get_prefecture_data":
                data = await client.get_prefectures()

            elif name == "get_municipality_data":
                p = GetMunicipalitiesParams.model_validate(arguments)
                data = await client.get_municipalities(
                    pref_codes=p.pref_codes,
                    muni_codes=p.muni_codes,
                    fields=p.fields,
                )

            elif name == "get_all_data":
                arguments = await _auto_normalize_region_args(arguments, client)
                p = GetAllDataInput.model_validate({
                    "size": arguments.get("size", 1000),
                    "term": arguments.get("term"),
                    "phrase_match": arguments.get("phrase_match"),
                    "prefecture_code": arguments.get("prefecture_code"),
                    "municipality_code": arguments.get("municipality_code"),
                    "address": arguments.get("address"),
                    "catalog_id": arguments.get("catalog_id"),
                    "dataset_id": arguments.get("dataset_id"),
                    "location_rectangle_top_left_lat": arguments.get("location_rectangle_top_left_lat"),
                    "location_rectangle_top_left_lon": arguments.get("location_rectangle_top_left_lon"),
                    "location_rectangle_bottom_right_lat": arguments.get("location_rectangle_bottom_right_lat"),
                    "location_rectangle_bottom_right_lon": arguments.get("location_rectangle_bottom_right_lon"),
                    "max_batches": arguments.get("max_batches", 20),
                    "include_metadata": arguments.get("include_metadata", True),
                })
                max_items = arguments.get("max_items")
                data = await client.get_all_data_collect(p, max_items=max_items)

            elif name == "get_suggest":
                arguments = await _auto_normalize_region_args(arguments, client)
                p = SuggestInput.model_validate(arguments)
                data = await client.suggest(p)

            elif name == "get_count_data":
                # --- Build sub-slice (plain dict, camelCase) ---
                sub_dict = None
                if arguments.get("slice_sub_attribute_name") or arguments.get("slice_sub_size") is not None:
                    sub_dict = {
                        "attributeName": arguments.get("slice_sub_attribute_name") or "",
                    }
                    if arguments.get("slice_sub_size") is not None:
                        sub_dict["size"] = int(arguments.get("slice_sub_size"))

                # --- Build attribute slice (plain dict, camelCase) ---
                attr_dict = None
                if (
                    arguments.get("slice_attribute_name")
                    or arguments.get("slice_size") is not None
                    or sub_dict is not None
                ):
                    attr_dict = {
                        "attributeName": arguments.get("slice_attribute_name") or "",
                    }
                    if arguments.get("slice_size") is not None:
                        attr_dict["size"] = int(arguments.get("slice_size"))
                    if sub_dict is not None:
                        # penting: key GraphQL adalah subSliceSetting (camelCase)
                        attr_dict["subSliceSetting"] = sub_dict

                # --- Decide slice_type ---
                slice_type = arguments.get("slice_type")
                if slice_type is None and attr_dict is not None:
                    slice_type = "attribute"

                # --- Assemble slice_setting (plain dict; do not use Pydantic yet) ---
                slice_setting = None
                if slice_type == "dataset":
                    slice_setting = {"type": "dataset"}
                elif slice_type is not None or attr_dict is not None:
                    slice_setting = {"type": slice_type or "attribute"}
                    if attr_dict is not None:
                        # important: GraphQL key is attributeSliceSetting (camelCase)
                        slice_setting["attributeSliceSetting"] = attr_dict

                # --- Normalize region args (same as before) ---
                arguments = await _auto_normalize_region_args(arguments, client)

                # --- Build CountDataInput (PASS-THROUGH dict slice_setting already assembled) ---
                p = CountDataInput.model_validate({
                    "term": arguments.get("term"),
                    "phrase_match": arguments.get("phrase_match"),
                    "prefecture_code": arguments.get("prefecture_code"),
                    "municipality_code": arguments.get("municipality_code"),
                    "address": arguments.get("address"),
                    "catalog_id": arguments.get("catalog_id"),
                    "dataset_id": arguments.get("dataset_id"),
                    "location_rectangle_top_left_lat": arguments.get("location_rectangle_top_left_lat"),
                    "location_rectangle_top_left_lon": arguments.get("location_rectangle_top_left_lon"),
                    "location_rectangle_bottom_right_lat": arguments.get("location_rectangle_bottom_right_lat"),
                    "location_rectangle_bottom_right_lon": arguments.get("location_rectangle_bottom_right_lon"),
                    "location_lat": arguments.get("location_lat"),
                    "location_lon": arguments.get("location_lon"),
                    "location_distance": arguments.get("location_distance"),
                    "slice_setting": slice_setting, 
                })

                data = await client.count_data(p)
                return {
                    "content": [{"type": "text", "text": json.dumps(data)}],
                    "isError": False,
                }


            elif name == "get_mesh":
                p = MeshParams.model_validate(arguments)
                data = await client.get_mesh(
                    dataset_id=p.dataset_id,
                    data_id=p.data_id,
                    mesh_id=p.mesh_id,
                    mesh_code=p.mesh_code,
                )

            elif name == "get_file_download_urls":
                p = FileDownloadURLsInput.model_validate(arguments)
                if p.files:
                    files = [FileRef(id=f.id, original_path=f.original_path) for f in p.files]
                    data = await client.file_download_urls(files=files)
                else:
                    data = await client.file_download_urls_from_data(
                        dataset_id=str(p.dataset_id), data_id=str(p.data_id)  # type: ignore
                    )

            elif name == "get_zipfile_download_url":
                p = ZipfileDownloadURLInput.model_validate(arguments)
                if p.files:
                    files = [FileRef(id=f.id, original_path=f.original_path) for f in p.files]
                    data = await client.zipfile_download_url(files=files)
                else:
                    data = await client.zipfile_download_url_from_data(
                        dataset_id=str(p.dataset_id), data_id=str(p.data_id)  # type: ignore
                    )

            elif name == "get_thumbnail_urls":
                p = ThumbnailURLsInput.model_validate(arguments)
                if p.thumbnails:
                    thumbs = [ThumbnailRef(id=t.id, original_path=t.original_path) for t in p.thumbnails]
                    data = await client.thumbnail_urls(thumbnails=thumbs)
                else:
                    data = await client.thumbnail_urls_from_data(
                        dataset_id=str(p.dataset_id), data_id=str(p.data_id)  # type: ignore
                    )

            elif name == "normalize_codes":
                p = NormalizeCodesInput.model_validate(arguments)
                res = await client.normalize_codes(p)
                data = res.dict()

            else:
                raise ValueError(f"Unknown tool: {name}")

        text = json.dumps(data, ensure_ascii=False)
        if len(text.encode("utf-8")) > 1024 * 1024:
            text = text[:1024 * 512] + "\n...<truncated>"
        logger.info("tool_done", extra={"rid": rid, "tool": name, "elapsed_ms": t.elapsed_ms})

        return [types.TextContent(type="text", text=text)]

    finally:
        await client.close()


async def _main() -> None:
    async with stdio_server() as (read, write):
        caps = server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
        )

        init_opts = InitializationOptions(
            server_name="mlit-mcp",
            server_version="0.1.0",
            capabilities=caps
        )

        await server.run(read, write, init_opts)


if __name__ == "__main__":
    anyio.run(_main)
