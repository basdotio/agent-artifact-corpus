import os
import re
import sys
import json
import time
import subprocess
import requests
import unicodedata
import urllib3
import xml.etree.ElementTree as ET
from urllib.parse import quote, unquote
from faster_whisper import WhisperModel

# SSL警告の完全抑制
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === 設定項目 (環境変数から取得、未設定時はデフォルト値) ===
NC_HOST = os.getenv("NC_HOST", "https://nextcloud.example.ts.net")
NC_USER = os.getenv("NC_USER", "your_username")
NC_PASS = os.getenv("NC_PASS", "your_app_password_here")
DAV_BASE = f"{NC_HOST}/remote.php/dav/files/{NC_USER}"
TARGET_ROOT = os.getenv("TARGET_ROOT", "大学/2026_秋")  # MCPサーバー側の参照ルートと完全に一致させる
LLM_API_URL = os.getenv("LLM_API_URL", "http://127.0.0.1:8000/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf")

auth = (NC_USER, NC_PASS)

def dav_url(path: str) -> str:
    parts = [quote(p) for p in path.strip("/").split("/") if p]
    return f"{DAV_BASE}/" + "/".join(parts)

def list_inbox():
    res = requests.request("PROPFIND", dav_url("00_Inbox"), auth=auth, verify=False, headers={"Depth": "1"})
    if res.status_code not in [200, 207]:
        return []
    root = ET.fromstring(res.text)
    files = []
    target = f"/remote.php/dav/files/{NC_USER}/00_Inbox"
    for elem in root.findall(".//{DAV:}response"):
        href = unquote(elem.find("{DAV:}href").text.rstrip("/"))
        if href != target and href.lower().endswith((".aac", ".m4a", ".mp3", ".wav")):
            files.append(href.split("/")[-1])
    return files

def mkdir_p(path: str):
    cur = ""
    for p in path.strip("/").split("/"):
        if not p: continue
        cur += "/" + p
        requests.request("MKCOL", dav_url(cur), auth=auth, verify=False)

def move_file(src: str, dest: str):
    headers = {"Destination": dav_url(dest), "Overwrite": "T"}
    res = requests.request("MOVE", dav_url(src), auth=auth, headers=headers, verify=False)
    return res.status_code in [201, 204]

def download_file(src: str, local_path: str):
    res = requests.get(dav_url(src), auth=auth, verify=False, stream=True)
    res.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in res.iter_content(chunk_size=8192):
            f.write(chunk)

def upload_text(dest: str, content: str):
    res = requests.put(dav_url(dest), data=content.encode("utf-8"), auth=auth, verify=False)
    return res.status_code in [201, 204]

def parse_filename(filename: str):
    base = os.path.splitext(filename)[0]
    base = unicodedata.normalize('NFKC', base).strip()
    match = re.search(r"^(.*?)[_ -]*(?:第)?([0-9]{1,2})(?:回)?$", base)
    if match:
        subject = match.group(1).strip()
        num = int(match.group(2))
        return subject, f"第{num:02d}回"
    return base, "第01回"

def convert_to_wav(input_path: str, output_path: str):
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        output_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"ffmpeg 変換に失敗しました: {input_path}")

def summarize_with_llm(subject: str, lecture_round: str, transcript: str) -> str:
    system_prompt = (
        "あなたは大学講義の専属ノートテイカーAIです。入力された講義音声の文字起こしテキストから、"
        "復習および試験対策に最適化された構造化された講義ノートをMarkdown形式で作成してください。\n"
        "専門用語は正確に記載し、重要な概念、箇条書き、定義、試験に出そうなポイントを明確に整理してください。"
    )
    user_prompt = f"# 講義科目: {subject} ({lecture_round})\n\n以下は本講義の文字起こしデータです。これを整理・構造化して講義ノートを作成してください。\n\n---\n{transcript}\n"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
        "chat_template_kwargs": {"enable_thinking": False}
    }
    # 巨大モデル・長文推論用にタイムアウトを1800秒（30分）に設定
    res = requests.post(LLM_API_URL, json=payload, timeout=1800)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

def main():
    inbox_files = list_inbox()
    if not inbox_files:
        return
        
    print(f"[*] 検出された音声 ({len(inbox_files)}件): {inbox_files}")
    print("[*] faster-whisper (large-v3) をロード中...")
    model = WhisperModel("large-v3", device="cpu", compute_type="int8", cpu_threads=16)

    for fname in inbox_files:
        subject, lecture_round = parse_filename(fname)
        print(f"\n==========================================")
        print(f"[*] 対象: {fname} -> 科目: {subject}, 回数: {lecture_round}")
        
        src_path = f"00_Inbox/{fname}"
        proc_path = f"01_Processing/{fname}"
        print(f"[*] Processingへ移動中: {src_path} -> {proc_path}")
        move_file(src_path, proc_path)
        
        local_audio = f"/tmp/{fname}"
        local_wav = f"/tmp/{os.path.splitext(fname)[0]}.wav"
        target_dir = f"{TARGET_ROOT}/{subject}/{lecture_round}"
        
        try:
            print(f"[*] 音声をダウンロード中...")
            download_file(proc_path, local_audio)
            
            print(f"[*] ffmpeg で WAV 変換中 (16kHz mono)...")
            convert_to_wav(local_audio, local_wav)
            
            print("[*] 文字起こし開始 (CPU int8, beam_size=1 爆速モード)...")
            t0 = time.time()
            segments, info = model.transcribe(
                local_wav,
                language="ja",
                beam_size=1,
                best_of=1,
                vad_filter=True
            )
            full_text = [seg.text for seg in segments]
            transcript_raw = "\n".join(full_text).strip()
            
            if not transcript_raw:
                print(f"[!] 警告: 文字起こし結果が空です。ファイルを保護して中断します。")
                continue
                
            duration_min = info.duration / 60 if info.duration else 0
            proc_time = time.time() - t0
            print(f"[*] 文字起こし完了! (音声長: {duration_min:.1f}分, 処理時間: {proc_time:.1f}秒, 文字数: {len(transcript_raw)})")
            
            # 【先行保存ガード】LLMを呼ぶ前に文字起こしテキスト全文を即座にNextcloudへ保存
            mkdir_p(target_dir)
            upload_text(f"{target_dir}/文字起こし_全文.txt", transcript_raw)
            print(f"[*] 文字起こし全文を Nextcloud に先行保存完了: {target_dir}")
            
            print(f"[*] {LLM_MODEL} (llama-proxy経由) で講義ノート作成中...")
            t0 = time.time()
            summary_md = summarize_with_llm(subject, lecture_round, transcript_raw)
            print(f"[*] 要約完了! ({time.time() - t0:.1f}秒)")
            
            upload_text(f"{target_dir}/講義ノート_要約.md", summary_md)
            print(f"[*] 講義ノート要約を保存しました: {target_dir}")
            
            archive_dir = f"99_Archive/{subject}"
            mkdir_p(archive_dir)
            move_file(proc_path, f"{archive_dir}/{fname}")
            print(f"[*] 元音声をアーカイブへ移動完了: {archive_dir}/{fname}")
            
        except Exception as e:
            print(f"[!] エラー発生 ({fname}): {e}")
        finally:
            for p in [local_audio, local_wav]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass
                    
        print(f"[*] {fname} の処理サイクルが終了しました。")

if __name__ == "__main__":
    main()