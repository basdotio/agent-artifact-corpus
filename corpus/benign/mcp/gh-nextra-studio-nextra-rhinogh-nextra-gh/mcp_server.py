import os
import sys
import json
import re
import math
import base64
import urllib.request
import urllib.parse
import importlib.util
import tempfile
from mcp.server.fastmcp import FastMCP
from google import genai
from google.genai import types

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(WORKSPACE_DIR, "backend", "tools")
KNOWLEDGE_DIR = os.path.join(WORKSPACE_DIR, "knowledge")
DOCS_DIR = os.path.join(WORKSPACE_DIR, "backend", "docs")
GH_DOCS_DIR = os.path.join(DOCS_DIR, "Grasshopper")
COMP_DOCS_DIR = os.path.join(DOCS_DIR, "components")

def _ensure_knowledge_dir():
    if not os.path.exists(KNOWLEDGE_DIR):
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    
    for cat in ["error", "geometry", "user_preference", "else"]:
        os.makedirs(os.path.join(KNOWLEDGE_DIR, cat), exist_ok=True)
        
    idx_path = os.path.join(KNOWLEDGE_DIR, "index.json")
    if not os.path.exists(idx_path):
        with open(idx_path, "w", encoding='utf-8') as f:
            json.dump({}, f)
    # Ensure the directory is hidden by default
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.kernel32.SetFileAttributesW(KNOWLEDGE_DIR, 2) # 2 is FILE_ATTRIBUTE_HIDDEN
        except:
            pass

def _ensure_config_exists():
    config_path = os.path.join(WORKSPACE_DIR, "backend", "backend_config.json")
    if not os.path.exists(config_path):
        default_cfg = {
            "api_key": "",
            "backend_url": "http://localhost:58001",
            "developer_mode": False
        }
        with open(config_path, "w", encoding='utf-8') as f:
            json.dump(default_cfg, f, indent=4)
    return config_path

def get_session_knowledge_dir(session_id: str) -> str:
    if session_id:
        session_dir = os.path.join(tempfile.gettempdir(), "nextra_knowledge", session_id)
        os.makedirs(session_dir, exist_ok=True)
        for cat in ["error", "geometry", "user_preference", "else"]:
            os.makedirs(os.path.join(session_dir, cat), exist_ok=True)
        return session_dir
    
    # Fallback to local workspace knowledge directory instead of crashing
    _ensure_knowledge_dir()
    return KNOWLEDGE_DIR

# --- 1. Configuration & Setup ---
def load_config():
    config_path = os.path.join(WORKSPACE_DIR, "backend", "backend_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {}

_ensure_config_exists()
CONFIG = load_config()
GEMINI_API_KEY = CONFIG.get("api_key", "")
BYPASS_KEY = ""
EMBEDDING_MODEL = CONFIG.get("models", {}).get("Embeddings", {}).get("model", "gemini-embedding-2")
GCS_BUCKET = CONFIG.get("gcs_bucket_name", "")

try:
    from google.cloud import storage
    _storage_client = storage.Client() if GCS_BUCKET else None
except Exception:
    _storage_client = None

def upload_to_gcs(source_content, destination_blob_name):
    if not _storage_client or not GCS_BUCKET:
        print(f"GCS Upload Error: Google Cloud Storage client or bucket not configured.")
        return False
    try:
        _storage_client.bucket(GCS_BUCKET).blob(destination_blob_name).upload_from_string(source_content)
        return True
    except Exception as e:
        print(f"GCS Upload Error: {e}")
        return False


mcp = FastMCP("nextra")
embed_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# --- 2. PURE RAG SEARCH ENGINE ---

def _pure_rag_search(query, index_source, top_k=5, session_id=None):
    docs = {}
    if isinstance(index_source, str):
        if not os.path.exists(index_source): return []
        try:
            with open(index_source, 'r', encoding='utf-8') as f: docs = json.load(f)
        except: return []
    elif isinstance(index_source, dict):
        docs = index_source
    else: return []

    q_emb = []
    try:
        if embed_client:
            q_emb = embed_client.models.embed_content(model=EMBEDDING_MODEL, contents=query).embeddings[0].values
    except Exception as e:
        pass
    
    results = []
    for fp, data in docs.items():
        chunks = data.get('chunks', [])
        if not chunks and 'content' in data:
            chunks = [{'content': data['content'], 'emb': data.get('emb'), 'name': os.path.basename(fp)}]
        elif not chunks:
            chunks = [{'emb': data.get('emb'), 'name': os.path.basename(fp)}]
            
        for chunk in chunks:
            sim = 0.0
            if q_emb and chunk.get('emb'):
                v1, v2 = q_emb, chunk['emb']
                dot = sum(x*y for x, y in zip(v1, v2))
                m1 = math.sqrt(sum(x*x for x in v1))
                m2 = math.sqrt(sum(x*x for x in v2))
                if m1*m2 > 0: sim = dot/(m1*m2)
            
            if sim > 0.4:
                content = chunk.get('content')
                if content is None and isinstance(index_source, str):
                    abs_path = os.path.join(os.path.dirname(index_source), fp)
                    if os.path.exists(abs_path):
                        try:
                            with open(abs_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except:
                            pass
                    else:
                        try:
                            res = _proxy_request({"type": "read_knowledge", "path": fp, "session_id": session_id})
                            if isinstance(res, str) and res.startswith("SUCCESS: "):
                                content = res[9:]
                        except:
                            pass
                if content:
                    results.append((sim, fp, chunk.get('name', ''), content))
    
    results.sort(reverse=True, key=lambda x: x[0])
    return results[:top_k]


def _send_to_sandbox(code: str, session_id: str = None) -> dict:
    backend_url = CONFIG.get("backend_url", f"http://localhost:{CONFIG.get('sandbox_port', 58001)}").rstrip('/')
    url_proxy = f"{backend_url}/plugin-execute"
    req_proxy = urllib.request.Request(
        url_proxy,
        data=json.dumps({"type": "execute_python", "code": code, "session_id": session_id}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req_proxy, timeout=180.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("status") == "success":
                return {"status": "success", "output": res_data.get("output", "")}
            else:
                if "not active/connected" not in res_data.get("message", ""):
                    return {
                        "status": "error",
                        "output": res_data.get("output") or res_data.get("message"),
                    }
    except Exception as proxy_ex:
        err_str = str(proxy_ex).lower()
        if "timeout" in err_str or "timed out" in err_str:
            return {"status": "error", "output": "ERROR: Execution timed out after 180 seconds. You likely created an infinite loop or an overly heavy calculation. Do not apologize. Rewrite the script to be more efficient or add a safe-exit counter to your while loops."}
        pass
        
    # Standalone legacy sandbox server fallback
    legacy_port = CONFIG.get("legacy_sandbox_port", 8081)
    url = f"http://127.0.0.1:{legacy_port}/execute/"
    req = urllib.request.Request(
        url,
        data=code.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        err_str = str(e).lower()
        if "timeout" in err_str or "timed out" in err_str:
            return {"status": "error", "output": "ERROR: Execution timed out after 180 seconds. You likely created an infinite loop or an overly heavy calculation. Do not apologize. Rewrite the script to be more efficient or add a safe-exit counter to your while loops."}
        return {
            "status": "error",
            "output": f"Both Grasshopper native plugin execution and legacy sandbox failed. Legacy error: {e}",
        }


def _proxy_request(arg1, arg2=None) -> str:
    if isinstance(arg1, str) and isinstance(arg2, dict):
        payload = {"type": arg1, **arg2}
    elif isinstance(arg1, dict) and arg2 is None:
        payload = arg1
    else:
        raise ValueError("Invalid arguments to _proxy_request")

    backend_url = CONFIG.get("backend_url", f"http://localhost:{CONFIG.get('sandbox_port', 58001)}").rstrip('/')
    url_proxy = f"{backend_url}/plugin-execute"
    req_proxy = urllib.request.Request(
        url_proxy,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req_proxy, timeout=180.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("status") == "success":
                output = res_data.get("output")
                if output is None:
                    output = "Success."
                if "spawned_guids" in res_data or "id" in res_data:
                    return f"SUCCESS: {json.dumps(res_data)}"
                return f"SUCCESS: {output}"
            else:
                error_msg = res_data.get("output") or res_data.get("message") or "Unknown error"
                return f"ERROR: {error_msg}"
    except Exception as ex:
        err_str = str(ex).lower()
        if "timeout" in err_str or "timed out" in err_str:
            return "ERROR: Execution timed out after 180 seconds. You likely created an infinite loop or an overly heavy calculation. Do not apologize. Rewrite the script to be more efficient or add a safe-exit counter to your while loops."
        return f"ERROR: Failed to connect to Grasshopper C# Plugin. Details: {ex}"

# --- 3. MCP TOOLS ---

@mcp.tool()
def search_knowledge(query: str, session_id: str = None) -> str:
    """Searches the internal knowledge base for past lessons and successful workflows."""
    target_dir = get_session_knowledge_dir(session_id)
    idx_path = os.path.join(target_dir, "index.json")
    results = _pure_rag_search(query, idx_path, top_k=5)
    if not results:
        return f"No matches found for '{query}' in knowledge base."
    formatted = [f"Knowledge Results for: '{query}'"]
    for score, filepath, name, content in results:
        formatted.append(f"### Match: {os.path.basename(filepath)} ({score:.2f}) ###\n{content}")
    return "\n\n".join(formatted)

@mcp.tool()
def search_rhinocommon_docs(query: str) -> str:
    """Searches the RhinoCommon API documentation for classes, methods, and examples. USE THIS FOR C# CODING ONLY."""
    idx_path = os.path.join(DOCS_DIR, "RhinoCommon_index.json")
    results = _pure_rag_search(query, idx_path, top_k=3)
    if not results: return f"No matches for '{query}' in RhinoCommon docs."
    out = [f"RhinoCommon Search: '{query}'"]
    for sc, fp, name, content in results:
        out.append(f"--- {name} ({sc:.2f}) ---\n{content}")
    return "\n\n".join(out)

@mcp.tool()
def search_rhinoscriptsyntax_docs(query: str) -> str:
    """Searches the RhinoScriptSyntax documentation for Python scripting functions. USE THIS FOR PYTHON CODING ONLY."""
    idx_path = os.path.join(DOCS_DIR, "RhinoScriptSyntax_index.json")
    results = _pure_rag_search(query, idx_path, top_k=3)
    if not results: return f"No matches for '{query}' in RhinoScriptSyntax docs."
    out = [f"RhinoScriptSyntax Search: '{query}'"]
    for sc, fp, name, content in results:
        out.append(f"--- {name} ({sc:.2f}) ---\n{content}")
    return "\n\n".join(out)

@mcp.tool()
def search_grasshopper_sdk(query: str) -> str:
    """Searches the Grasshopper SDK documentation for specific classes or methods."""
    idx_path = os.path.join(GH_DOCS_DIR, "index.json")
    results = _pure_rag_search(query, idx_path, top_k=3)
    if not results:
        return f"No SDK matches for '{query}'."
    return "\n\n".join([f"--- {name} ({sc:.2f}) ---\n{content}" for sc, fp, name, content in results])

@mcp.tool()
def search_components(keywords: str) -> str:
    """
    Searches the Grasshopper component dictionary for port indices and categories using pure RAG. USE THIS FOR GRASSHOPPER COMPONENT INFO.
    Supports comma-separated multiple keywords (e.g. 'Extrude, Unit Z, Rectangle') to query multiple components.
    """
    keys = [k.strip() for k in keywords.split(",") if k.strip()]
    if not keys: return "No keywords provided."
    
    idx_path = os.path.join(DOCS_DIR, "Components_index.json")
    all_results = []
    seen = set()
    
    for key in keys:
        results = _pure_rag_search(key, idx_path, top_k=3)
        for sc, fp, name, content in results:
            if name not in seen:
                seen.add(name)
                all_results.append((sc, name, content))
    
    if not all_results: return "No components found."
    all_results.sort(reverse=True, key=lambda x: x[0])
    
    formatted = [f"Component Search Results:"]
    for sc, name, content in all_results[:6]:
        formatted.append(f"--- {name} ({sc:.2f}) ---\n{content}")
    return "\n\n".join(formatted)

# @mcp.tool()
async def web_search(query: str) -> str:
    """
    Searches online using Google Search grounding. Can be used for Grasshopper API documentation, general references, or explicitly requesting images.
    """
    if not embed_client:
        return "Live Web search is unavailable: API Key not set."
    import asyncio
    try:
        def do_search():
            prompt = f"Search online for: {query}. Provide a concise summary with exact property/method names."
            return embed_client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.1
                ),
            )
        response = await asyncio.to_thread(do_search)
        return response.text
    except Exception as e:
        return f"Online web search failed: {e}"

@mcp.tool()
def list_knowledge_topics(session_id: str = None) -> str:
    """Returns a flat list of all knowledge file paths and their associated topics/headers."""
    target_dir = get_session_knowledge_dir(session_id)
    idx_path = os.path.join(target_dir, "index.json")
    try:
        with open(idx_path, 'r', encoding='utf-8') as f:
            idx = json.load(f)
    except:
        idx = {}
        
    if not idx:
        return "Knowledge base is empty."
        
    results = []
    for path, data in idx.items():
        results.append(f"- {path}")
    return "Knowledge Topics:\n" + "\n".join(results)

@mcp.tool()
def manage_knowledge_files(actions: list[str], paths: list[str], contents: list[str] = None, session_id: str = None, email: str = None) -> str:
    """Batch manage knowledge files natively by their path. Actions can be 'read', 'update', or 'delete'."""
    if len(actions) != len(paths):
        return "Error: actions and paths arrays must be the same length."
        
    target_dir = get_session_knowledge_dir(session_id)
    idx_path = os.path.join(target_dir, "index.json")
    
    results = []
    
    for i in range(len(actions)):
        action = actions[i]
        file_path = paths[i]
        content = contents[i] if contents and i < len(contents) else ""
        abs_path = os.path.join(target_dir, file_path)
        
        if action == "read":
            if os.path.exists(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        results.append(f"--- {file_path} ---\n{f.read()}")
                except Exception as e:
                    results.append(f"Error reading {file_path}: {e}")
            else:
                try:
                    res = _proxy_request({"type": "read_knowledge", "path": file_path, "session_id": session_id})
                    if isinstance(res, str) and res.startswith("SUCCESS: "):
                        results.append(f"--- {file_path} ---\n{res[9:]}")
                    elif isinstance(res, dict) and res.get("status") == "success":
                        results.append(f"--- {file_path} ---\n{res.get('output', '')}")
                    else:
                        results.append(f"File {file_path} not found locally or remotely.")
                except Exception as e:
                    results.append(f"File {file_path} not found. Remote proxy also failed: {e}")
                    
        elif action == "delete":
            valid_categories = ["error", "geometry", "user_preference", "else"]
            path_parts = file_path.replace("\\", "/").split("/")
            category = path_parts[0] if path_parts[0] in valid_categories else "else"
            title = path_parts[-1] if len(path_parts) > 1 else path_parts[0]
            title = title.lower().replace(" ", "_")
            if title.endswith(".md"): title = title[:-3] + ".json"
            elif not title.endswith(".json"): title += ".json"
            file_path = f"{category}/{title}"
            abs_path = os.path.join(target_dir, file_path)
            
            if os.path.exists(abs_path):
                os.remove(abs_path)
            try:
                with open(idx_path, 'r', encoding='utf-8') as f: docs = json.load(f)
            except: docs = {}
            norm_path = file_path.replace("\\", "/")
            if norm_path in docs:
                del docs[norm_path]
                with open(idx_path, 'w', encoding='utf-8') as f:
                    json.dump(docs, f)
                if GCS_BUCKET:
                    pass
            try:
                _proxy_request("manage_knowledge", {"action": "delete", "file_path": file_path, "session_id": session_id})
            except: pass
            results.append(f"Deleted {file_path} and updated index.")
            
        elif action == "update":
            if not content:
                results.append(f"Content is required for update action on {file_path}.")
                continue
                
            valid_categories = ["error", "geometry", "user_preference", "else"]
            path_parts = file_path.replace("\\", "/").split("/")
            
            category = path_parts[0] if path_parts[0] in valid_categories else "else"
            title = path_parts[-1] if len(path_parts) > 1 else path_parts[0]
            
            title = title.lower().replace(" ", "_")
            if title.endswith(".md"): title = title[:-3] + ".json"
            elif not title.endswith(".json"): title += ".json"
            
            file_path = f"{category}/{title}"
            abs_path = os.path.join(target_dir, file_path)
            
            try:
                json_data = json.loads(content)
                final_content = json.dumps(json_data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                json_data = {
                    "question": title.replace("_", " ").replace(".json", ""),
                    "answer": content
                }
                final_content = json.dumps(json_data, indent=2, ensure_ascii=False)
                
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(final_content)
                
            try:
                with open(idx_path, 'r', encoding='utf-8') as f: docs = json.load(f)
            except: docs = {}
            
            emb = []
            if embed_client:
                try:
                    emb = embed_client.models.embed_content(model=EMBEDDING_MODEL, contents=final_content).embeddings[0].values
                except: pass
                
            norm_path = file_path.replace("\\", "/")
            docs[norm_path] = {
                "emb": emb,
                "mtime": os.path.getmtime(abs_path)
            }
            with open(idx_path, 'w', encoding='utf-8') as f:
                json.dump(docs, f)
                
            if GCS_BUCKET:
                user_email = email if email else (session_id if session_id else "anonymous")
                success = upload_to_gcs(final_content, f"users/{user_email}/{norm_path}")
                
            try:
                _proxy_request("manage_knowledge", {"action": "update", "file_path": file_path, "content": final_content, "embedding": json.dumps(emb), "session_id": session_id})
            except: pass
            
            results.append(f"Updated {file_path} and re-indexed.")
            
        else:
            results.append(f"Unknown action: {action} for {file_path}.")
            
    return "\n".join(results)
@mcp.tool()
def sync_local_knowledge(session_id: str = None) -> str:
    """
    Forces the local Grasshopper plugin to re-scan the user's local knowledge directory and push any missing or modified files to the cloud.
    Use this if the user says they manually modified a local Markdown file while the session was active, and you need to pull those changes.
    """
    try:
        res = _proxy_request({"type": "trigger_sync", "session_id": session_id})
        return "Successfully triggered local sync. The cloud index will be updated shortly."
    except Exception as e:
        return f"Failed to trigger local sync: {e}"


@mcp.tool()
def modify_component_grips(component_guid: str, input_count: int = None, output_count: int = None, session_id: str = None) -> str:
    """
    Adjusts the total count of input or output ports (grips) on standard ZUI and variable-parameter Grasshopper components (like Merge, List Item, Entwine, Addition, Multiplication, etc.).
    CRITICAL INSTRUCTION: Use this whenever you just need to change the total count of inputs or outputs on a standard customizable component.
    CRITICAL INSTRUCTION: DO NOT use this tool for C# or Python Script components.
    """
    payload = {"guid": component_guid, "session_id": session_id}
    if input_count is not None: payload["i"] = input_count
    if output_count is not None: payload["o"] = output_count
    return _proxy_request("modify_grips", payload)


@mcp.tool()
def rename_component_variables(
    guid: str, 
    target_mode: str, 
    indices: list[int], 
    names: list[str], 
    access_types: list[str] = None, 
    session_id: str = None
) -> str:
    """
    Renames and optionally changes access types (item/list/tree) for existing inputs or outputs on a Grasshopper component at specific indices.
    `indices` and `names` must be lists of the same length (e.g. indices=[0, 2], names=["crv", "pt"]).
    CRITICAL INSTRUCTION: Use ONLY when you need granular index-based control to rename or change access types of specific parameters.
    CRITICAL INSTRUCTION: DO NOT use this tool for standard count adjustments on ZUI components like Merge, List Item, or Entwine - use `modify_component_grips` instead!
    CRITICAL INSTRUCTION: DO NOT use this tool for C# or Python Script components.
    `target_mode` must be 'Input' or 'Output'.
    """
    return _proxy_request({
        "type": "modify_component_variables", 
        "action": "rename",
        "guid": guid, 
        "target_mode": target_mode, 
        "indices": indices,
        "names": names or [], 
        "access_types": access_types or [], 
        "session_id": session_id
    })

@mcp.tool()
def add_component_variables(
    guid: str, 
    target_mode: str, 
    indices: list[int], 
    session_id: str = None
) -> str:
    """
    Safely adds new inputs or outputs to a Grasshopper component at specific indices (e.g. indices=[1, 3]) with custom names.
    CRITICAL INSTRUCTION: Use ONLY when you need granular index-based control to insert custom parameters.
    CRITICAL INSTRUCTION: DO NOT use this tool for standard count adjustments on ZUI components like Merge, List Item, or Entwine - use `modify_component_grips` instead!
    CRITICAL INSTRUCTION: DO NOT use this tool for C# or Python Script components.
    `target_mode` must be 'Input' or 'Output'.
    """
    return _proxy_request({
        "type": "modify_component_variables", 
        "action": "add",
        "guid": guid, 
        "target_mode": target_mode, 
        "indices": indices, 
        "session_id": session_id
    })

@mcp.tool()
def remove_component_variables(
    guid: str, 
    target_mode: str, 
    indices: list[int], 
    session_id: str = None
) -> str:
    """
    Safely removes inputs or outputs from a Grasshopper component at specific indices (e.g. indices=[2, 4]).
    CRITICAL INSTRUCTION: Use ONLY when you need granular index-based control to remove specific parameters.
    CRITICAL INSTRUCTION: DO NOT use this tool for standard count adjustments on ZUI components like Merge, List Item, or Entwine - use `modify_component_grips` instead!
    CRITICAL INSTRUCTION: DO NOT use this tool for C# or Python Script components.
    `target_mode` must be 'Input' or 'Output'.
    """
    return _proxy_request({
        "type": "modify_component_variables", 
        "action": "remove",
        "guid": guid, 
        "target_mode": target_mode, 
        "indices": indices, 
        "session_id": session_id
    })


@mcp.tool()
def modify_component_modifiers(
    guid: str, 
    target_mode: str, 
    modifiers: list[str] = None, 
    session_id: str = None
) -> str:
    """
    Sets DataMapping (graft/flatten), Simplify, and Reverse for a component's inputs/outputs.
    `modifiers` should be a list where index corresponds to the parameter index.
    e.g. ["graft", "flatten, simplify", ""]
    """
    return _proxy_request({
        "type": "modify_component_modifiers", 
        "guid": guid, 
        "target_mode": target_mode, 
        "modifiers": modifiers or [], 
        "session_id": session_id
    })


# --- 3. RIGOROUS STATE TRACKING (PHYSICAL ANCHOR METHOD) ---
@mcp.tool()
def mark_state(session_id: str = None) -> str:
    """System tool: Anchors the document state natively with a physical point."""
    code = """
import rhinoscriptsyntax as rs
import Rhino

old_anchors = rs.ObjectsByAttribute("AI_SYSTEM_ANCHOR", "TURN")
if old_anchors:
    for old in old_anchors:
        rs.UnlockObject(old)
        rs.ShowObject(old)
        rs.DeleteObject(old)

doc = Rhino.RhinoDoc.ActiveDoc
sn = doc.BeginUndoRecord("Turn_Anchor")
pt = rs.AddPoint(0,0,0)
rs.SetUserText(pt, "AI_SYSTEM_ANCHOR", "TURN")
rs.LockObject(pt)
rs.HideObject(pt)
doc.EndUndoRecord(sn)
print("State anchored.")
"""
    res = _send_to_sandbox(code, session_id)
    return res.get("output", "Anchored.")


@mcp.tool()
def revert_to_mark(session_id: str = None) -> str:
    """System tool: Reverts all actions by looping Undo until the Turn Anchor disappears."""
    code = """
import rhinoscriptsyntax as rs
import Rhino

anchors = rs.ObjectsByAttribute("AI_SYSTEM_ANCHOR", "TURN")
if not anchors:
    print("No anchor found to revert to.")
else:
    anchor_id = anchors[0]
    count = 0
    while rs.IsObject(anchor_id) and count < 200:
        rs.Command("_-Undo", False)
        count += 1

    if rs.IsObject(anchor_id):
        rs.UnlockObject(anchor_id)
        rs.DeleteObject(anchor_id)

    print("Successfully reverted " + str(count) + " actions.")
"""
    res = _send_to_sandbox(code, session_id)
    return res.get("output", "Reverted.")


# --- 4. EXECUTION TOOLS ---
@mcp.tool()
def run_python_script(code: str, session_id: str = None) -> str:
    """Executes Python code inside Grasshopper. Use this to create or modify Grasshopper components, wires, and data. You MUST include print() statements summarizing what was modified so you can read the result."""
    encoded_code = base64.b64encode(code.encode("utf-8")).decode("utf-8")
    wrapper = f"""
import Rhino
import sys, traceback
import base64

user_code = base64.b64decode("{encoded_code}").decode('utf-8')
try:
    exec(user_code, globals())
    print("|||SUCCESS|||")
except Exception as e:
    print("Script failed.\\n")
    traceback.print_exc()
"""
    res = _send_to_sandbox(wrapper, session_id)
    
    import time
    res_str = res.get("output", "")
    log_msg = ""
    if len(res_str) > 1000:
        log_dir = os.path.join(WORKSPACE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"tool_result_{int(time.time())}.txt").replace("\\", "/")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(res_str)
            log_msg = f"\n\n[Output truncated to save tokens. Full raw result saved to: {log_path}. Use read_file to view if absolutely necessary.]"
            res_str = res_str[:1000] + "..."
        except Exception: pass

    if res.get("status") == "success" and "|||SUCCESS|||" in res_str:
        return f"Success:\n{res_str.replace('|||SUCCESS|||', '')}{log_msg}"
    else:
        # Also check for success if |||SUCCESS||| was stripped but it was successful
        if "|||SUCCESS|||" in res.get("output", "") or ("Script failed" not in res_str and res.get("status") == "success"):
            output = res_str.replace('|||SUCCESS|||', '').strip()
            return f"Success:\n{output}{log_msg}"
        return f"Error:\n{res_str}{log_msg}"


@mcp.tool()
def run_csharp_script(code: str, session_id: str = None) -> str:
    """Executes C# Roslyn script code natively inside the Grasshopper/Rhino environment."""
    payload = {"type": "execute_csharp", "code": code, "session_id": session_id}
    res_str = _proxy_request(payload)
    
    import time
    log_msg = ""
    if len(res_str) > 1000:
        log_dir = os.path.join(WORKSPACE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"tool_result_cs_{int(time.time())}.txt").replace("\\", "/")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(res_str)
            log_msg = f"\n\n[Output truncated to save tokens. Full raw result saved to: {log_path}. Use read_file to view if absolutely necessary.]"
            res_str = res_str[:1000] + "..."
        except Exception: pass
        
    return res_str + log_msg


# --- 5. UTILITY TOOLS ---
@mcp.tool()
def take_rhino_screenshot(
    view_name: str = "Perspective",
    zoom_extents: bool = True,
    display_mode: str = "Shaded",
    isolate_guids: str = "",
    session_id: str = None
) -> str:
    """Takes a screenshot of the active Rhino screen."""
    if isolate_guids or zoom_extents or display_mode:
        setup_code = f"""
import rhinoscriptsyntax as rs
try:
    if '{view_name}': rs.CurrentView('{view_name}')
    if '{display_mode}': rs.ViewDisplayMode('{view_name}', '{display_mode}')
    if '{isolate_guids}':
        guids = [g.strip() for g in '{isolate_guids}'.split(',')]
        for obj in rs.AllObjects():
            if str(obj) not in guids: rs.HideObject(obj)
            else: rs.ShowObject(obj)
    if {zoom_extents}: rs.ZoomExtents('{view_name}')
except Exception as e: print("Setup warning:", e)
"""
        _send_to_sandbox(setup_code, session_id)
        
    backend_url = CONFIG.get("backend_url", f"http://localhost:{CONFIG.get('sandbox_port', 58001)}").rstrip('/')
    url_proxy = f"{backend_url}/plugin-execute"
    req_proxy = urllib.request.Request(
        url_proxy,
        data=json.dumps({"type": "take_screenshot", "view": view_name, "session_id": session_id}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    result_img = ""
    try:
        with urllib.request.urlopen(req_proxy, timeout=900) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("status") == "success":
                result_img = f"IMAGE_BASE64:{res_data.get('output')}"
    except Exception:
        pass
        
    if not result_img:
        legacy_port = CONFIG.get("legacy_sandbox_port", 8081)
        params = {"view": view_name}
        query_string = urllib.parse.urlencode(params)
        url = f"http://127.0.0.1:{legacy_port}/screenshot/?{query_string}"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=900) as response:
                res = json.loads(response.read().decode("utf-8"))
                if res.get("status") == "success":
                    result_img = f"IMAGE_BASE64:{res.get('image')}"
                else:
                    result_img = f"Error: Failed to capture screenshot."
        except Exception as e:
            result_img = f"Screenshot failed: {e}"
            
    if isolate_guids:
        _send_to_sandbox(
            "import rhinoscriptsyntax as rs\nfor obj in rs.AllObjects(): rs.ShowObject(obj)",
            session_id
        )
    return result_img


@mcp.tool()
def investigate_canvas(session_id: str = None) -> str:
    """Natively inspects the active Grasshopper Canvas, retrieving all components."""
    return _proxy_request({"type": "investigate_canvas", "session_id": session_id})


@mcp.tool()
def examine_canvas_geometry(session_id: str = None) -> str:
    """Natively examines the entire Grasshopper canvas, checking all components for warnings and errors."""
    return _proxy_request({"type": "examine_canvas", "session_id": session_id})


@mcp.tool()
def get_selected_components(session_id: str = None) -> str:
    """Retrieves the instance GUIDs and basic metadata of all components currently selected on the canvas."""
    return _proxy_request({"type": "get_selected", "session_id": session_id})


@mcp.tool()
def reset_session(session_id: str = None) -> str:
    """Resets the current session tracking and removes the temporary session folder."""
    if session_id:
        import shutil
        session_dir = os.path.join(tempfile.gettempdir(), "nextra_knowledge", session_id)
        if os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
            except Exception as e:
                print(f"Failed to remove session folder {session_dir}: {e}")
    return _proxy_request({"type": "reset_session", "session_id": session_id})


@mcp.tool()
def investigate_output_geometry(guid: str, session_id: str = None) -> str:
    """Investigates the output geometry of a specific Grasshopper component based on its instance GUID."""
    code = """
import Grasshopper
import System
import Rhino

doc = Grasshopper.Instances.ActiveCanvas.Document if Grasshopper.Instances.ActiveCanvas else (Grasshopper.Instances.DocumentServer[0] if Grasshopper.Instances.DocumentServer.DocumentCount > 0 else None)
if not doc:
    print("No active Grasshopper document found.")
else:
    obj = doc.FindObject(System.Guid("__GUID__"), True)
    if not obj:
        print("Component not found.")
    else:
        if hasattr(obj, 'Params') and hasattr(obj.Params, 'Output'):
            for i, param in enumerate(obj.Params.Output):
                data = param.VolatileData
                print("Output {} '{}': {} items".format(i, param.NickName, data.DataCount))
                for path in data.Paths:
                    branch = data.get_Branch(path)
                    for j, item in enumerate(branch):
                        if item is None:
                            continue
                        val = item.Value
                        if isinstance(val, Rhino.Geometry.Point3d):
                            print("  Point: {}".format(val))
                        elif isinstance(val, Rhino.Geometry.Curve):
                            print("  Curve Length: {}, Domain: {}".format(val.GetLength(), val.Domain))
                        elif isinstance(val, Rhino.Geometry.Brep):
                            print("  Brep Faces: {}".format(val.Faces.Count))
                        elif isinstance(val, Rhino.Geometry.Mesh):
                            print("  Mesh Vertices: {}, Faces: {}".format(val.Vertices.Count, val.Faces.Count))
                        else:
                            print("  Data: {}".format(val))
        else:
            print("Component has no outputs or data is not computed.")
""".replace("__GUID__", guid)
    res = _send_to_sandbox(code, session_id)
    return res.get("output", str(res))


@mcp.tool()
def execute_shorthand(
    shorthand_code: str,
    clean_previous: bool = False,
    anchor_x: float = None,
    anchor_y: float = None,
    session_id: str = None
) -> str:
    """Compiles and executes a block of nextra.gh Shorthand code natively on the canvas."""
    try:
        log_dir = os.path.join(WORKSPACE_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "latest_shorthand.txt"), "w", encoding="utf-8") as f:
            f.write(shorthand_code)
    except Exception as e:
        print(f"DEBUG: Failed to log shorthand: {e}")
        
    payload = {
        "type": "build_shorthand",
        "shorthand": shorthand_code,
        "clean_previous": clean_previous,
        "session_id": session_id
    }
    if anchor_x is not None and anchor_y is not None:
        payload["anchor_x"] = anchor_x
        payload["anchor_y"] = anchor_y
        
    return _proxy_request(payload)


@mcp.tool()
def cleanup_canvas(guids: list[str] = None, group_name: str = None, session_id: str = None) -> str:
    """Cleans up and deletes components from the active Grasshopper canvas."""
    payload = {"type": "clear_previous", "session_id": session_id}
    if guids:
        payload["guids"] = guids
    if group_name:
        payload["group_name"] = group_name
    return _proxy_request(payload)


@mcp.tool()
def cleanup_group(group_name: str, session_id: str = None) -> str:
    """Deletes an entire group and all its components from the Grasshopper canvas by the group's name."""
    return _proxy_request({"type": "clear_previous", "group_name": group_name, "session_id": session_id})


@mcp.tool()
def tidy_up_canvas(session_id: str = None) -> str:
    """Cleans up and automatically tidies the active Grasshopper canvas. It automatically affects all relevant objects in the session."""
    payload = {"type": "layout_canvas", "session_id": session_id}
    return _proxy_request(payload)

@mcp.tool()
def reverse_engineer_shorthand(guids: list[str] = None, depth: int = 0, session_id: str = None) -> str:
    """Convert selected or specified Grasshopper components back into nextra.gh shorthand."""
    return _proxy_request({"type": "reverse_engineer", "guids": guids, "depth": depth, "session_id": session_id})

@mcp.tool()
def group_components(guids: list[str], name: str = "Group", color: str = "#ABDBFF", session_id: str = None) -> str:
    """Groups components by their instance GUIDs."""
    return _proxy_request({"type": "group", "guids": guids, "name": name, "color": color, "session_id": session_id})

@mcp.tool()
def ungroup_components(guids: list[str], session_id: str = None) -> str:
    """Removes components from any groups they belong to."""
    return _proxy_request({"type": "ungroup", "guids": guids, "session_id": session_id})

@mcp.tool()
def disconnect_port(guid: str, port_index: int, is_input: bool = True, session_id: str = None) -> str:
    """Disconnects all wires from a specific port on a component."""
    return _proxy_request({"type": "disconnect", "guid": guid, "port_index": port_index, "is_input": is_input, "session_id": session_id})

@mcp.tool()
def connect_ports(from_guid: str, from_port: int, to_guid: str, to_port: int, session_id: str = None) -> str:
    """Connects an output port of one component to an input port of another."""
    return _proxy_request({
        "type": "connect", 
        "from_guid": from_guid, "from_port": from_port, 
        "to_guid": to_guid, "to_port": to_port,
        "session_id": session_id
    })

@mcp.tool()
def set_preview(guids: list[str], visible: bool = False, session_id: str = None) -> str:
    """Toggles the preview (visibility) of components on the canvas."""
    return _proxy_request({"type": "set_preview", "guids": guids, "visible": visible, "session_id": session_id})

@mcp.tool()
def add_component(type_name: str, category: str = "", x: float = 0, y: float = 0, session_id: str = None) -> str:
    """Adds a single component to the canvas by its library name. Returns its instance GUID."""
    return _proxy_request({"type": "add_component", "type_name": type_name, "category": category, "x": x, "y": y, "session_id": session_id})

# @mcp.tool()
# def add_csharp_script_component(code: str = "", x: float = 0, y: float = 0, session_id: str = None) -> str:
#     """Adds a C# script component to the Grasshopper canvas, automatically configuring inputs/outputs based on RunScript signature."""
#     return _proxy_request({
#         "type": "add_script_component", 
#         "lang": "csharp", 
#         "code": code, 
#         "x": x, 
#         "y": y, 
#         "session_id": session_id
#     })

@mcp.tool()
def modify_csharp_script_component(guid: str, code: str, session_id: str = None) -> str:
    """Modifies an existing C# script component and automatically updates its inputs and outputs based on the RunScript signature."""
    return _proxy_request({
        "type": "modify_script_component", 
        "lang": "csharp", 
        "guid": guid, 
        "code": code, 
        "session_id": session_id
    })

# @mcp.tool()
# def add_python_script_component(code: str = "", in_grips: list[str] = None, out_grips: list[str] = None, x: float = 0, y: float = 0, session_id: str = None) -> str:
#     """Adds a Python script component to the Grasshopper canvas, automatically configuring its inputs and outputs."""
#     return _proxy_request({
#         "type": "add_script_component", 
#         "lang": "python", 
#         "code": code, 
#         "x": x, 
#         "y": y, 
#         "in_grips": in_grips or [],
#         "out_grips": out_grips or [],
#         "session_id": session_id
#     })

@mcp.tool()
def modify_python_script_component(guid: str, code: str, session_id: str = None) -> str:
    """Modifies an existing Python script component and automatically updates its inputs and outputs based on the RunScript signature."""
    return _proxy_request({
        "type": "modify_script_component", 
        "lang": "python", 
        "guid": guid, 
        "code": code, 
        "session_id": session_id
    })

@mcp.tool()
def remove_components(guids: list[str], session_id: str = None) -> str:
    """Deletes specific components from the canvas by their GUIDs."""
    return _proxy_request({"type": "remove_components", "guids": guids, "session_id": session_id})

@mcp.tool()
def get_component_locations(guids: list[str] = None, session_id: str = None) -> str:
    """Returns the coordinates (Pivot) and dimensions (Bounds) of components."""
    return _proxy_request({"type": "get_locations", "guids": guids, "session_id": session_id})

@mcp.tool()
def move_components(guids: list[str], dx: float, dy: float, session_id: str = None) -> str:
    """Moves components by a relative offset (dx, dy)."""
    return _proxy_request({"type": "move", "guids": guids, "dx": dx, "dy": dy, "session_id": session_id})

@mcp.tool()
def get_port_data(guid: str, port_index: int, is_input: bool = True, session_id: str = None) -> str:
    """Retrieves detailed tree structure and data snippets (strings) from a specific port."""
    return _proxy_request({"type": "get_port_data", "guid": guid, "port_index": port_index, "is_input": is_input, "session_id": session_id})

@mcp.tool()
def get_reference_geometry_info(guid: str, session_id: str = None) -> str:
    """Investigates any Rhino geometry referenced by a Grasshopper parameter."""
    return _proxy_request({"type": "get_ref_geom", "guid": guid, "session_id": session_id})

@mcp.tool()
def debug_plugin_environment(session_id: str = None) -> str:
    """Returns detailed diagnostic information about the plugin's environment."""
    return _proxy_request({"type": "debug_info", "session_id": session_id})


@mcp.tool()
def add_to_group(guids: list[str], group_guid: str, session_id: str = None) -> str:
    """
    Adds components (by their instance GUIDs) into an existing Grasshopper group (by its group GUID).
    Use this to keep the canvas organized when adding or fixing components that belong in an existing group.
    """
    return _proxy_request("add_to_group", {"guids": guids, "group_guid": group_guid, "session_id": session_id})

@mcp.tool()
def search_plugin_components(plugin_name: str, session_id: str = None) -> str:
    """Searches for all components belonging to a specific plugin (category). Use this to discover available components when using 3rd party plugins."""
    code = f"""
import Grasshopper

server = Grasshopper.Instances.ComponentServer
namesOut = []
catsOut = []
subCatsOut = []

query = '{plugin_name}'.lower()
targetLibrary = None
for lib in server.Libraries:
    if lib.Name and query in lib.Name.lower():
        targetLibrary = lib
        break

if not targetLibrary:
    print("Plugin '" + query + "' is not installed or loaded.")
else:
    for proxy in server.ObjectProxies:
        if proxy.Obsolete: continue
        if proxy.LibraryGuid == targetLibrary.Id:
            namesOut.append(proxy.Desc.Name)
            catsOut.append(proxy.Desc.Category)
            subCatsOut.append(proxy.Desc.SubCategory)
            
    if not namesOut:
        print("No active components found for plugin '" + targetLibrary.Name + "'.")
    else:
        print("Found active components for plugin '" + targetLibrary.Name + "':\\n")
        unique_cats = list(set([c for c in catsOut if c]))
        unique_subcats = list(set([s for s in subCatsOut if s]))
        print("Categories: " + ", ".join(unique_cats) + "\\n")
        print("Subcategories: " + ", ".join(unique_subcats) + "\\n")
        for cat, name, subcat in zip(catsOut, namesOut, subCatsOut):
            print(" - " + str(name) + " | Category: " + str(cat) + " | Sub: " + str(subcat))
"""
    res = _send_to_sandbox(code, session_id)
    return res.get("output", "Error fetching plugin components.")

@mcp.tool()
def get_component_info(name: str = "", plugin_name: str = "", subcategory: str = "", session_id: str = None) -> str:
    """Gets detailed information about Grasshopper components including their descriptions, inputs, and outputs. Uses case-insensitive partial matching."""
    code = f"""
import Grasshopper

server = Grasshopper.Instances.ComponentServer
target_name = '{name}'.lower()
target_plugin = '{plugin_name}'.lower()
target_sub = '{subcategory}'.lower()

matches = []
for proxy in server.ObjectProxies:
    n = proxy.Desc.Name.lower() if proxy.Desc.Name else ""
    c = proxy.Desc.Category.lower() if proxy.Desc.Category else ""
    s = proxy.Desc.SubCategory.lower() if proxy.Desc.SubCategory else ""
    desc = proxy.Desc.Description.lower() if proxy.Desc.Description else ""
    
    match = True
    if target_name and (target_name not in n) and (target_name not in s) and (target_name not in c) and (target_name not in desc):
        match = False
    if target_plugin and target_plugin not in c:
        match = False
    if target_sub and target_sub not in s:
        match = False
        
    if match:
        matches.append(proxy)

if not matches:
    print("No components matching the criteria found.")
else:
    for proxy in matches:
        print("=========================================")
        print("Component: " + str(proxy.Desc.Name))
        print("Plugin (Category): " + str(proxy.Desc.Category))
        print("SubCategory: " + str(proxy.Desc.SubCategory))
        print("Obsolete: " + str(proxy.Obsolete))
        print("Description: " + str(proxy.Desc.Description) + "\\n")
        
        try:
            instance = proxy.CreateInstance()
            inList = []
            outList = []
            
            if isinstance(instance, Grasshopper.Kernel.IGH_Component):
                instance.Params.OnParametersChanged()
                for param in instance.Params.Input:
                    inList.append(str(param.Name) + " [" + str(param.NickName) + "]: " + str(param.Description))
                for param in instance.Params.Output:
                    outList.append(str(param.Name) + " [" + str(param.NickName) + "]: " + str(param.Description))
            elif hasattr(instance, 'Name') and hasattr(instance, 'Description'):
                inList.append("(None) This is a standalone data parameter.")
                outList.append(str(instance.Name) + " [" + str(instance.NickName) + "]: " + str(instance.Description))
                
            print("Inputs:")
            for i in inList: print(" - " + i)
            print("\\nOutputs:")
            for o in outList: print(" - " + o)
        except Exception as e:
            print("Error inspecting component: " + str(e))
        print("\\n")
"""
    res = _send_to_sandbox(code, session_id)
    return res.get("output", "Error fetching component info.")

@mcp.tool()
def check_installed_plugins(session_id: str = None) -> str:
    """Checks what Grasshopper plugins are currently installed and available."""
    code = """
import Grasshopper
libraries = Grasshopper.Instances.ComponentServer.Libraries
print("Installed Plugins:\\n")
for lib in libraries:
    name = lib.Name if lib.Name else "Unknown"
    version = lib.Version if lib.Version else "Unknown"
    author = lib.AuthorName if lib.AuthorName else "Unknown"
    print(" - " + str(name) + " | v" + str(version) + " | by " + str(author))
"""
    res = _send_to_sandbox(code, session_id)
    return res.get("output", "Error fetching installed plugins.")


if __name__ == "__main__":
    mcp.run()


