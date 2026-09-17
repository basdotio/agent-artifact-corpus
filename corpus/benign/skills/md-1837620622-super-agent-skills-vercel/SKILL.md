---
name: vercel
description: "在 Vercel 上部署和配置应用。适用于部署 Next.js 应用、配置 Serverless 函数、设置 Edge 函数或管理 Vercel 项目。触发关键词：Vercel, deploy, serverless, edge function, Next.js deployment, 部署。"
---

# Vercel 部署

在 Vercel 边缘网络上部署和配置应用。

## 快速开始

```bash
# 安装 Vercel CLI
npm i -g vercel

# 从项目目录部署
vercel

# 部署到生产环境
vercel --prod

# 链接到现有项目
vercel link
```

## vercel.json 配置文件

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["iad1", "sfo1"],
  "functions": {
    "api/**/*.ts": {
      "memory": 1024,
      "maxDuration": 30
    }
  },
  "rewrites": [
    { "source": "/api/:path*", "destination": "/api/:path*" },
    { "source": "/:path*", "destination": "/" }
  ],
  "headers": [
    {
      "source": "/api/:path*",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" }
      ]
    }
  ],
  "env": {
    "DATABASE_URL": "@database-url"
  }
}
```

## Serverless 函数

```typescript
// api/hello.ts
import type { VercelRequest, VercelResponse } from '@vercel/node';

export default function handler(req: VercelRequest, res: VercelResponse) {
  const { name = 'World' } = req.query;
  res.status(200).json({ message: `Hello ${name}!` });
}
```

## Edge 边缘函数

```typescript
// api/edge.ts
export const config = {
  runtime: 'edge',
};

export default function handler(request: Request) {
  return new Response(JSON.stringify({ message: 'Hello from Edge!' }), {
    headers: { 'content-type': 'application/json' },
  });
}
```

## Next.js App Router

```typescript
// app/api/route.ts
import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const name = searchParams.get('name') ?? 'World';
  
  return NextResponse.json({ message: `Hello ${name}!` });
}

export async function POST(request: Request) {
  const body = await request.json();
  return NextResponse.json({ received: body });
}
```

## ISR（增量静态再生成）

```typescript
// app/posts/[id]/page.tsx
export const revalidate = 60; // 每 60 秒重新验证

export async function generateStaticParams() {
  const posts = await getPosts();
  return posts.map((post) => ({ id: post.id }));
}

export default async function Post({ params }: { params: { id: string } }) {
  const post = await getPost(params.id);
  return <article>{post.content}</article>;
}
```

## Vercel KV (Redis)

```typescript
import { kv } from '@vercel/kv';

// 设置
await kv.set('user:123', { name: 'Alice', visits: 0 });

// 获取
const user = await kv.get('user:123');

// 自增
await kv.incr('user:123:visits');

// 哈希操作
await kv.hset('session:abc', { userId: '123', expires: Date.now() + 3600000 });
const session = await kv.hgetall('session:abc');
```

## Vercel Blob

```typescript
import { put, list, del, head } from '@vercel/blob';

// 上传文件
export async function POST(request: Request) {
  const formData = await request.formData();
  const file = formData.get('file') as File;
  
  const blob = await put(file.name, file, {
    access: 'public',
    contentType: file.type,
  });
  
  return Response.json(blob);
}

// 列出所有文件
export async function GET() {
  const { blobs } = await list();
  return Response.json(blobs);
}

// 获取文件元数据
const blobDetails = await head(blobUrl);

// 删除文件
await del(blobUrl);
```

### 客户端上传
```typescript
import { handleUpload, type HandleUploadBody } from '@vercel/blob/client';
import { NextResponse } from 'next/server';

export async function POST(request: Request): Promise<NextResponse> {
  const body = (await request.json()) as HandleUploadBody;

  const jsonResponse = await handleUpload({
    body,
    request,
    onBeforeGenerateToken: async (pathname) => {
      // 验证用户权限后生成令牌
      return {
        allowedContentTypes: ['image/jpeg', 'image/png', 'image/webp'],
        maximumSizeInBytes: 10 * 1024 * 1024, // 10MB
      };
    },
    onUploadCompleted: async ({ blob }) => {
      console.log('Upload completed:', blob.url);
    },
  });

  return NextResponse.json(jsonResponse);
}
```

## Vercel Postgres

```typescript
import { sql } from '@vercel/postgres';

// 查询
const { rows } = await sql`SELECT * FROM users WHERE id = ${userId}`;

// 插入
await sql`INSERT INTO users (name, email) VALUES (${name}, ${email})`;

// 事务
await sql.query('BEGIN');
try {
  await sql`UPDATE accounts SET balance = balance - ${amount} WHERE id = ${from}`;
  await sql`UPDATE accounts SET balance = balance + ${amount} WHERE id = ${to}`;
  await sql.query('COMMIT');
} catch (e) {
  await sql.query('ROLLBACK');
  throw e;
}
```

## 环境变量

```bash
# 添加密钥
vercel env add DATABASE_URL production

# 拉取环境变量到本地
vercel env pull .env.local

# 列出环境变量
vercel env ls
```

## 定时任务

```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/daily-job",
      "schedule": "0 0 * * *"
    }
  ]
}
```

```typescript
// api/daily-job.ts
export default function handler(req, res) {
  // 验证是否来自 Vercel Cron
  if (req.headers['authorization'] !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).end();
  }
  
  // 运行任务
  await runDailyJob();
  res.status(200).end();
}
```

## 数据获取与缓存策略

```typescript
// app/posts/page.tsx
export default async function PostsPage() {
  // 静态数据 - 缓存直到手动失效（类似 getStaticProps）
  const staticData = await fetch('https://api.example.com/posts', { 
    cache: 'force-cache'  // 默认值，可省略
  });

  // 动态数据 - 每次请求都重新获取（类似 getServerSideProps）
  const dynamicData = await fetch('https://api.example.com/user', { 
    cache: 'no-store' 
  });

  // 定时重新验证 - 每 60 秒重新获取
  const revalidatedData = await fetch('https://api.example.com/stats', {
    next: { revalidate: 60 }
  });

  // 带标签的缓存 - 用于按需重新验证
  const taggedData = await fetch('https://api.example.com/products', {
    next: { tags: ['products'] }
  });

  return <div>...</div>;
}
```

## Server Actions 与缓存失效

```typescript
// app/actions.ts
'use server'

import { revalidatePath, revalidateTag } from 'next/cache';

// 按路径重新验证
export async function createPost(formData: FormData) {
  const title = formData.get('title');
  await db.post.create({ data: { title } });
  
  // 使 /posts 路径的缓存失效
  revalidatePath('/posts');
}

// 按标签重新验证
export async function updateProduct(id: string, data: any) {
  await db.product.update({ where: { id }, data });
  
  // 使所有带 'products' 标签的数据缓存失效
  revalidateTag('products');
}

// 立即更新缓存（读取自己写入的数据场景）
import { revalidateTag } from 'next/cache';
import { redirect } from 'next/navigation';

export async function createArticle(formData: FormData) {
  const article = await db.article.create({
    data: {
      title: formData.get('title'),
      content: formData.get('content'),
    },
  });

  // 立即使缓存失效，确保新文章立即可见
  updateTag('articles');
  updateTag(`article-${article.id}`);

  redirect(`/articles/${article.id}`);
}
```

## 表单处理示例

```tsx
// app/posts/new/page.tsx
import { createPost } from '@/app/actions';

export default function NewPostPage() {
  return (
    <form action={createPost}>
      <input name="title" placeholder="标题" required />
      <textarea name="content" placeholder="内容" required />
      <button type="submit">发布</button>
    </form>
  );
}
```

## Vercel AI SDK

使用 AI SDK 构建流式 AI 应用：

```typescript
// app/api/chat/route.ts
import { openai } from '@ai-sdk/openai';
import { streamText } from 'ai';

// 允许流式响应最长 30 秒
export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages } = await req.json();
  
  const result = streamText({
    model: openai('gpt-4o'),
    messages,
  });

  return result.toDataStreamResponse();
}
```

### 客户端 Hook
```tsx
'use client';

import { useChat } from 'ai/react';

export default function Chat() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat();

  return (
    <div>
      {messages.map((m) => (
        <div key={m.id}>
          <strong>{m.role}:</strong> {m.content}
        </div>
      ))}
      
      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="输入消息..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          发送
        </button>
      </form>
    </div>
  );
}
```

## Edge Runtime

在边缘运行函数以获得更低延迟：

```typescript
// app/api/edge/route.ts
export const runtime = 'edge';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const name = searchParams.get('name') ?? 'World';
  
  return new Response(`Hello ${name}!`, {
    headers: { 'content-type': 'text/plain' },
  });
}
```

## Web Analytics

启用网站分析：

```tsx
// app/layout.tsx
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/next';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
```

## 相关资源

- **Vercel 文档**: https://vercel.com/docs
- **Next.js on Vercel**: https://vercel.com/docs/frameworks/nextjs
- **Server Actions**: https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions
- **缓存与重新验证**: https://nextjs.org/docs/app/building-your-application/caching
- **AI SDK**: https://sdk.vercel.ai/docs
