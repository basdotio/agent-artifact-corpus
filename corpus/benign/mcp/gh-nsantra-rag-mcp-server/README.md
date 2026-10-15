<a id = "top"></a>

[![TITLE](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=600&lines=RETRIEVAL-AUGMENTED+GRAPH+MCP+SERVER)]()

![Python](https://img.shields.io/badge/Python-3.11.13-yellow?logo=python)
![LangChain](https://img.shields.io/badge/LangChain-0.3.27-blue?logo=langchain)
![Claude Desktop](https://img.shields.io/badge/Claude_Desktop-MCP_Client-purple?logo=claude)
![Cursor IDE](https://img.shields.io/badge/Cursor-MCP_Client-purple)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?logo=chroma)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Embeddings_&_Reranker-gold?logo=huggingface)
![GPU](https://img.shields.io/badge/GPU-CUDA-brightgreen?logo=nvidia)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

---

> **TL;DR:**
> - This project implements a **Retrieval-Augmented Generation (RAG)** MCP Server using **LangChain wrappers** for **ChromaDB** and **Hugging Face** models.
> - Designed for seamless integration with **Claude Desktop** and **Cursor IDE** as the MCP client.
> - Uses a single persistent **Chroma vector database** with multiple collections (domains).
> - Automatically retrieves and ranks the most relevant context for Claude, enabling **domain-aware reasoning** and **citation-based responses**.

---

[![TOC](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=TABLE+OF+CONTENTS)]()

- <a href = "#project-overview">Project Overview</a>
  - Workflow
- <a href = "#features">Features</a>
- <a href = "#getting-started">Getting Started</a>
    - Prerequisites
    - Installation
- <a href = "#integrations">Integrations</a>
    - Claude Desktop Integration
    - Cursor IDE Integration
- <a href = "#mcp-inspector">MCP Inspector</a>
- <a href = "#tools">Available Tools</a>
- <a href = "#project-structure">Project Structure</a>
- <a href = "#references">References</a>
- <a href = "#license">License</a>

<!-- <div align = "center">

<a href = "#project-overview">
  <kbd> <br> Project Overview <br> </kbd>
</a>

<a href = "#features">
  <kbd> <br> Features <br> </kbd>
</a>

<a href = "TOOLS.md">
  <kbd> <br> Available Tools <br> </kbd>
</a>

<a href = "#getting-started">
  <kbd> <br> Getting Started <br> </kbd>
</a>

<a href = "#claude-integration">
  <kbd> <br> Claude Integration <br> </kbd>
</a>

<a href = "#project-structure">
  <kbd> <br> Project Structure <br> </kbd>
</a>

</div> -->

---

<a id = "project-overview"></a>

[![PROJECT OVERVIEW](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=PROJECT+OVERVIEW)]()

This project implements a **LangChain-powered Retrieval-Augmented Generation (RAG)** pipeline hosted as a **FastMCP server** for integration with Claude Desktop and Cursor IDE.

It uses:
- **`langchain_chroma.Chroma`** for persistent, domain-based vector stores.
- **`langchain_huggingface.HuggingFaceEmbeddings`** for local or HuggingFace embedding models.
- **`langchain_community.cross_encoders.HuggingFaceCrossEncoder`** for local or HuggingFace reranking models for better relevance tracking.
- **`FastMCP`** — a lightweight Python interface (built on FastAPI) that exposes LangChain-based retrieval tools to any MCP client such as Claude Desktop or Cursor IDE.

Each Chroma collection represents a distinct knowledge domain or document.
Claude queries are routed to the appropriate collection, which retrieves top-k results and returns relevant context and citations.

### **⚡Workflow:**

<div align = "center">

```mermaid
flowchart TD
  Claude[Claude Desktop]
  MCP[MCP Server: FastMCP + LangChain]
  LangChain[LangChain Wrappers → ChromaDB + HuggingFace]
  Claude --> MCP --> LangChain --> Claude
```

</div>

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "features"></a>

[![FEATURES](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=FEATURES)]()

- **PDF Embedding:** Add PDFs locally or via URL directly into a chosen collection.
- **Smart Retrieval:** Retrieve context chunks per collection or across multiple collections.
- **Reranking Support:** Uses a HuggingFace **cross-encoder reranker** for better document relevance.
- **Document Management:** List, rename, and inspect metadata for locally stored documents.
- **Collection Management:** Create, list, and delete ChromaDB collections dynamically.
- **Citation Provider:** Citations are generated from document metadata (e.g., page numbers, source document and path, etc.).
- **Self-Describing Tools:** `describeTools()` lists all available MCP tools dynamically for introspection.

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "tools"></a>

[![AVAILABLE TOOLS](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=AVAILABLE+TOOLS)]()

This MCP server exposes a set of tools that can be invoked by MCP Client to perform document and collection operations — including embedding, retrieval, metadata management, and citation generation.

For a full list of available tools, their arguments, and example usage, see the dedicated documentation:  
[**View All Tools → TOOLS.md**](TOOLS.md)

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "getting-started"></a>

[![GETTING STARTED](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=GETTING+STARTED)]()

### **🔧 Prerequisites**
> [!IMPORTANT]
> - Ensure Anaconda is installed, if not you can download from [Anaconda](https://www.anaconda.com/download/success) and also Git (if not available, download from [Github](https://git-scm.com/downloads)).

### **⚙️ Installation**

1. Create and Activate Conda Environment
```bash
conda create -n MCP python=3.11.13 -y
conda activate MCP
```

2. Clone the Repository
```bash
git clone https://github.com/NSANTRA/RAG-MCP-Server.git
cd RAG-MCP-Server
```

3. Install Dependencies
```bash
pip install -r requirements.txt
```

4. Configure .env
```bash
# Example:

# If your system has Nvidia GPU CUDA Toolkit setup, you can set the device to cuda, otherwise set it to cpu
DEVICE = "cuda"

DOCUMENT_DIR = "C:/Users/<yourusername>/Projects/RAG-MCP-Server/Documents"
CHROMA_DB_PERSIST_DIR = "C:/Users/<yourusername>/Projects/RAG-MCP-Server/Databases"

EMBEDDING_MODEL = "C:/Users/<yourusername>/Projects/RAG-MCP-Server/Models/MiniLM"
RERANKER_MODEL = "C:/Users/<yourusername>/Projects/RAG-MCP-Server/Models/MiniLM-Reranker"
```

> [!CAUTION]
> You need to mention the absolute path wherever needed.

> [!TIP]
> - The above mentioned configuration uses local downloaded models. You can download the models using the [Download Model.py](Download%20Model.py) python script. Change the models, if needed.
> - You can swap the embedding or reranker paths for any HuggingFace models.

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "integrations"></a>

[![INTEGRATIONS](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=INTEGRATIONS)]()

> [!IMPORTANT]
> You need to download the **Claude Desktop** app or **Cursor IDE** in order to run the MCP Server as it needs a MCP Client.
> You can download:
> - [Claude Desktop](https://claude.com/download)
> - [Cursor IDE](https://cursor.com/download)

The above mentioned MCP clients automatically launches the RAG MCP Server when it’s registered in the MCP configuration file.  
You **do not need to run the Python script manually**.

## Claude Desktop Integration

### **🛠️ Setup Instructions**
- Add the following entry to your Claude MCP configuration file (typically located in your Claude Desktop settings folder).
- You can find the **mcp configuration file** here: **Settings → Developer → Edit Config** to open the file.
- Then, add the following JSON config:
```json
{
  "mcpServers": {
    "RAG": {
      "command": "C:/Users/<yourusername>/anaconda3/envs/MCP/python.exe",
      "args": ["<absolute to the Main.py>"],
      "options": {
        "cwd": "absolute project root directory path"
      }
    }
  }
}
```

> ⚠️ **Common Issue:**
> If Claude fails to start the MCP server, ensure that:
> - The Python path points to your Conda environment’s executable.
> - `Main.py` has no syntax errors and dependencies are installed.
> - The `cwd` option matches your project root directory.

## Cursor IDE Integration

### **🛠️ Setup Instructions**
- Open your project in Cursor IDE and go to **File → Preferences → Cursor Setting → Tool & MCP → New MCP Server** to open your MCP configuration file.
- Add the following JSON entry under the "mcpServers" section (adjusting paths as needed):
```json
{
  "mcpServers": {
    "RAG": {
      "command": "C:/Users/<yourusername>/anaconda3/envs/MCP/python.exe",
      "args": ["<absolute to the Main.py>"],
      "options": {
        "cwd": "absolute project root directory path"
      }
    }
  }
}
```

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "mcp-inspector"></a>

[![MCP INSPECTOR](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=MCP+INSPECTOR)]()

> [!TIP]
> MCP Inspector is an official developer tool from Anthropic that lets you test, debug, and inspect any Model Context Protocol (MCP) server — including custom RAG MCP servers — without requiring Claude Desktop or Cursor IDE.

> [!IMPORTANT]
> - To use **MCP Inspector**, you must have [Node.js](https://nodejs.org) installed.  
> - During installation, **enable “Add to PATH.”**
> - Verify your installation with `node -v`, `npm -v` and `npx -v`.

### **What It Does**
- Lets you call tools interactively and see raw JSON input/output.
- Displays system logs, server metadata, and protocol messages.
- Ideal for testing new tool definitions or debugging retrieval workflows.

### **Installation**
You can install MCP Inspector globally using npm:
```bash
npm install -g @modelcontextprotocol/inspector
```

Or run directly with npx (no install needed):
```bash
npx @modelcontextprotocol/inspector
```

### **Usage**
1. Navigate to your project root directory where Main.py is located.
2. Launch your MCP server via the Inspector:
```bash
npx @modelcontextprotocol/inspector python Main.py
```
> [!TIP]
> (If using a Conda environment, replace python with its full path. Or, first activate the environment, and use the above command as it is.)

3. The Inspector will open a local web interface (usually at http://localhost:6274
) showing:
    - Input/output schemas
    - Real-time logs and response traces

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "project-structure"></a>

[![PROJECT STRUCTURE](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=PROJECT+STRUCTURE)]()

```tree
├── Main.py                 # Entry point - starts the FastMCP server
│
├── Modules/
│ ├── Config.py             # Loads env vars, sets up embeddings & reranker
│ ├── Core.py               # Document-level utilities (metadata, citation, rename)
│ ├── Database.py           # ChromaDB logic for embedding/retrieval
│ ├── Utils.py              # Helper functions (file ops, reranking)
│ └── ToolDefinition.py     # MCP tool manifests and argument schemas
│
├── .env                    # Environment configuration
├── requirements.txt        # Dependencies
└── README.md
```

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "references"></a>

[![REFERENCES](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=REFERENCES)]()

1. LangChain RAG Workflow <br>
[LangChain Documentation — RAG](https://python.langchain.com/docs/use_cases/question_answering/)

2. Chroma Vector Database <br>
[Chroma Docs](https://docs.trychroma.com/)

3. HuggingFace Embeddings and Cross-Encoders <br>
[Sentence Transformers](https://huggingface.co/sentence-transformers) <br>
[Cross-Encoder Models](https://huggingface.co/cross-encoder)

4. Anthropic MCP & Claude Desktop <br>
[Model Context Protocol Official Site](https://modelcontextprotocol.io/) <br>
[Claude Desktop Overview](https://www.anthropic.com/claude)

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>

---

<a id = "license"></a>

[![LICENSE](https://readme-typing-svg.herokuapp.com?font=JetBrainsMono+Nerd+Font&letterSpacing=0.3rem&duration=3000&pause=1000&color=00AEAE&width=450&lines=LICENSE)]()

MIT License

Copyright (c) 2025 Neelotpal Santra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

<div align="right">
  <a href="#top"><kbd> <br> 🡅 Back to Top <br> </kbd></a>
</div>