"""Safe Model Context Protocol (MCP) server for training orchestration."""

import hashlib
import hmac
import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from mcp.server.fastmcp import FastMCP

from llm_training_stack.checkpoints.resume import ResumeManager
from llm_training_stack.config.loader import ConfigLoader
from llm_training_stack.config.schema import TaskType
from llm_training_stack.eval.comparator import RunComparator
from llm_training_stack.lifecycle.manager import LifecycleManager, JobStatus, JobRecord
from llm_training_stack.preflight.data_inspector import PreflightInspectionSuite
from llm_training_stack.preflight.hardware import HardwareInspector
from llm_training_stack.preflight.memory_model import MemoryEstimator

# Transient server-scoped secret generated on startup to prevent autonomous client grant synthesis
_SERVER_STARTUP_SECRET = secrets.token_hex(32)

# Operator-owned maximum memory ceiling for empirical probe subprocesses (MB)
SERVER_MAX_PROBE_MEMORY_MB = 8192

mcp_server = FastMCP(
    name="llm-training-stack",
    instructions="Secure ML training automation server. Separates read/probe from launch permissions. Arbitrary shell execution is strictly disallowed.",
)


def _get_allowed_filesystem_roots() -> List[Path]:
    """Retrieves normalized list of authorized filesystem roots for path jail enforcement."""
    env_roots = os.environ.get("TRAIN_STACK_ALLOWED_ROOTS")
    if env_roots:
        if ";" in env_roots:
            separator = ";"
        elif "," in env_roots:
            separator = ","
        else:
            # Single root path (may contain Windows drive letter like 'C:\...')
            return [Path(env_roots.strip()).resolve()]
        return [Path(r.strip()).resolve() for r in env_roots.split(separator) if r.strip()]

    # Default permitted roots: project root, current working directory, system temp directory, and cache
    project_root = Path(__file__).resolve().parent.parent.parent
    cwd = Path.cwd().resolve()
    temp_dir = Path(tempfile.gettempdir()).resolve()
    home_cache = Path.home().resolve() / ".cache"

    return [project_root, cwd, temp_dir, home_cache]


def validate_path_jail(path_str: Optional[str], field_name: str) -> Optional[Dict[str, Any]]:
    """Enforces path root jail to ensure file/model/dataset paths stay within authorized filesystem roots.

    Returns None if permitted, or an error dictionary if path traversal or unauthorized access is detected.
    """
    if not path_str:
        return None

    # Check for forbidden remote URI schemes unless explicitly authorized
    if "://" in path_str and os.environ.get("TRAIN_STACK_ALLOW_REMOTE_CODE") != "1":
        return {
            "error": "SECURITY_POLICY_VIOLATION",
            "message": f"Arbitrary remote URI scheme in '{field_name}' is forbidden by security policy.",
            "field": field_name,
        }

    # Only model/tokenizer/dataset name fields may be treated as Hugging Face Hub IDs
    is_hub_candidate_field = any(
        k in field_name for k in ("model_name_or_path", "tokenizer_name_or_path", "dataset_name_or_path", "model_path", "tokenizer_path")
    )
    is_filesystem_only_field = any(
        k in field_name for k in ("output_dir", "resume_from", "checkpoint_dir", "run_dirs")
    )

    if is_hub_candidate_field and not is_filesystem_only_field:
        # Standard Hugging Face hub model identifiers (e.g. 'gpt2', 'HuggingFaceTB/SmolLM-135M')
        is_hub_id = (
            not Path(path_str).is_absolute()
            and not path_str.startswith(".")
            and "\\" not in path_str
            and not Path(path_str).exists()
            and ".." not in path_str
        )
        if is_hub_id:
            return None

    # Resolve local filesystem path
    try:
        resolved_path = Path(path_str).resolve()
    except Exception as exc:
        return {
            "error": "PATH_RESOLUTION_FAILED",
            "message": f"Failed to resolve path '{path_str}' in '{field_name}': {exc}",
            "field": field_name,
        }

    allowed_roots = _get_allowed_filesystem_roots()
    is_contained = any(
        resolved_path == root or root in resolved_path.parents
        for root in allowed_roots
    )

    if not is_contained:
        return {
            "error": "PATH_ROOT_JAIL_VIOLATION",
            "message": (
                f"Path '{path_str}' in '{field_name}' resolves to '{resolved_path}', "
                f"which is outside authorized filesystem roots."
            ),
            "field": field_name,
        }

    return None


def compute_plan_binding_string(
    config: Any,
    action: str,
    resume_from: Optional[str] = None,
) -> str:
    """Computes canonical plan binding string encompassing action, model, dataset, resume target, and full config."""
    canonical_cfg = config.model_dump_json() if hasattr(config, "model_dump_json") else json.dumps(config, sort_keys=True)
    model_id = str(getattr(getattr(config, "model", None), "model_name_or_path", ""))
    dataset_id = str(getattr(getattr(config, "dataset", None), "dataset_name_or_path", ""))
    resume_id = str(resume_from or "")
    return f"action={action}|model={model_id}|dataset={dataset_id}|resume={resume_id}|config={canonical_cfg}"


def create_plan_grant(
    config: Any,
    action: str = "launch",
    resume_from: Optional[str] = None,
    secret: Optional[str] = None,
) -> str:
    """Generates an authoritative HMAC authorization grant for a specific training execution plan."""
    signing_secret = secret or os.environ.get("TRAIN_STACK_AUTH_SECRET") or _SERVER_STARTUP_SECRET
    binding_str = compute_plan_binding_string(config, action, resume_from)
    return hmac.new(
        signing_secret.encode("utf-8"),
        binding_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def compute_cancellation_binding_string(target: str) -> str:
    """Computes canonical action-bound cancellation string."""
    return f"action=cancel|target={str(target).strip()}"


def create_cancellation_grant(target: str, secret: Optional[str] = None) -> str:
    """Generates an action-bound HMAC cancellation authorization grant."""
    signing_secret = secret or os.environ.get("TRAIN_STACK_AUTH_SECRET") or os.environ.get("TRAIN_STACK_OPERATOR_TOKEN") or _SERVER_STARTUP_SECRET
    binding_str = compute_cancellation_binding_string(target)
    return hmac.new(
        signing_secret.encode("utf-8"),
        binding_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_mcp_policy(
    config: Any,
    action: str,
    authorized: bool = False,
    authorization_grant: Optional[str] = None,
    resume_from: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Enforces shared server-level operator policy across all mutating and privileged probe paths.

    Returns None if allowed, or an error dictionary if denied.
    Strictly validates before any model loading or network I/O occurs.
    """
    # 1. Path root jail enforcement across model, tokenizer, dataset, output, and resume paths
    model_path = getattr(getattr(config, "model", None), "model_name_or_path", None)
    jail_err = validate_path_jail(model_path, "config.model.model_name_or_path")
    if jail_err is not None:
        return jail_err

    tok_path = getattr(getattr(config, "model", None), "tokenizer_name_or_path", None)
    if tok_path:
        jail_err = validate_path_jail(tok_path, "config.model.tokenizer_name_or_path")
        if jail_err is not None:
            return jail_err

    dataset_path = getattr(getattr(config, "dataset", None), "dataset_name_or_path", None)
    jail_err = validate_path_jail(dataset_path, "config.dataset.dataset_name_or_path")
    if jail_err is not None:
        return jail_err

    output_dir = getattr(getattr(config, "logging", None), "output_dir", None)
    jail_err = validate_path_jail(output_dir, "config.logging.output_dir")
    if jail_err is not None:
        return jail_err

    if resume_from:
        jail_err = validate_path_jail(resume_from, "resume_from")
        if jail_err is not None:
            return jail_err

    # 2. trust_remote_code security boundary (applies to BOTH probe and launch)
    if getattr(getattr(config, "model", None), "trust_remote_code", False) and os.environ.get("TRAIN_STACK_ALLOW_REMOTE_CODE") != "1":
        return {
            "error": "SECURITY_POLICY_VIOLATION",
            "message": (
                "trust_remote_code=True is forbidden by default MCP server security policy. "
                "Arbitrary remote model code execution is blocked. "
                "Set TRAIN_STACK_ALLOW_REMOTE_CODE=1 in the server environment to override."
            ),
        }

    # 3. Privileged empirical probe policy
    if action == "probe":
        if os.environ.get("TRAIN_STACK_ALLOW_PROBE") != "1":
            return {
                "error": "EXECUTION_DENIED_BY_OPERATOR_POLICY",
                "message": (
                    "run_preflight_probe is disabled by operator policy. "
                    "The server operates in read-only inspection mode by default. "
                    "Set TRAIN_STACK_ALLOW_PROBE=1 in server environment to permit empirical memory probing."
                ),
                "operator_policy": "READ_ONLY",
            }
        return None

    # 4. Launch / Submit execution policy
    if action in ("launch", "submit"):
        if not authorized:
            return {
                "error": "EXECUTION_DENIED",
                "message": f"{action}_training requires explicit parameter 'authorized=True'.",
                "authorized": False,
            }

        if os.environ.get("TRAIN_STACK_ALLOW_LAUNCH") != "1":
            return {
                "error": "EXECUTION_DENIED_BY_OPERATOR_POLICY",
                "message": (
                    f"{action}_training is disabled by operator policy. The MCP server runs in read-only mode by default. "
                    "An agent setting authorized=True does not constitute operator authorization. "
                    "Set TRAIN_STACK_ALLOW_LAUNCH=1 in server environment to enable execution."
                ),
                "operator_policy": "READ_ONLY",
            }

        # Authorization grant is REQUIRED by default unless explicit dev bypass is configured
        dev_bypass = os.environ.get("TRAIN_STACK_DEV_BYPASS_GRANT") == "1"
        if not dev_bypass:
            if not authorization_grant:
                return {
                    "error": "AUTHORIZATION_GRANT_REQUIRED",
                    "message": (
                        f"{action}_training requires a plan-bound operator authorization grant. "
                        "Grants must bind action, model, dataset, resume target, and full configuration. "
                        "Set TRAIN_STACK_DEV_BYPASS_GRANT=1 only in local non-production development environments to bypass."
                    ),
                }

            # Plan-bound HMAC signature verification (strictly binds action, model, dataset, resume, and config)
            binding_str = compute_plan_binding_string(config, action, resume_from)
            is_valid_grant = False

            # Secret-keyed HMAC verification (requires full 64-character SHA256 digest)
            candidate_secrets = []
            auth_secret = os.environ.get("TRAIN_STACK_AUTH_SECRET")
            op_secret = os.environ.get("TRAIN_STACK_OPERATOR_TOKEN")
            if auth_secret:
                candidate_secrets.append(auth_secret)
            if op_secret:
                candidate_secrets.append(op_secret)
            candidate_secrets.append(_SERVER_STARTUP_SECRET)

            for sec in candidate_secrets:
                expected_hmac = hmac.new(
                    sec.encode("utf-8"),
                    binding_str.encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if hmac.compare_digest(authorization_grant, expected_hmac):
                    is_valid_grant = True
                    break

            if not is_valid_grant:
                return {
                    "error": "PLAN_GRANT_MISMATCH",
                    "message": "Execution rejected: authorization_grant does not match valid plan-bound operator signature.",
                }

        return None

    return {"error": "UNKNOWN_ACTION", "message": f"Action '{action}' is not recognized."}


@mcp_server.tool()
def inspect_hardware() -> str:
    """Read-only: Inspect local host hardware, CPU, RAM, and GPU/CUDA devices."""
    info = HardwareInspector.inspect()
    return json.dumps(info, indent=2)


@mcp_server.tool()
def estimate_memory(
    total_params: int,
    task_type: str = "sft",
    batch_size: int = 2,
    seq_len: int = 2048,
    mixed_precision: str = "bf16",
    gradient_checkpointing: bool = True,
) -> str:
    """Read-only: Calculate analytical memory breakdown for LLM training."""
    from llm_training_stack.config.schema import DatasetConfig, HardwareConfig, ModelConfig, TrainingJobConfig

    cfg = TrainingJobConfig(
        task_type=TaskType(task_type.lower()),
        model=ModelConfig(model_name_or_path="mock/model"),
        dataset=DatasetConfig(dataset_name_or_path="mock/dataset", max_seq_length=seq_len),
        hardware=HardwareConfig(
            per_device_train_batch_size=batch_size,
            mixed_precision=mixed_precision,
            gradient_checkpointing=gradient_checkpointing,
        ),
    )
    result = MemoryEstimator.estimate(cfg, total_params=total_params)
    return json.dumps(result, indent=2)


@mcp_server.tool()
def audit_tokenizer(
    model_path: str,
    tokenizer_path: Optional[str] = None,
) -> str:
    """Read-only: Inspect vocabulary alignment, missing special tokens, and pad/eos token gotchas.
    Guarded by TRAIN_STACK_ALLOW_PROBE=1 and bounded against arbitrary remote URI protocols and unvalidated paths.
    """
    if os.environ.get("TRAIN_STACK_ALLOW_PROBE") != "1":
        return json.dumps({
            "error": "EXECUTION_DENIED_BY_OPERATOR_POLICY",
            "message": (
                "audit_tokenizer is disabled by operator policy. "
                "Set TRAIN_STACK_ALLOW_PROBE=1 in server environment to enable preflight inspections."
            ),
            "operator_policy": "READ_ONLY",
        }, indent=2)

    tok_target = tokenizer_path or model_path

    # Path jail validation
    jail_err = validate_path_jail(model_path, "model_path") or validate_path_jail(tok_target, "tokenizer_path")
    if jail_err is not None:
        return json.dumps(jail_err, indent=2)

    # Local path existence check (distinguish local paths from valid 1-slash HF Hub IDs)
    for target in [model_path, tok_target]:
        p = Path(target)
        is_hub_like = (
            not p.is_absolute()
            and not target.startswith("./")
            and not target.startswith(".\\")
            and "\\" not in target
            and target.count("/") <= 1
            and not any(k in target for k in ("path", "local", "to", "dir", "tmp"))
        )
        if not is_hub_like and not p.exists():
            return json.dumps({
                "error": "PATH_NOT_FOUND",
                "message": f"Local model/tokenizer path does not exist: '{target}'.",
            }, indent=2)

    try:
        from transformers import AutoConfig, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(tok_target)
        model_cfg = AutoConfig.from_pretrained(model_path)
        report = PreflightInspectionSuite.run_full_inspection(
            model_or_config=model_cfg,
            tokenizer=tokenizer,
        )
        return json.dumps(report, indent=2)
    except Exception as e:
        return json.dumps({"error": "TOKENIZER_AUDIT_FAILED", "message": str(e)}, indent=2)


@mcp_server.tool()
def inspect_checkpoint(checkpoint_dir: str) -> str:
    """Read-only: Verify checkpoint integrity, completeness, and state restoration readiness."""
    jail_err = validate_path_jail(checkpoint_dir, "checkpoint_dir")
    if jail_err is not None:
        return json.dumps(jail_err, indent=2)

    info = ResumeManager.inspect_checkpoint(Path(checkpoint_dir))
    return json.dumps(info, indent=2)


@mcp_server.tool()
def compare_runs(run_dirs: List[str]) -> str:
    """Read-only: Ingest and compare multiple run directories, emitting a Markdown diff table with compatibility checks."""
    for d in run_dirs:
        jail_err = validate_path_jail(d, "run_dirs")
        if jail_err is not None:
            return json.dumps(jail_err, indent=2)

    result = RunComparator.compare_runs(run_dirs)
    return json.dumps(result, indent=2)


@mcp_server.tool()
def run_preflight_probe(
    config_json: str,
    in_subprocess: bool = True,
    max_process_memory_mb: Optional[int] = 4096,
) -> str:
    """Privileged probe: Run a bounded empirical memory probe without initiating full training.
    Separates probing privileges from training execution privileges.
    Guarded by TRAIN_STACK_ALLOW_PROBE=1, trust_remote_code policies, and mandatory subprocess isolation.
    """
    try:
        data = json.loads(config_json)
        config = ConfigLoader.load_from_dict(data)
    except Exception as e:
        return json.dumps({"error": "INVALID_CONFIG", "message": str(e)}, indent=2)

    policy_err = validate_mcp_policy(config, action="probe")
    if policy_err is not None:
        return json.dumps(policy_err, indent=2)

    if not in_subprocess:
        return json.dumps({
            "error": "ISOLATION_POLICY_VIOLATION",
            "message": "in_subprocess=False is disallowed over MCP. Probes must execute in isolated subprocess.",
        }, indent=2)

    # Validate and clamp caller memory ceiling against operator upper bound
    if max_process_memory_mb is not None:
        if max_process_memory_mb <= 0:
            return json.dumps({
                "error": "INVALID_ARGUMENT",
                "message": f"max_process_memory_mb must be a positive integer, got {max_process_memory_mb}",
            }, indent=2)
        memory_ceiling = min(max_process_memory_mb, SERVER_MAX_PROBE_MEMORY_MB)
    else:
        memory_ceiling = 4096

    try:
        from llm_training_stack.preflight.probe import EmpiricalMemoryProbe

        probe_res = EmpiricalMemoryProbe.run_probe_subprocess(
            model_path=config.model.model_name_or_path,
            config=config,
            timeout_seconds=60,
            max_process_memory_mb=memory_ceiling,
        )
        return json.dumps(probe_res, indent=2)
    except Exception as e:
        return json.dumps({"error": "PROBE_FAILED", "message": str(e)}, indent=2)


@mcp_server.tool()
def submit_training_job(
    config_json: str,
    authorized: bool = False,
    authorization_grant: Optional[str] = None,
    resume_from: Optional[str] = None,
    background: bool = True,
) -> str:
    """Durable execution: Asynchronously submit a training job tracked via shared LifecycleManager.
    Requires authorized=True, TRAIN_STACK_ALLOW_LAUNCH=1, and plan-bound authorization_grant.
    """
    try:
        data = json.loads(config_json)
        config = ConfigLoader.load_from_dict(data)
    except Exception as e:
        return json.dumps({"error": "INVALID_CONFIG", "message": str(e)}, indent=2)

    policy_err = validate_mcp_policy(
        config,
        action="submit",
        authorized=authorized,
        authorization_grant=authorization_grant,
        resume_from=resume_from,
    )
    if policy_err is not None:
        return json.dumps(policy_err, indent=2)

    try:
        record = LifecycleManager.submit_job(
            config=config,
            resume_from=resume_from,
            run_in_background=background,
        )
        return json.dumps(record.model_dump(mode="json"), indent=2)
    except Exception as e:
        return json.dumps({"error": "SUBMIT_FAILED", "message": str(e)}, indent=2)


@mcp_server.tool()
def get_training_job_status(run_dir: str) -> str:
    """Read-only: Inspect durable lifecycle status of a submitted training job."""
    try:
        resolved_dir = LifecycleManager.resolve_job_dir(run_dir).resolve()
        target_path_str = str(resolved_dir)
    except Exception as e:
        return json.dumps({"error": "JOB_NOT_FOUND", "message": str(e)}, indent=2)

    jail_err = validate_path_jail(target_path_str, "run_dir")
    if jail_err is not None:
        return json.dumps(jail_err, indent=2)

    try:
        record = LifecycleManager.get_job_status(resolved_dir)
        return json.dumps(record.model_dump(mode="json"), indent=2)
    except Exception as e:
        return json.dumps({"error": "JOB_NOT_FOUND", "message": str(e)}, indent=2)


def resolve_and_validate_cancellation_target(
    run_dir: str,
    authorized: bool = False,
    authorization_grant: Optional[str] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    """Enforces mutating authorization policy for training job cancellation and returns canonical immutable target directory."""
    try:
        resolved_dir = LifecycleManager.resolve_job_dir(run_dir).resolve()
        target_path_str = str(resolved_dir)
    except Exception as e:
        return {"error": "JOB_NOT_FOUND", "message": f"Cannot resolve target job directory '{run_dir}': {e}"}, None

    jail_err = validate_path_jail(target_path_str, "run_dir")
    if jail_err is not None:
        return jail_err, None

    if not authorized:
        return {
            "error": "EXECUTION_DENIED",
            "message": "cancel_training_job requires explicit parameter 'authorized=True'.",
            "authorized": False,
        }, None

    if os.environ.get("TRAIN_STACK_ALLOW_LAUNCH") != "1" and os.environ.get("TRAIN_STACK_ALLOW_CANCEL") != "1":
        return {
            "error": "EXECUTION_DENIED_BY_OPERATOR_POLICY",
            "message": (
                "cancel_training_job is disabled by operator policy. The MCP server runs in read-only mode by default. "
                "Set TRAIN_STACK_ALLOW_LAUNCH=1 or TRAIN_STACK_ALLOW_CANCEL=1 to permit job cancellation."
            ),
            "operator_policy": "READ_ONLY",
        }, None

    dev_bypass = os.environ.get("TRAIN_STACK_DEV_BYPASS_GRANT") == "1"
    if not dev_bypass:
        if not authorization_grant:
            return {
                "error": "AUTHORIZATION_GRANT_REQUIRED",
                "message": (
                    "cancel_training_job requires an action-bound operator cancellation grant. "
                    "Set TRAIN_STACK_DEV_BYPASS_GRANT=1 only in local non-production development environments to bypass."
                ),
            }, None

        candidate_targets = [target_path_str, resolved_dir.as_posix()]
        try:
            rec = JobRecord.load(resolved_dir)
            if rec.job_id:
                candidate_targets.append(str(rec.job_id).strip())
        except Exception:
            pass

        candidate_secrets = []
        auth_secret = os.environ.get("TRAIN_STACK_AUTH_SECRET")
        op_secret = os.environ.get("TRAIN_STACK_OPERATOR_TOKEN")
        if auth_secret:
            candidate_secrets.append(auth_secret)
        if op_secret:
            candidate_secrets.append(op_secret)
        candidate_secrets.append(_SERVER_STARTUP_SECRET)

        is_valid = False
        for sec in candidate_secrets:
            for tgt in candidate_targets:
                expected_hmac = hmac.new(
                    sec.encode("utf-8"),
                    compute_cancellation_binding_string(tgt).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
                if hmac.compare_digest(authorization_grant, expected_hmac):
                    is_valid = True
                    break
            if is_valid:
                break

        if not is_valid:
            return {
                "error": "ACTION_GRANT_MISMATCH",
                "message": "Cancellation rejected: authorization_grant does not match valid action-bound operator signature.",
            }, None

    return None, resolved_dir


def validate_cancellation_policy(
    run_dir: str,
    authorized: bool = False,
    authorization_grant: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Backward-compatible validation helper returning error dict or None."""
    err, _ = resolve_and_validate_cancellation_target(
        run_dir=run_dir,
        authorized=authorized,
        authorization_grant=authorization_grant,
    )
    return err


@mcp_server.tool()
def cancel_training_job(
    run_dir: str,
    authorized: bool = False,
    authorization_grant: Optional[str] = None,
    wait: bool = True,
    timeout: float = 10.0,
) -> str:
    """Mutating: Cancel an active training job with action-bound operator authorization."""
    policy_err, target_path = resolve_and_validate_cancellation_target(
        run_dir,
        authorized=authorized,
        authorization_grant=authorization_grant,
    )
    if policy_err is not None:
        return json.dumps(policy_err, indent=2)

    assert target_path is not None
    try:
        # Mutates strictly against the validated, immutable resolved directory
        record = LifecycleManager.cancel_job(target_path, wait=wait, timeout=timeout)
        result = record.model_dump(mode="json")
        result["cancellation_token_created"] = (target_path / "cancel.token").exists()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": "CANCEL_FAILED", "message": str(e)}, indent=2)


@mcp_server.tool()
def get_training_job_logs(run_dir: str, tail_lines: int = 50) -> str:
    """Read-only: Retrieve recent structured event logs from an active or finished training job."""
    try:
        resolved_dir = LifecycleManager.resolve_job_dir(run_dir).resolve()
        target_path_str = str(resolved_dir)
    except Exception as e:
        return json.dumps({"error": "JOB_NOT_FOUND", "message": str(e)}, indent=2)

    jail_err = validate_path_jail(target_path_str, "run_dir")
    if jail_err is not None:
        return json.dumps(jail_err, indent=2)

    try:
        events = LifecycleManager.get_job_logs(resolved_dir, tail_lines=tail_lines)
        return json.dumps(events, indent=2)
    except Exception as e:
        return json.dumps({"error": "LOGS_FAILED", "message": str(e)}, indent=2)


@mcp_server.tool()
def launch_training(
    config_json: str,
    authorized: bool = False,
    authorization_grant: Optional[str] = None,
    resume_from: Optional[str] = None,
) -> str:
    """Guarded execution: Launch a training job synchronously through durable LifecycleManager.
    Requires caller confirmation (authorized=True), server operator policy (TRAIN_STACK_ALLOW_LAUNCH=1),
    and validates plan-bound authorization grant.
    """
    try:
        data = json.loads(config_json)
        config = ConfigLoader.load_from_dict(data)
    except Exception as e:
        return json.dumps({"error": "INVALID_CONFIG", "message": str(e)}, indent=2)

    policy_err = validate_mcp_policy(
        config,
        action="launch",
        authorized=authorized,
        authorization_grant=authorization_grant,
        resume_from=resume_from,
    )
    if policy_err is not None:
        return json.dumps(policy_err, indent=2)

    if getattr(config.model, "model_name_or_path", "") == "mock":
        return json.dumps({"status": "MOCK_VERIFIED", "message": "Policy authorization grant accepted for mock plan."}, indent=2)

    try:
        record = LifecycleManager.submit_job(
            config=config,
            resume_from=resume_from,
            run_in_background=False,
        )
        if record.status == JobStatus.COMPLETED:
            return json.dumps(record.metrics, indent=2)
        else:
            return json.dumps({"error": "TRAINING_FAILED", "status": record.status.value, "message": record.error}, indent=2)
    except Exception as e:
        return json.dumps({"error": "TRAINING_FAILED", "message": str(e)}, indent=2)


def run_server():
    """Runs the FastMCP server via stdio transport."""
    mcp_server.run()


if __name__ == "__main__":
    run_server()
