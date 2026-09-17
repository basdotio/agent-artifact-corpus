---
name: s3-download-zip
description: >
  Guia completo para baixar arquivos/vídeos do Amazon S3 para diretório local (/tmp) e empacotar
  os resultados em um arquivo ZIP usando .NET em AWS Lambda. Use sempre que precisar implementar
  o pipeline de: download de arquivo do S3 → processamento em diretório local → compactação em ZIP
  → upload do ZIP de volta ao S3. Aplica-se a projetos .NET Lambda que trabalham com geração de
  thumbnails, processamento de vídeos, extração de frames, geração de relatórios em lote, ou
  qualquer operação que precise agrupar arquivos gerados em um único artefato compactado.
---

# S3 Download + Diretório Local + ZIP em .NET Lambda

Skill focada no pipeline completo de: **baixar do S3** → **operar em diretório local** → **compactar em ZIP** → **enviar ZIP ao S3**.

Baseada no código real do projeto FrameSnap (Lambda-FrameSnap-Processor/Function.cs).

---

## Visão Geral do Pipeline

```
S3 (vídeo/arquivo)
       │
       ▼
  DownloadVideoFromS3()
       │
       ▼
  /tmp/arquivo.mp4       ← armazenamento temporário
       │
       ▼
  Processar (extrair frames, gerar imagens, etc.)
       │
       ▼
  /tmp/images/           ← diretório de saída
  ├── frame_0.jpg
  ├── frame_20.jpg
  └── frame_40.jpg
       │
       ▼
  ZipFile.CreateFromDirectory()
       │
       ▼
  /tmp/videoId_thumbnails.zip
       │
       ▼
  UploadZipToS3()
       │
       ▼
  S3: thumbnails/videoId_thumbnails.zip
```

---

## 1. Download de Vídeo/Arquivo do S3

### Implementação Direta (como no projeto)

```csharp
private async Task DownloadVideoFromS3(string key, string localPath)
{
    var response = await _s3Client.GetObjectAsync(new GetObjectRequest
    {
        BucketName = BUCKET_NAME,
        Key = key
    });

    using var fileStream = File.Create(localPath);
    await response.ResponseStream.CopyToAsync(fileStream);
}
```

**Uso no handler:**

```csharp
// A chave S3 vem do evento (ex: SQS disparado por S3)
var videoKey = s3Record.S3.Object.Key;

// Montar caminho local em /tmp
var localVideoPath = Path.Combine(TEMP_DIR, Path.GetFileName(videoKey));

// Baixar
await DownloadVideoFromS3(videoKey, localVideoPath);
context.Logger.LogInformation($"Vídeo baixado para {localVideoPath}");
```

### Versão com parâmetros explícitos (reutilizável)

```csharp
private async Task<string> DownloadFromS3(
    string bucketName,
    string key,
    IAmazonS3 s3Client,
    string destinationDir = "/tmp")
{
    var localPath = Path.Combine(destinationDir, Path.GetFileName(key));

    var response = await s3Client.GetObjectAsync(new GetObjectRequest
    {
        BucketName = bucketName,
        Key = key
    });

    using var fileStream = File.Create(localPath);
    await response.ResponseStream.CopyToAsync(fileStream);

    return localPath; // retorna caminho local para uso posterior
}
```

---

## 2. Gerenciamento do Diretório de Saída Local

A Lambda reutiliza instâncias entre invocações — **sempre limpe e recrie** o diretório de saída para evitar contaminação entre execuções.

```csharp
// Definir diretório de saída dentro de /tmp
var outputFolder = Path.Combine(TEMP_DIR, "images");

// Limpar se já existe (de execução anterior)
if (Directory.Exists(outputFolder))
{
    Directory.Delete(outputFolder, true);
}

// Criar limpo
Directory.CreateDirectory(outputFolder);
context.Logger.LogInformation($"Diretório de saída criado: {outputFolder}");
```

**Por que isso importa:**
- `/tmp` em Lambda persiste entre invocações na mesma instância (warm start)
- Arquivos da execução anterior podem corromper o ZIP gerado
- Sempre use `Directory.Delete(path, true)` antes de recriar

---

## 3. Criação do ZIP a partir do Diretório

### ZipFile.CreateFromDirectory — simples e direto

```csharp
// Após popular outputFolder com os arquivos gerados...

var zipFileName = $"{videoId}_thumbnails.zip";
var zipPath = Path.Combine(TEMP_DIR, zipFileName);

ZipFile.CreateFromDirectory(outputFolder, zipPath);
context.Logger.LogInformation($"Arquivo ZIP criado: {zipPath}");
```

**Namespace necessário:**
```csharp
using System.IO.Compression;
```

### ZIP com controle de nível de compressão

```csharp
using System.IO.Compression;

var zipPath = Path.Combine(TEMP_DIR, $"{videoId}_thumbnails.zip");

ZipFile.CreateFromDirectory(
    sourceDirectoryName: outputFolder,
    destinationArchiveFileName: zipPath,
    compressionLevel: CompressionLevel.Fastest, // Fastest | Optimal | NoCompression | SmallestSize
    includeBaseDirectory: false // false = zip contém os arquivos diretamente, sem subpasta raiz
);
```

**Guia de compressionLevel:**
| Nível | Uso ideal |
|---|---|
| `Fastest` | Imagens (JPG/PNG já são comprimidas, pouco ganho) |
| `Optimal` | Documentos, texto, CSVs |
| `SmallestSize` | Quando tamanho importa mais que velocidade |
| `NoCompression` | Quando já são dados comprimidos |

---

## 4. Upload do ZIP para S3

```csharp
private async Task UploadZipToS3(string localPath, string key)
{
    await _s3Client.PutObjectAsync(new PutObjectRequest
    {
        BucketName = BUCKET_NAME,
        Key = key,
        FilePath = localPath
    });
}
```

**Uso:**
```csharp
var zipKey = $"thumbnails/{zipFileName}";
await UploadZipToS3(zipPath, zipKey);
context.Logger.LogInformation($"ZIP enviado para S3: {zipKey}");
```

---

## 5. Limpeza de Arquivos Temporários

**Sempre use `finally`** para garantir limpeza mesmo em caso de erro:

```csharp
string localVideoPath = null;
string outputFolder = null;
string zipPath = null;

try
{
    // ... pipeline completo ...
}
finally
{
    try
    {
        if (localVideoPath != null && File.Exists(localVideoPath))
            File.Delete(localVideoPath);

        if (zipPath != null && File.Exists(zipPath))
            File.Delete(zipPath);

        if (outputFolder != null && Directory.Exists(outputFolder))
            Directory.Delete(outputFolder, true);
    }
    catch (Exception ex)
    {
        context.Logger.LogWarning($"Erro durante limpeza: {ex.Message}");
        // Não relançar — limpeza não deve mascarar erro original
    }
}
```

**Ordem de limpeza:** vídeo original → ZIP gerado → diretório de frames (maior)

---

## 6. Pipeline Completo — Exemplo de Referência

Este é o padrão completo extraído do projeto FrameSnap:

```csharp
private async Task ProcessMessageAsync(SQSEvent.SQSMessage message, ILambdaContext context)
{
    string videoId = null;
    string localVideoPath = null;
    string outputFolder = null;
    string zipPath = null;

    try
    {
        // 1. Extrair metadados do evento S3 (via SQS)
        var s3Event = JsonConvert.DeserializeObject<S3Event>(message.Body);
        var videoKey = s3Event.Records.First().S3.Object.Key;

        // Ignorar ZIPs para evitar loop infinito (S3 trigger)
        if (videoKey.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
        {
            context.Logger.LogInformation($"Ignorando arquivo ZIP: {videoKey}");
            return;
        }

        videoId = Path.GetFileNameWithoutExtension(videoKey).Split('_')[0];
        context.Logger.LogInformation($"Processando vídeo: {videoKey} (ID: {videoId})");

        // 2. Baixar vídeo do S3 para /tmp
        localVideoPath = Path.Combine("/tmp", Path.GetFileName(videoKey));
        await DownloadVideoFromS3(videoKey, localVideoPath);
        context.Logger.LogInformation($"Vídeo baixado: {localVideoPath}");

        // 3. Preparar diretório de saída limpo
        outputFolder = Path.Combine("/tmp", "images");
        if (Directory.Exists(outputFolder))
            Directory.Delete(outputFolder, true);
        Directory.CreateDirectory(outputFolder);

        // 4. Processar (extrair frames, gerar imagens, etc.)
        // ... lógica de negócio aqui ...

        // 5. Compactar diretório em ZIP
        var zipFileName = $"{videoId}_thumbnails.zip";
        zipPath = Path.Combine("/tmp", zipFileName);
        ZipFile.CreateFromDirectory(outputFolder, zipPath);
        context.Logger.LogInformation($"ZIP criado: {zipPath}");

        // 6. Upload do ZIP para S3
        var zipKey = $"thumbnails/{zipFileName}";
        await UploadZipToS3(zipPath, zipKey);
        context.Logger.LogInformation($"ZIP enviado para S3: {zipKey}");
    }
    catch (Exception ex)
    {
        context.Logger.LogError($"Erro ao processar: {ex.Message}");
        throw;
    }
    finally
    {
        // 7. Limpeza garantida
        CleanupTempFiles(localVideoPath, zipPath, outputFolder, context);
    }
}
```

---

## 7. Estrutura de Pastas em /tmp

Lambda dispõe de `/tmp` com até **10 GB** (configurável, default 512 MB).

```
/tmp/
├── video_abc123_original.mp4    ← download do S3
├── images/                      ← diretório de trabalho
│   ├── frame_at_0.jpg
│   ├── frame_at_20.jpg
│   └── frame_at_40.jpg
└── abc123_thumbnails.zip        ← ZIP final (antes do upload)
```

**Pontos de atenção:**
- Vídeo + frames + ZIP podem ocupar 3-5× o tamanho do vídeo original
- Configure memória Lambda adequada: mínimo 512 MB para vídeos pequenos
- Para vídeos > 1 GB, aumente `/tmp` via `EphemeralStorage` nas configs da Lambda

---

## 8. Dependências NuGet

```xml
<PackageReference Include="AWSSDK.S3" Version="3.7.300.2" />
<PackageReference Include="Amazon.Lambda.Core" Version="2.2.0" />
<PackageReference Include="Amazon.Lambda.SQSEvents" Version="5.2.0" />
<!-- System.IO.Compression já está incluído no .NET runtime -->
```

---

## 9. IAM Permissions Necessárias

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::seu-bucket/videos/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::seu-bucket/thumbnails/*"
    }
  ]
}
```

---

## 10. Armadilhas Comuns

### Loop infinito com S3 trigger
Se o Lambda é disparado por eventos S3 e faz upload no mesmo bucket, **filtre por prefixo ou extensão**:

```csharp
if (videoKey.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
{
    context.Logger.LogInformation($"Ignorando ZIP para evitar loop: {videoKey}");
    return;
}
```

Ou configure a trigger S3 para escutar apenas `videos/` e fazer upload em `thumbnails/`.

### Espaço insuficiente em /tmp

```csharp
var tmpInfo = new DriveInfo("/");
var availableMB = tmpInfo.AvailableFreeSpace / (1024 * 1024);
if (availableMB < 200)
    throw new Exception($"Espaço insuficiente em /tmp: {availableMB}MB disponíveis");
```

### Stream não fechado antes do ZipFile

Certifique-se de que todos os `FileStream` estejam fechados (com `using`) antes de chamar `ZipFile.CreateFromDirectory` — arquivos abertos podem causar erros ou ZIPs corrompidos.
