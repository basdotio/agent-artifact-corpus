"""Read-only diagnostics and CLI-child stage instrumentation; no lock recovery."""
import json
from pathlib import Path
import re
import sys
import time

CURRENT_STAGE = 'engine_initialization'


def diagnose(message):
    text = message.lower()
    # Specific failures precede incidental backend/cache names in tracebacks.
    groups = [
        ('permission_denied', '权限问题', r'permission denied|access is denied|permissionerror|winerror 5\b|拒绝访问'),
        ('cache_lock_timeout', '缓存锁等待超时或占用', r'filelock\..*timeout|file lock.*could not be acquired|lock.*(?:timeout|timed out)|winerror 32\b|sharing violation'),
        ('conversion_timeout', '本次转换超时或中断', r'转换超时|timeoutexpired'),
        ('out_of_memory', '内存不足', r'out of memory|memoryerror|cannot allocate'),
        ('engine_missing', 'OCR 本地推理引擎缺失', r'(?:llama-server|llamacpp).*(?:not found|no such file|未找到|需要)|(?:not found|no such file).*llama-server'),
        ('dependency_error', 'Python 环境或依赖问题', r'modulenotfounderror|importerror|no module named|dll load|no matching distribution'),
        ('invalid_pdf', 'PDF 损坏、加密或格式不受支持', r'pdfium|invalid pdf|password|encrypted|failed to load document'),
        ('network_error', '模型下载或网络问题', r'connectionerror|ssl|connection refused|connecttimeout|readtimeout|huggingface.*(?:error|failed)'),
        ('engine_error', 'OCR 本地推理后端异常', r'llama-server|llamacpp|vllm|docker|inference server'),
        ('path_error', '输出路径问题', r'no such file|not a directory|filename too long'),
    ]
    code, label = next(((code, label) for code, label, pattern in groups if re.search(pattern, text)),
                       ('unknown', '未能自动归类；请查看保存的日志'))
    action = ('等待持锁任务完成后再重试；锁文件存在本身不证明陈旧，不自动删除锁或终止其他任务。'
              if code == 'cache_lock_timeout' else
              '检查当前用户对缓存/输出目录的访问权限，不自动重装依赖。' if code == 'permission_denied' else
              '指定现有 llama-server 及配套 DLL；不自动覆盖运行库或下载模型。' if code == 'engine_missing' else
              '查看本次 stdout/stderr 日志，确认原因后再重试。')
    return {'code': code, 'category': label, 'action': action}


def write_status(output, stage, status='running', **details):
    record = {'stage': stage, 'status': status, **details}
    path = Path(output) / 'run_status.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def stage(name):
    global CURRENT_STAGE
    CURRENT_STAGE = name
    print('[marker-pdf2md:stage] ' + name, file=sys.stderr, flush=True)


def install_lock_observer():
    # Observe only this CLI process. Acquire/release semantics remain upstream's.
    try:
        from filelock import BaseFileLock
    except ImportError:
        return
    original = BaseFileLock.acquire
    original_release = BaseFileLock.release
    def acquire(self, *args, **kwargs):
        previous = CURRENT_STAGE
        stage('cache_lock_wait')
        started = time.monotonic()
        try:
            result = original(self, *args, **kwargs)
        except Exception as exc:
            print('Cache lock acquisition failed: ' + str(exc), file=sys.stderr, flush=True)
            raise
        print(f'Cache lock acquired after {time.monotonic()-started:.1f}s', file=sys.stderr, flush=True)
        if not hasattr(self, '_marker_previous_stage'):
            self._marker_previous_stage = previous
        stage('engine_initialization')
        return result
    def release(self, *args, **kwargs):
        result = original_release(self, *args, **kwargs)
        if hasattr(self, '_marker_previous_stage') and not self.is_locked:
            previous = self._marker_previous_stage
            del self._marker_previous_stage
            stage(previous)
        return result
    BaseFileLock.acquire = acquire
    BaseFileLock.release = release
