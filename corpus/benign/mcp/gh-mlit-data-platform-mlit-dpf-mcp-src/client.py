import os
import aiohttp
import asyncio
import time
import unicodedata
import json
from typing import Any, Dict, List, Optional, AsyncIterator, Tuple
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from .config import load_settings
from .utils import logger, RateLimiter, new_request_id
from .schemas import (
    GetAllDataInput, GetAllDataItem,
    SuggestInput,
    CountSliceSettingInput, CountDataInput,
    FileRef,
    ThumbnailRef,
    NormalizeCodesInput, NormalizeCodesOutput, MunicipalityCandidate,
)


class TransientHttpError(RuntimeError):
    """Error (429/5xx/network/timeout) -> eligible for retry."""
    pass


class MLITClient:
    """
    GraphQL client for MLIT Data Platform.
    - Endpoint: POST https://data-platform.mlit.go.jp/api/v1/
    - Header:  apikey: <MLIT_API_KEY>
    """

    def __init__(self):
        self.s = load_settings()
        self._session: Optional[aiohttp.ClientSession] = None
        self._limiter = RateLimiter(self.s.rps)

        # --- caches for normalization ---
        self._pref_cache: Optional[Tuple[float, List[Dict[str, str]]]] = None
        self._muni_cache: Dict[str, Tuple[float, List[Dict[str, str]]]] = {}
        self._cache_ttl_sec = 600  # 10 minutes

    async def _ensure(self):
        if self._session is None or self._session.closed:
            try:
                total_timeout = float(os.getenv("MLIT_TIMEOUT_S", str(self.s.timeout_s)))
            except Exception:
                total_timeout = self.s.timeout_s
            timeout = aiohttp.ClientTimeout(
                total=total_timeout,
                # sock_read=total_timeout,
            )
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    # ---------- GraphQL helper ----------
    async def post_query(self, query: str) -> Dict[str, Any]:
        """
        Send GraphQL query and return the 'data' dict.
        - Log query if MLIT_DEBUG_QUERY=1
        - Log response details if MLIT_DEBUG_RESP=1
        - Retry on 429/5xx + timeout/network errors
        """
        await self._ensure()
        await self._limiter.acquire()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "apikey": self.s.api_key,
        }
        payload = {"query": query}
        assert self._session is not None

        debug_query = os.getenv("MLIT_DEBUG_QUERY") == "1"
        debug_resp = os.getenv("MLIT_DEBUG_RESP") == "1"
        body_limit = int(os.getenv("MLIT_LOG_BODY_LIMIT", "4000"))

        rid = new_request_id()

        if debug_query:
            q_preview = query if len(query) <= body_limit else query[:body_limit] + "\n...<truncated>"
            logger.info("gql_query_out", extra={"rid": rid, "query": q_preview})

        retryer = AsyncRetrying(
            retry=retry_if_exception_type(TransientHttpError),
            wait=wait_exponential(multiplier=1, min=self.s.backoff_base_s, max=8),
            stop=stop_after_attempt(1 + self.s.max_retries),
            reraise=True,
        )

        async for attempt in retryer:
            with attempt:
                t0 = time.perf_counter()
                try:
                    async with self._session.post(
                        str(self.s.base_url),
                        headers=headers,
                        json=payload,
                        compress=True,
                    ) as resp:
                        elapsed_ms = (time.perf_counter() - t0) * 1000.0

                        # Transient HTTP status
                        if resp.status in (429, 500, 502, 503, 504):
                            text = await resp.text()
                            if debug_resp:
                                preview = text if len(text) <= body_limit else text[:body_limit] + "\n...<truncated>"
                                logger.info(
                                    "gql_resp_transient",
                                    extra={
                                        "rid": rid,
                                        "status": resp.status,
                                        "elapsed_ms": round(elapsed_ms, 2),
                                        "content_length": resp.headers.get("Content-Length"),
                                        "body_preview": preview,
                                    },
                                )
                            raise TransientHttpError(f"HTTP {resp.status}")

                        # Non-transient error: still log to know what happened
                        try:
                            resp.raise_for_status()
                        except aiohttp.ClientResponseError as cre:
                            text = await resp.text()
                            preview = text if len(text) <= body_limit else text[:body_limit] + "\n...<truncated>"
                            logger.warning(
                                "gql_resp_error",
                                extra={
                                    "rid": rid,
                                    "status": resp.status,
                                    "elapsed_ms": round(elapsed_ms, 2),
                                    "error": str(cre),
                                    "body_preview": preview,
                                },
                            )
                            raise

                        # Read as text first so it can be logged
                        resp_text = await resp.text()
                        if debug_resp:
                            preview = resp_text if len(resp_text) <= body_limit else resp_text[:body_limit] + "\n...<truncated>"
                            logger.info(
                                "gql_resp_ok",
                                extra={
                                    "rid": rid,
                                    "status": resp.status,
                                    "elapsed_ms": round(elapsed_ms, 2),
                                    "content_length": resp.headers.get("Content-Length"),
                                    "body_size": len(resp_text),
                                    "body_preview": preview,
                                },
                            )

                        # Parse JSON and check 'data' field
                        try:
                            data_json = json.loads(resp_text)
                        except json.JSONDecodeError as je:
                            logger.warning(
                                "gql_resp_json_decode_error",
                                extra={"rid": rid, "error": str(je)},
                            )
                            raise

                        if "data" not in data_json:
                            logger.warning("gql_resp_no_data_field", extra={"rid": rid})
                            raise RuntimeError("unexpected response: no 'data'")

                        return data_json["data"]

                except (asyncio.TimeoutError, aiohttp.ClientError) as neterr:
                    # Treat as transient (will be retried by tenacity)
                    logger.warning(
                        "gql_network_or_timeout",
                        extra={"rid": rid, "error": str(neterr)},
                    )
                    raise TransientHttpError(str(neterr)) from neterr

    # ---------- field presets ----------
    def _fields_min(self) -> str:
        return "id title lat lon dataset_id"

    def _fields_basic(self) -> str:
        return "id title lat lon year dataset_id catalog_id"

    def _fields_detail(self) -> str:
        return "id title lat lon year theme metadata dataset_id catalog_id hasThumbnail"

    # ---------- builders ----------
    def build_search(
        self,
        term: Optional[str] = None,
        first: int = 0,
        size: int = 50,
        sort_attribute_name: Optional[str] = None,
        sort_order: Optional[str] = None,
        phrase_match: bool = True,
        location_filter: Optional[str] = None,
        attribute_filter: Optional[str] = None,
        fields: Optional[str] = None,
    ) -> str:
        parts: List[str] = [f"first: {int(first)}"]
        if size:
            parts.append(f"size: {int(size)}")
        if term is not None:
            escaped = term.replace('"', '\\"')
            parts.append(f'term: "{escaped}"')
        if phrase_match:
            parts.append("phraseMatch: true")
        if sort_attribute_name:
            escaped = sort_attribute_name.replace('"', '\\"')
            parts.append(f'sortAttributeName: "{escaped}"')
        if sort_order:
            escaped = sort_order.replace('"', '\\"')
            parts.append(f'sortOrder: "{escaped}"')
        if attribute_filter:
            parts.append(f"attributeFilter: {attribute_filter}")
        if location_filter:
            parts.append(f"locationFilter: {location_filter}")

        fields = fields or self._fields_basic()
        return f"""
        query {{
          search({", ".join(parts)}) {{
            totalNumber
            searchResults {{ {fields} }}
          }}
        }}
        """.strip()

    def build_data_catalog(
        self,
        *,
        ids: Optional[List[str]] = None,
        fields: Optional[str] = None,
        include_datasets: bool = True,
    ) -> str:
        if ids is None:
            ids_arg = "null"
        else:
            esc_list = []
            for i in ids:
                esc_i = i.replace('"', '\\"')
                esc_list.append(f'"{esc_i}"')
            ids_arg = "[" + ", ".join(esc_list) + "]"

        base_fields = fields or "id title"
        if include_datasets:
            out_fields = f"""{base_fields}
                datasets {{
                  id
                  title
                  data_count
                }}"""
        else:
            out_fields = base_fields

        return f"""
        query {{
          dataCatalog(IDs: {ids_arg}) {{
            {out_fields}
          }}
        }}
        """.strip()

    def build_get_all_data(
        self,
        *,
        size: int = 1000,
        term: Optional[str] = None,
        phrase_match: Optional[bool] = None,
        attribute_filter: Optional[str] = None,
        location_filter: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> str:
        if size < 1:
            size = 1
        if size > 1000:
            size = 1000

        parts: List[str] = [f"size: {int(size)}"]

        if next_token:
            esc = next_token.replace('"', '\\"')
            parts.append(f'nextDataRequestToken: "{esc}"')
        else:
            if term is not None:
                esc_term = term.replace('"', '\\"')
                parts.append(f'term: "{esc_term}"')
            if phrase_match is not None:
                parts.append(f'phraseMatch: {"true" if phrase_match else "false"}')
            if attribute_filter:
                parts.append(f"attributeFilter: {attribute_filter}")
            if location_filter:
                parts.append(f"locationFilter: {location_filter}")

        return f"""
        query {{
          getAllData({", ".join(parts)}) {{
            nextDataRequestToken
            data {{
              id
              title
              metadata
            }}
          }}
        }}
        """.strip()

    # ----- SUGGEST -----
    def build_suggest(
        self,
        *,
        term: str,
        phrase_match: Optional[bool] = None,
        attribute_filter: Optional[str] = None,
        location_filter: Optional[str] = None,
    ) -> str:
        parts: List[str] = []

        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'

        parts.append(f"term: {q(term)}")
        if phrase_match is not None:
            parts.append(f'phraseMatch: {"true" if phrase_match else "false"}')
        if location_filter:
            parts.append(f"locationFilter: {location_filter}")
        if attribute_filter:
            parts.append(f"attributeFilter: {attribute_filter}")

        return f"""
        query {{
          suggest({", ".join(parts)}) {{
            totalNumber
            suggestions {{
              name
              cnt
            }}
          }}
        }}
        """.strip()

    # ===== helpers: attribute name/value handling =====
    def _normalize_attr_name(self, name: str) -> str:
        """
        Normalize attribute name with intelligent namespace detection:
        - If already has namespace (contains ':'), return as-is
        - If matches known DPF attributes, add DPF: prefix
        - Otherwise return as-is (assume user knows the correct namespace)
        """
        if not name:
            return name
        
        # Already has namespace prefix
        if ":" in name:
            return name
        
        # Known DPF attributes - add prefix
        dpf_attrs = {
            "dataset_id", "catalog_id", "prefecture_code", 
            "municipality_code", "year", "address", "title",
            "lat", "lon", "theme"
        }
        
        if name in dpf_attrs:
            return f"DPF:{name}"
        
        # Return as-is - user must provide correct namespace
        return name

    def _token_for_code_value(self, s: str) -> str:
        """
        Literal GraphQL for code (prefecture/municipality).
        - NFKC normalization (full-width '１３' -> '13')
        - If pure digit & no leading zero -> unquoted number
        - Otherwise -> quoted string
        """
        if s is None:
            return '""'
        s_norm = unicodedata.normalize("NFKC", str(s)).strip()
        if s_norm.isdigit() and not (len(s_norm) > 1 and s_norm[0] == "0"):
            return s_norm
        return '"' + s_norm.replace('"', '\\"') + '"'

    # ----- COUNT DATA (helpers that accept model/dict) -----
    def _build_attribute_slice_any(self, s: Any) -> str:
        if isinstance(s, dict):
            name = s.get("attributeName") or s.get("attribute_name") or ""
            size = s.get("size")
            sub  = s.get("subSliceSetting") or s.get("sub_slice_setting")
        else:
            name = getattr(s, "attribute_name", "") or getattr(s, "attributeName", "") or ""
            size = getattr(s, "size", None)
            sub  = getattr(s, "sub_slice_setting", None) or getattr(s, "subSliceSetting", None)

        attr = self._normalize_attr_name(name or "")
        escaped_attr = attr.replace('"', '\\"')
        parts: List[str] = [f'attributeName: "{escaped_attr}"']
        if size is not None:
            parts.append(f"size: {int(size)}")
        if sub is not None:
            parts.append(f"subSliceSetting: {{ {self._build_attribute_slice_any(sub)} }}")
        return ", ".join(parts)

    def _build_slice_setting(self, s: Any) -> str:
        if s is None:
            return "{}"

        if isinstance(s, dict):
            typ  = s.get("type") or s.get("type_")
            attr = s.get("attributeSliceSetting") or s.get("attribute_slice_setting")
        else:
            typ  = getattr(s, "type_", None) or getattr(s, "type", None)
            attr = getattr(s, "attribute_slice_setting", None) or getattr(s, "attributeSliceSetting", None)

        parts: List[str] = []
        if typ:
            # NOTE: MLIT schema accepts string for this field (not enum)
            parts.append(f'type: "{typ}"')
        # if dataset, do not include attributeSliceSetting
        if attr is not None and (typ or "attribute") != "dataset":
            parts.append(f"attributeSliceSetting: {{ {self._build_attribute_slice_any(attr)} }}")

        return "{ " + ", ".join(parts) + " }" if parts else "{}"


    def build_count_data(
        self,
        *,
        term: Optional[str] = None,
        phrase_match: Optional[bool] = None,
        attribute_filter: Optional[str] = None,
        location_filter: Optional[str] = None,
        slice_setting: Optional[CountSliceSettingInput] = None,
    ) -> str:
        parts: List[str] = []

        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'

        if term is not None:
            parts.append(f"term: {q(term)}")
        if phrase_match is not None:
            parts.append(f'phraseMatch: {"true" if phrase_match else "false"}')
        if location_filter:
            parts.append(f"locationFilter: {location_filter}")
        if attribute_filter:
            parts.append(f"attributeFilter: {attribute_filter}")
        if slice_setting is not None:
            parts.append(f"sliceSetting: {self._build_slice_setting(slice_setting)}")

        return f"""
        query {{
          countData({", ".join(parts)}) {{
            dataCount
            slices {{
              attributeName
              attributeValue
              dataCount
              slices {{
                attributeName
                attributeValue
                dataCount
                slices {{
                  attributeName
                  attributeValue
                  dataCount
                }}
              }}
            }}
          }}
        }}
        """.strip()

    # ----- MESH -----
    def build_mesh(self, *, dataset_id: str, data_id: str, mesh_id: str, mesh_code: str) -> str:
        ds = dataset_id.replace('"', '\\"')
        di = data_id.replace('"', '\\"')
        mid = mesh_id.replace('"', '\\"')
        mcode = mesh_code.replace('"', '\\"')
        return f"""
        query {{
          mesh(
            dataSetID: "{ds}"
            dataID: "{di}"
            meshID: "{mid}"
            meshCode: "{mcode}"
          )
        }}
        """.strip()

    # ----- FILE DOWNLOAD URLs -----
    def build_file_download_urls(self, *, files: List[FileRef]) -> str:
        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'
        items = ", ".join(
            "{ id: " + q(f.id) + ", original_path: " + q(f.original_path) + " }" for f in files
        )
        return f"""
        query {{
          fileDownloadURLs(files: [{items}]) {{
            ID
            URL
          }}
        }}
        """.strip()

    # ----- ZIPFILE DOWNLOAD URL -----
    def build_zipfile_download_url(self, *, files: List[FileRef]) -> str:
        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'
        items = ", ".join(
            "{ id: " + q(f.id) + ", original_path: " + q(f.original_path) + " }" for f in files
        )
        return f"""
        query {{
          zipfileDownloadURL(files: [{items}])
        }}
        """.strip()

    # ----- THUMBNAIL URLs -----
    def build_thumbnail_urls(self, *, thumbnails: List[ThumbnailRef]) -> str:
        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'
        items = ", ".join(
            "{ id: " + q(t.id) + ", original_path: " + q(t.original_path) + " }" for t in thumbnails
        )
        return f"""
        query {{
          thumbnailURLs(thumbnails: [{items}]) {{
            ID
            URL
          }}
        }}
        """.strip()

    # ----- SINGLE ATTRIBUTE FILTER (operator always 'is') -----
    def make_single_attribute_filter(self, attribute_name: str, attribute_value: Any) -> str:
        """
        Build a single attribute filter: { attributeName: "<DPF:name>", is: <value> }
        - Auto-prefix "DPF:" for common attribute names
        - Prefecture/municipality codes -> numeric token if possible
        - Otherwise -> quoted string
        """
        name_norm = self._normalize_attr_name(attribute_name or "")

        if name_norm in ("DPF:prefecture_code", "DPF:municipality_code"):
            val_token = self._token_for_code_value(str(attribute_value))
        else:
            val_token = '"' + str(attribute_value).replace('"', '\\"') + '"'

        escaped_name = name_norm.replace('"', '\\"')
        return "{ " + f'attributeName: "{escaped_name}", ' + f"is: {val_token}" + " }"

    # ---------- location & attribute helpers (misc) ----------
    def make_rectangle_filter(self, tl_lat: float, tl_lon: float, br_lat: float, br_lon: float) -> str:
        # Normalize to NW (top-left) and SE (bottom-right)
        top = max(tl_lat, br_lat)
        bottom = min(tl_lat, br_lat)
        left = min(tl_lon, br_lon)
        right = max(tl_lon, br_lon)
        return (
            "{"
            f"rectangle: {{ topLeft: {{ lat: {top}, lon: {left} }}, "
            f"bottomRight: {{ lat: {bottom}, lon: {right} }} }}"
            "}"
        )

    def make_geodistance_filter(self, lat: float, lon: float, distance_m: float) -> str:
        # MLIT spec: geoDistance has lat/lon/distance directly (no center, no circle)
        return (
            "{"
            f"geoDistance: {{ lat: {lat}, lon: {lon}, distance: {distance_m} }}"
            "}"
        )

    def make_attribute_filter_for_countdata(
        self,
        *,
        prefecture_code: Optional[str] = None,
        municipality_code: Optional[str] = None,
        address: Optional[str] = None,
        catalog_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> Optional[str]:
        clauses: List[str] = []

        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'

        if dataset_id:
            clauses.append('{ attributeName: "DPF:dataset_id", is: ' + q(dataset_id) + " }")
        if catalog_id:
            clauses.append('{ attributeName: "DPF:catalog_id", is: ' + q(catalog_id) + " }")
        if prefecture_code:
            clauses.append('{ attributeName: "DPF:prefecture_code", is: ' + q(str(prefecture_code)) + " }")
        if municipality_code:
            clauses.append('{ attributeName: "DPF:municipality_code", is: ' + q(str(municipality_code)) + " }")
        if address:
            # countData: official operator is always 'is'
            clauses.append('{ attributeName: "DPF:address", is: ' + q(address) + " }")

        if not clauses:
            return None
        if len(clauses) == 1:
            # Return the single object as is (DO NOT wrap again to avoid {{ ... }})
            return clauses[0]
        return "{ AND: [" + ", ".join(clauses) + "] }"

    def make_attribute_filter_strict_for_get_all_data(
        self,
        *,
        prefecture_code: Optional[str] = None,
        municipality_code: Optional[str] = None,
        address: Optional[str] = None,
        catalog_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> Optional[str]:
        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'

        conds: List[str] = []
        if dataset_id:
            conds.append('{ attributeName: "DPF:dataset_id", is: ' + q(dataset_id) + " }")
        if catalog_id:
            conds.append('{ attributeName: "DPF:catalog_id", is: ' + q(catalog_id) + " }")
        if prefecture_code:
            conds.append('{ attributeName: "DPF:prefecture_code", is: ' + q(str(prefecture_code)) + " }")
        if municipality_code:
            conds.append('{ attributeName: "DPF:municipality_code", is: ' + q(str(municipality_code)) + " }")
        if address:
            conds.append('{ attributeName: "DPF:address", is: ' + q(address) + " }")

        if not conds:
            return None
        return "{ AND: [" + ", ".join(conds) + "] }"

    # >>> attribute filter tailored for search_by_attribute (numeric codes unquoted)
    def make_attribute_filter_for_search(
        self,
        *,
        prefecture_code: Optional[str] = None,
        municipality_code: Optional[str] = None,
        address: Optional[str] = None,
        catalog_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> Optional[str]:
        clauses: List[str] = []

        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'

        if dataset_id:
            clauses.append('{ attributeName: "DPF:dataset_id", is: ' + q(dataset_id) + " }")
        if catalog_id:
            clauses.append('{ attributeName: "DPF:catalog_id", is: ' + q(catalog_id) + " }")
        if prefecture_code:
            clauses.append('{ attributeName: "DPF:prefecture_code", is: ' + self._token_for_code_value(str(prefecture_code)) + " }")
        if municipality_code:
            clauses.append('{ attributeName: "DPF:municipality_code", is: ' + self._token_for_code_value(str(municipality_code)) + " }")
        if address:
            clauses.append('{ attributeName: "DPF:address", similar: ' + q(address) + " }")

        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return "{ AND: [" + ", ".join(clauses) + "] }"

    # ---------- Public high-level methods ----------
    async def search_keyword(self, term: str, **kw) -> Dict[str, Any]:
        q = self.build_search(term=term, **kw)
        return await self.post_query(q)

    async def search_by_rectangle(
        self, tl_lat: float, tl_lon: float, br_lat: float, br_lon: float, **kw
    ) -> Dict[str, Any]:
        loc = self.make_rectangle_filter(tl_lat, tl_lon, br_lat, br_lon)
        q = self.build_search(location_filter=loc, **kw)
        return await self.post_query(q)

    async def search_by_point(self, lat: float, lon: float, distance_m: float, **kw) -> Dict[str, Any]:
        loc = self.make_geodistance_filter(lat, lon, distance_m)
        q = self.build_search(location_filter=loc, **kw)
        return await self.post_query(q)

    # ==== (GraphQL): operator 'is' ====
    async def search_by_attribute_raw(
        self,
        *,
        term: Optional[str] = None,
        first: int = 0,
        size: int = 20,
        phrase_match: bool = True,
        attribute_name: str,
        attribute_value: Any,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        af = self.make_single_attribute_filter(attribute_name, attribute_value)
        effective_term = term if term is not None else "" 
        q = self.build_search(
            term=effective_term,
            first=first,
            size=size,
            phrase_match=phrase_match,
            attribute_filter=af,
            fields=fields or self._fields_basic(),
        )
        return await self.post_query(q)

    async def get_data(self, dataset_id: str, data_id: str) -> Dict[str, Any]:
        q = f"""
        query {{
        data(dataSetID: "{dataset_id}", dataID: "{data_id}") {{
            totalNumber
            getDataResults {{
            id
            title
            metadata
            files {{ id original_path }}
            hasThumbnail
            tileset {{
                url
                altitude_offset_meters
            }}
            }}
        }}
        }}
        """.strip()
        return await self.post_query(q)

    async def get_data_summary(self, dataset_id: str, data_id: str) -> Dict[str, Any]:
        q = f"""
        query {{
          data(dataSetID: "{dataset_id}", dataID: "{data_id}") {{
            totalNumber
            getDataResults {{
              id
              title
            }}
          }}
        }}
        """.strip()
        return await self.post_query(q)

    async def get_data_catalog_summary(self) -> Dict[str, Any]:
        q = """
        query {
          dataCatalog(IDs: null) {
            id
            title
          }
        }
        """.strip()
        return await self.post_query(q)

    async def get_data_catalog(
        self,
        *,
        ids: Optional[List[str]] = None,
        minimal: bool = False,
        include_datasets: bool = True,
    ) -> Dict[str, Any]:
        fields = "id title" if minimal else "id title"
        q = self.build_data_catalog(ids=ids, fields=fields, include_datasets=include_datasets)
        return await self.post_query(q)

    async def get_prefectures(self) -> Dict[str, Any]:
        q = """
        query {
          prefecture {
            code
            name
          }
        }
        """.strip()
        return await self.post_query(q)

    async def get_municipalities(
        self,
        pref_codes: Optional[List[str]] = None,
        muni_codes: Optional[List[str]] = None,
        *,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not pref_codes and not muni_codes:
            raise ValueError("Either pref_codes or muni_codes must be provided")

        def q(s: str) -> str:
            return '"' + s.replace('"', '\\"') + '"'

        args: List[str] = []
        if pref_codes:
            pref = "[" + ", ".join(q(c) for c in pref_codes) + "]"
            args.append(f"prefCodes: {pref}")
        if muni_codes:
            muni = "[" + ", ".join(q(c) for c in muni_codes) + "]"
            args.append(f"muniCodes: {muni}")

        default_fields = ["code_as_string", "prefecture_code", "name"]
        out_fields = " ".join(fields if fields else default_fields)

        ql = f"""
        query {{
          municipalities({", ".join(args)}) {{
            {out_fields}
          }}
        }}
        """.strip()
        return await self.post_query(ql)

    # ---------- getAllData iterator/collector ----------
    async def get_all_data_iter(self, params: GetAllDataInput) -> AsyncIterator[List[GetAllDataItem]]:
        token: Optional[str] = None
        batches = 0

        attr_filter_str = self.make_attribute_filter_strict_for_get_all_data(
            prefecture_code=params.prefecture_code,
            municipality_code=params.municipality_code,
            address=params.address,
            catalog_id=params.catalog_id,
            dataset_id=params.dataset_id,
        )

        loc_filter_str: Optional[str] = None
        if all(v is not None for v in [
            params.location_rectangle_top_left_lat,
            params.location_rectangle_top_left_lon,
            params.location_rectangle_bottom_right_lat,
            params.location_rectangle_bottom_right_lon
        ]):
            tl_lat = float(params.location_rectangle_top_left_lat)  # type: ignore
            tl_lon = float(params.location_rectangle_top_left_lon)  # type: ignore
            br_lat = float(params.location_rectangle_bottom_right_lat)  # type: ignore
            br_lon = float(params.location_rectangle_bottom_right_lon)  # type: ignore
            if not (-90 <= tl_lat <= 90 and -180 <= tl_lon <= 180 and -90 <= br_lat <= 90 and -180 <= br_lon <= 180):
                raise ValueError("Invalid rectangle coordinates")
            loc_filter_str = self.make_rectangle_filter(tl_lat, tl_lon, br_lat, br_lon)

        effective_first_term: Optional[str] = params.term
        if effective_first_term is None:
            if attr_filter_str is not None or loc_filter_str is not None:
                effective_first_term = ""

        while True:
            if batches >= params.max_batches:
                break

            if token:
                q = self.build_get_all_data(size=params.size, next_token=token)
            else:
                q = self.build_get_all_data(
                    size=params.size,
                    term=effective_first_term,
                    phrase_match=params.phrase_match,
                    attribute_filter=attr_filter_str,
                    location_filter=loc_filter_str,
                    next_token=None,
                )

            data = await self.post_query(q)
            node = data.get("getAllData") or {}
            raw_items = node.get("data") or []
            token = node.get("nextDataRequestToken")

            batch: List[GetAllDataItem] = []
            for it in raw_items:
                item = GetAllDataItem(
                    id=str(it.get("id")),
                    title=it.get("title"),
                    metadata=(it.get("metadata") if params.include_metadata else None),
                )
                batch.append(item)

            yield batch

            batches += 1
            if not batch or not token:
                break

    async def get_all_data_collect(
        self,
        params: GetAllDataInput,
        *,
        max_items: Optional[int] = None
    ) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = []
        count = 0
        batches = 0

        async for batch in self.get_all_data_iter(params):
            rows = [x.dict() for x in batch]
            items.extend(rows)
            count += len(rows)
            batches += 1

            if max_items is not None and count >= max_items:
                break

            if len(str(items).encode("utf-8")) > 900_000:
                logger.warning("get_all_data_collect: response approaching size cap, truncating further collection")
                break

        return {"batches": batches, "count": count, "items": items}

    # ----- SUGGEST -----
    async def suggest(self, params: SuggestInput) -> Dict[str, Any]:
        attr_filter = self.make_attribute_filter_for_countdata(
            prefecture_code=params.prefecture_code,
            municipality_code=params.municipality_code,
            address=params.address,
            catalog_id=params.catalog_id,
            dataset_id=params.dataset_id,
        )

        loc_filter = None
        if all(v is not None for v in [
            params.location_rectangle_top_left_lat,
            params.location_rectangle_top_left_lon,
            params.location_rectangle_bottom_right_lat,
            params.location_rectangle_bottom_right_lon
        ]):
            loc_filter = self.make_rectangle_filter(
                float(params.location_rectangle_top_left_lat),   # type: ignore
                float(params.location_rectangle_top_left_lon),   # type: ignore
                float(params.location_rectangle_bottom_right_lat),  # type: ignore
                float(params.location_rectangle_bottom_right_lon),  # type: ignore
            )

        q = self.build_suggest(
            term=params.term,
            phrase_match=params.phrase_match,
            attribute_filter=attr_filter,
            location_filter=loc_filter,
        )
        return await self.post_query(q)

    # ----- COUNT DATA -----
    async def count_data(self, params: CountDataInput) -> Dict[str, Any]:
        attr_filter = self.make_attribute_filter_for_countdata(
            prefecture_code=params.prefecture_code,
            municipality_code=params.municipality_code,
            address=params.address,
            catalog_id=params.catalog_id,
            dataset_id=params.dataset_id,
        )

        loc_filter = None
        if all(v is not None for v in [
            params.location_rectangle_top_left_lat,
            params.location_rectangle_top_left_lon,
            params.location_rectangle_bottom_right_lat,
            params.location_rectangle_bottom_right_lon
        ]):
            loc_filter = self.make_rectangle_filter(
                float(params.location_rectangle_top_left_lat),   # type: ignore
                float(params.location_rectangle_top_left_lon),   # type: ignore
                float(params.location_rectangle_bottom_right_lat),  # type: ignore
                float(params.location_rectangle_bottom_right_lon),  # type: ignore
            )
        elif all(v is not None for v in [
            params.location_lat, params.location_lon, params.location_distance
        ]):
            loc_filter = self.make_geodistance_filter(
                float(params.location_lat),   # type: ignore
                float(params.location_lon),   # type: ignore
                float(params.location_distance),  # type: ignore
            )

        effective_term: Optional[str] = params.term
        if effective_term is None and (attr_filter is not None or loc_filter is not None):
            effective_term = ""

        # BRIDGE: top-level slice_* → slice_setting (kalau belum ada)
        slice_setting_obj = params.slice_setting
        if slice_setting_obj is None:
            st = (getattr(params, "slice_type", None) or "").strip().lower()
            if st == "dataset":
                slice_setting_obj = {"type": "dataset"}
            elif st == "attribute":
                # Build attributeSliceSetting from top-level fields
                name = self._normalize_attr_name(getattr(params, "slice_attribute_name", "") or "")
                size = getattr(params, "slice_size", None)
                sub_name = self._normalize_attr_name(getattr(params, "slice_sub_attribute_name", "") or "")
                sub_size = getattr(params, "slice_sub_size", None)

                attr_block: Dict[str, Any] = {}
                if name:
                    attr_block["attributeName"] = name
                if isinstance(size, int):
                    attr_block["size"] = int(size)

                sub_block: Dict[str, Any] = {}
                if sub_name:
                    sub_block["attributeName"] = sub_name
                if isinstance(sub_size, int):
                    sub_block["size"] = int(sub_size)
                if sub_block:
                    attr_block["subSliceSetting"] = sub_block

                slice_setting_obj = (
                    {"type": "attribute", "attributeSliceSetting": attr_block}
                    if attr_block else
                    {"type": "attribute"}
                )

        q = self.build_count_data(
            term=effective_term,
            phrase_match=params.phrase_match,
            attribute_filter=attr_filter,
            location_filter=loc_filter,
            slice_setting=slice_setting_obj,
        )
        return await self.post_query(q)

    # ----- MESH -----
    async def get_mesh(self, *, dataset_id: str, data_id: str, mesh_id: str, mesh_code: str) -> Dict[str, Any]:
        q = self.build_mesh(dataset_id=dataset_id, data_id=data_id, mesh_id=mesh_id, mesh_code=mesh_code)
        return await self.post_query(q)

    # ----- FILES / THUMBNAILS helpers & public -----
    async def get_data_files(self, *, dataset_id: str, data_id: str) -> List[FileRef]:
        q = f"""
        query {{
          data(dataSetID: "{dataset_id}", dataID: "{data_id}") {{
            totalNumber
            getDataResults {{
              id
              files {{ id original_path }}
            }}
          }}
        }}
        """.strip()
        data = await self.post_query(q)
        node = data.get("data") or {}
        results = (node.get("getDataResults") or [])
        files: List[FileRef] = []
        for r in results:
            for f in (r.get("files") or []):
                if f and f.get("id") and f.get("original_path"):
                    files.append(FileRef(id=str(f["id"]), original_path=str(f["original_path"])))
        return files

    async def get_data_thumbnails(self, *, dataset_id: str, data_id: str) -> List[ThumbnailRef]:
        q = f"""
        query {{
          data(dataSetID: "{dataset_id}", dataID: "{data_id}") {{
            totalNumber
            getDataResults {{
              id
              thumbnails {{ id original_path }}
            }}
          }}
        }}
        """.strip()
        data = await self.post_query(q)
        node = data.get("data") or {}
        results = (node.get("getDataResults") or [])
        thumbs: List[ThumbnailRef] = []
        for r in results:
            for t in (r.get("thumbnails") or []):
                if t and t.get("id") and t.get("original_path"):
                    thumbs.append(ThumbnailRef(id=str(t["id"]), original_path=str(t["original_path"])))
        return thumbs

    async def file_download_urls(self, *, files: List[FileRef]) -> Dict[str, Any]:
        if not files:
            return {"fileDownloadURLs": []}
        q = self.build_file_download_urls(files=files)
        return await self.post_query(q)

    async def file_download_urls_from_data(self, *, dataset_id: str, data_id: str) -> Dict[str, Any]:
        files = await self.get_data_files(dataset_id=dataset_id, data_id=data_id)
        if not files:
            return {"fileDownloadURLs": []}
        return await self.file_download_urls(files=files)

    async def zipfile_download_url(self, *, files: List[FileRef]) -> Dict[str, Any]:
        if not files:
            return {"zipfileDownloadURL": None}
        q = self.build_zipfile_download_url(files=files)
        return await self.post_query(q)

    async def zipfile_download_url_from_data(self, *, dataset_id: str, data_id: str) -> Dict[str, Any]:
        files = await self.get_data_files(dataset_id=dataset_id, data_id=data_id)
        if not files:
            return {"zipfileDownloadURL": None}
        return await self.zipfile_download_url(files=files)

    async def thumbnail_urls(self, *, thumbnails: List[ThumbnailRef]) -> Dict[str, Any]:
        if not thumbnails:
            return {"thumbnailURLs": []}
        q = self.build_thumbnail_urls(thumbnails=thumbnails)
        return await self.post_query(q)

    async def thumbnail_urls_from_data(self, *, dataset_id: str, data_id: str) -> Dict[str, Any]:
        thumbs = await self.get_data_thumbnails(dataset_id=dataset_id, data_id=data_id)
        if not thumbs:
            return {"thumbnailURLs": []}
        return await self.thumbnail_urls(thumbnails=thumbs)

    # ==============================
    # NORMALIZE CODES
    # ==============================
    def _now(self) -> float:
        return time.time()

    def _fresh(self, ts: float) -> bool:
        return (self._now() - ts) < self._cache_ttl_sec

    async def _load_pref_list(self) -> List[Dict[str, str]]:
        if self._pref_cache and self._fresh(self._pref_cache[0]):
            return self._pref_cache[1]
        data = await self.get_prefectures()
        rows = data.get("prefecture") or []
        out = [{"code": str(r.get("code")), "name": str(r.get("name"))} for r in rows if r]
        self._pref_cache = (self._now(), out)
        return out

    async def _load_muni_list(self, pref_code: str) -> List[Dict[str, str]]:
        ent = self._muni_cache.get(pref_code)
        if ent and self._fresh(ent[0]):
            return ent[1]
        data = await self.get_municipalities(pref_codes=[pref_code])
        rows = data.get("municipalities") or []
        out = [{
            "code_as_string": str(r.get("code_as_string")),
            "name": str(r.get("name")),
            "prefecture_code": str(r.get("prefecture_code")),
        } for r in rows if r]
        self._muni_cache[pref_code] = (self._now(), out)
        return out

    def _nfkc(self, s: str) -> str:
        return unicodedata.normalize("NFKC", s)

    def _strip_pref_suffix(self, s: str) -> str:
        return s.rstrip("都道府県")

    def _canon(self, s: str) -> str:
        s2 = self._nfkc(s.strip())
        return s2.lower()

    def _pref_romaji_map(self) -> Dict[str, str]:
        return {
            "hokkaido": "北海道",
            "aomori": "青森県",
            "iwate": "岩手県",
            "miyagi": "宮城県",
            "akita": "秋田県",
            "yamagata": "山形県",
            "fukushima": "福島県",
            "ibaraki": "茨城県",
            "tochigi": "栃木県",
            "gunma": "群馬県",
            "saitama": "埼玉県",
            "chiba": "千葉県",
            "tokyo": "東京都",
            "kanagawa": "神奈川県",
            "niigata": "新潟県",
            "toyama": "富山県",
            "ishikawa": "石川県",
            "fukui": "福井県",
            "yamanashi": "山梨県",
            "nagano": "長野県",
            "gifu": "岐阜県",
            "shizuoka": "静岡県",
            "aichi": "愛知県",
            "mie": "三重県",
            "shiga": "滋賀県",
            "kyoto": "京都府",
            "osaka": "大阪府",
            "hyogo": "兵庫県",
            "nara": "奈良県",
            "wakayama": "和歌山県",
            "tottori": "鳥取県",
            "shimane": "島根県",
            "okayama": "岡山県",
            "hiroshima": "広島県",
            "yamaguchi": "山口県",
            "tokushima": "徳島県",
            "kagawa": "香川県",
            "ehime": "愛媛県",
            "kochi": "高知県",
            "fukuoka": "福岡県",
            "saga": "佐賀県",
            "nagasaki": "長崎県",
            "oita": "大分県",
            "miyazaki": "宮崎県",
            "kagoshima": "鹿児島県",
            "okinawa": "沖縄県",
        }

    async def normalize_codes(self, params: NormalizeCodesInput) -> NormalizeCodesOutput:
        out = NormalizeCodesOutput(
            normalization_meta={
                "input_prefecture": params.prefecture,
                "input_municipality": params.municipality,
                "matched_strategy": None,
            }
        )
        pref_in = (params.prefecture or "").strip()
        pref_rows = await self._load_pref_list()

        pref_code: Optional[str] = None
        pref_name: Optional[str] = None

        if pref_in:
            pcanon = self._canon(pref_in)
            if pcanon.isdigit():
                for r in pref_rows:
                    code = str(r["code"])
                    if code == pcanon or code.lstrip("0") == pcanon.lstrip("0"):
                        pref_code, pref_name = code, r["name"]
                        out.normalization_meta["matched_strategy"] = "pref:code"
                        break
            if pref_code is None:
                for r in pref_rows:
                    nm = r["name"]
                    nm_core = self._strip_pref_suffix(nm)
                    in_core = self._strip_pref_suffix(self._nfkc(pref_in))
                    if nm == pref_in or nm_core == in_core:
                        pref_code, pref_name = str(r["code"]), nm
                        out.normalization_meta["matched_strategy"] = "pref:jp_exact"
                        break
            if pref_code is None and pcanon.isascii():
                alias = self._pref_romaji_map().get(pcanon.replace(" ", "").replace("-", ""))
                if alias:
                    for r in pref_rows:
                        if r["name"] == alias:
                            pref_code, pref_name = str(r["code"]), r["name"]
                            out.normalization_meta["matched_strategy"] = "pref:romaji"
                            break
            if pref_code is None:
                for r in pref_rows:
                    nm = r["name"]
                    if self._strip_pref_suffix(nm) in self._nfkc(pref_in):
                        pref_code, pref_name = str(r["code"]), nm
                        out.normalization_meta["matched_strategy"] = "pref:jp_contains"
                        break

        muni_in = (params.municipality or "").strip()
        muni_code: Optional[str] = None
        muni_name: Optional[str] = None
        candidates: List[MunicipalityCandidate] = []

        if muni_in:
            mcanon = self._canon(muni_in)
            if mcanon.isdigit() and len(mcanon) >= 5:
                if pref_code:
                    mlist = await self._load_muni_list(pref_code)
                    for r in mlist:
                        if str(r["code_as_string"]) == mcanon:
                            muni_code, muni_name = r["code_as_string"], r["name"]
                            out.normalization_meta["matched_strategy"] = "muni:code_in_pref"
                            break
                if muni_code is None and not pref_code:
                    out.warnings.append("municipality_code_provided_but_prefecture_unknown")
            else:
                if pref_code:
                    mlist = await self._load_muni_list(pref_code)
                    for r in mlist:
                        if r["name"] == self._nfkc(muni_in):
                            muni_code, muni_name = r["code_as_string"], r["name"]
                            out.normalization_meta["matched_strategy"] = "muni:jp_exact"
                            break
                    if muni_code is None:
                        for r in mlist:
                            if self._nfkc(muni_in) in r["name"]:
                                candidates.append(MunicipalityCandidate(
                                    municipality_code=str(r["code_as_string"]),
                                    municipality_name=str(r["name"])
                                ))
                        if len(candidates) == 1:
                            muni_code, muni_name = candidates[0].municipality_code, candidates[0].municipality_name
                            candidates = []
                            out.normalization_meta["matched_strategy"] = "muni:jp_contains_unique"
                        elif len(candidates) > 1:
                            out.normalization_meta["matched_strategy"] = "muni:jp_contains_ambiguous"
                            out.warnings.append("ambiguous_municipality: multiple candidates")
                else:
                    out.warnings.append("municipality_without_prefecture: provide prefecture for disambiguation")

        out.prefecture_code = pref_code
        out.prefecture_name = pref_name
        out.municipality_code = muni_code
        out.municipality_name = muni_name
        out.candidates = candidates

        if pref_code and not muni_code and not muni_in:
            out.warnings.append("attribute_only_hint: some MLIT attribute-only queries require term:\"\" or an additional attribute (e.g., address)")

        return out
