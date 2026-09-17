---
name: check-library
description: 라이브러리 정보를 확인하기 위한 스킬이다. Next.js, shadcn, 기타 라이브러리에 대해 적절한 MCP 서버를 사용해 최신 문서와 사용 방법을 조회한다.
---

# Check Library

이 스킬은 라이브러리 정보를 확인하기 위해 적절한 MCP 서버를 선택해 사용한다.

## Instructions

라이브러리 이름에 따라 아래 우선순위로 MCP 서버를 사용한다:

### 1. Next.js 관련

Next.js와 관련된 질문이나 구현의 경우, next-devtools MCP를 사용한다.

```
# 최초 초기화 (세션 시작 시 1회만 수행)
mcp__plugin_gaebalai_next-devtools__init

# 문서 검색
mcp__plugin_gaebalai_next-devtools__nextjs_docs
  action: "search"
  query: "<검색 키워드>"

# 문서 조회 (경로를 알고 있는 경우)
mcp__plugin_gaebalai_next-devtools__nextjs_docs
  action: "get"
  path: "<문서 경로>"
```

### 2. shadcn 관련

shadcn/ui 관련 질문이나 구현의 경우, shadcn MCP를 사용한다.

```
# shadcn MCP 도구 사용
# 사용 가능한 도구는 ListMcpResourcesTool로 확인 가능
```

### 3. 기타 라이브러리

위에 해당하지 않는 라이브러리는 context7 MCP를 사용한다.

```
# 라이브러리 ID 해결
mcp__plugin_gaebalai_context7__resolve-library-id
  libraryName: "<라이브러리명>"

# 문서 조회
mcp__plugin_gaebalai_context7__get-library-docs
  context7CompatibleLibraryID: "<resolve-library-id로 얻은 ID>"
  topic: "<선택 사항: 특정 토픽>"
  page: 1
```

## 사용 예시

### Next.js App Router 조사
1. `mcp__plugin_gaebalai_next-devtools__init`으로 초기화
2. `mcp__plugin_gaebalai_next-devtools__nextjs_docs`로 App Router 문서 검색

### shadcn/ui Button 컴포넌트 조사
1. shadcn MCP 도구를 사용해 Button 컴포넌트 정보 조회

### React Query 사용 방법 조사
1. `mcp__plugin_gaebalai_context7__resolve-library-id` 로 React Query 라이브러리 ID 조회
2. `mcp__plugin_gaebalai_context7__get-library-docs` 로 문서 조회

## 주의 사항

- 라이브러리명이 모호한 경우, 사용자에게 확인한 뒤 적절한 MCP를 선택한다.
- Next.js와 shadcn은 전용 MCP가 있으므로 우선적으로 사용한다.
- context7을 사용하는 경우, 반드시 `resolve-library-id`로 라이브러리 ID를 먼저 해결한 뒤 `get-library-docs`를 사용한다.
