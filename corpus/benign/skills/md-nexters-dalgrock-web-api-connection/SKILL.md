---
name: api-connection
description: TanStack Query와 Axios를 사용한 API 연결 패턴. API 훅 생성, 데이터 페칭, 뮤테이션 처리 시 사용.
---

# API 연결 가이드

## 기술 스택

- **HTTP 클라이언트**: Axios
- **데이터 페칭**: TanStack Query (React Query)
- **Provider**: `src/components/providers/query-provider.tsx`에 설정됨

## 폴더 구조

```
src/
├── apis/
│   ├── instance.ts     # Axios 인스턴스
│   └── [feature]/
│       ├── index.ts        # API 함수
│       ├── interface.ts    # TypeScript 타입
│       └── queries.ts      # queryOptions 정의
└── utils/
    └── query.ts        # Query Key Helper
```

## Axios 인스턴스

```ts
// src/apis/instance.ts
import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})
```

## Query Key Helper

일관된 query key 관리를 위한 유틸리티:

```ts
// src/utils/query.ts
export const getQueryKeyHelper = (queryName: string) => {
  return {
    all: [queryName],
    detail: (key: string, params?: object) => [
      ...getQueryKeyHelper(queryName).all,
      key,
      ...(params ? [params] : [])
    ]
  }
}
```

## Query Options 정의

`queryOptions`만 정의하고, 훅으로 감싸지 않음:

```ts
// src/apis/records/queries.ts
import { queryOptions } from '@tanstack/react-query'
import { getRecords, getRecordById } from './index'
import { getQueryKeyHelper } from '@/utils/query'

export const recordsQueries = {
  ...getQueryKeyHelper('records'),

  getRecords: () =>
    queryOptions({
      queryKey: recordsQueries.all,
      queryFn: getRecords
    }),

  getRecordById: (recordId: number) =>
    queryOptions({
      queryKey: recordsQueries.detail('getRecordById', { recordId }),
      queryFn: () => getRecordById(recordId),
      enabled: !!recordId
    })
}
```

## API 함수

```ts
// src/apis/records/index.ts
import { api } from '@/apis/instance'
import type { Record, CreateRecordInput } from './interface'

export const getRecords = async (): Promise<Record[]> => {
  const { data } = await api.get<Record[]>('/records')
  return data
}

export const getRecordById = async (recordId: number): Promise<Record> => {
  const { data } = await api.get<Record>(`/records/${recordId}`)
  return data
}

export const createRecord = async (
  input: CreateRecordInput
): Promise<Record> => {
  const { data } = await api.post<Record>('/records', input)
  return data
}

export const deleteRecord = async (recordId: number): Promise<void> => {
  await api.delete(`/records/${recordId}`)
}
```

## 컴포넌트에서 사용 (Query)

컴포넌트에서 `useQuery`로 직접 사용. 변수명은 구체적으로 리네이밍:

```tsx
import { useQuery } from '@tanstack/react-query'
import { recordsQueries } from '@/apis/records/queries'

function RecordList() {
  const {
    data: records,
    isLoading: isRecordsLoading,
    isError: isRecordsError
  } = useQuery(recordsQueries.getRecords())

  if (isRecordsLoading) return <Skeleton />
  if (isRecordsError) return <div>오류가 발생했습니다</div>

  return (
    <div>
      {records?.map(record => (
        <RecordCard
          key={record.id}
          record={record}
        />
      ))}
    </div>
  )
}

function RecordDetail({ recordId }: { recordId: number }) {
  const { data: record, isLoading: isRecordLoading } = useQuery(
    recordsQueries.getRecordById(recordId)
  )

  if (isRecordLoading) return <Skeleton />

  return <div>{record?.music.title}</div>
}
```

## 컴포넌트에서 사용 (Mutation)

컴포넌트에서 `useMutation`으로 직접 사용. 변수명은 구체적으로 리네이밍:

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createRecord, deleteRecord } from '@/apis/records'
import { recordsQueries } from '@/apis/records/queries'
import { toast } from 'sonner'

function RecordForm() {
  const queryClient = useQueryClient()

  const { mutate: createRecordMutate, isPending: isCreatePending } =
    useMutation({
      mutationFn: createRecord,
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: recordsQueries.all })
        toast.success('기록이 저장되었습니다')
      },
      onError: () => {
        toast.error('저장에 실패했습니다')
      }
    })

  const handleSubmit = (data: CreateRecordInput) => {
    createRecordMutate(data)
  }

  return <form>...</form>
}

function DeleteButton({ recordId }: { recordId: number }) {
  const queryClient = useQueryClient()

  const { mutate: deleteRecordMutate, isPending: isDeletePending } =
    useMutation({
      mutationFn: () => deleteRecord(recordId),
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: recordsQueries.all })
        toast.success('기록이 삭제되었습니다')
      }
    })

  return (
    <Button
      onClick={() => deleteRecordMutate()}
      disabled={isDeletePending}>
      삭제
    </Button>
  )
}
```

## 인터페이스 정의

```ts
// src/apis/records/interface.ts
export interface Record {
  id: number
  date: string
  music: Music
  emotions: string[]
  situations: string[]
  memo?: string
  createdAt: string
}

export interface CreateRecordInput {
  date: string
  musicId: string
  emotions: string[]
  situations: string[]
  memo?: string
}

export interface Music {
  id: string
  title: string
  artist: string
  albumCover: string
}
```

## Query Client 옵션

```ts
// src/components/providers/query-provider.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60, // 1분
      gcTime: 1000 * 60 * 5 // 5분
    },
    mutations: {
      retry: 0
    }
  }
})
```
