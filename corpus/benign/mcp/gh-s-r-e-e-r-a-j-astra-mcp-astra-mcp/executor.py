# Developer: Sreeraj
# GitHub: https://github.com/s-r-e-e-r-a-j

import asyncio
import os
import secrets
import shutil
import signal
import time
from pathlib import Path
import pty
import fcntl

from astra_mcp.config import ServerConfig, ToolConfig
from astra_mcp.policy import expand_argument, validate_arguments, validate_host, validate_path, validate_url_host
from astra_mcp.audit import write_audit


class ToolExecutor:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        self._interactive_sessions: dict[str, dict[str, object]] = {}
        self._interactive_session_limit = max(1, min(config.max_concurrency, 32))

    async def start_command(self, raw_arguments: object) -> dict[str, object]:
        if not self.config.enable_interactive_command_tool:
            raise PermissionError("Interactive command execution is disabled in tools.toml")
        if not isinstance(raw_arguments, dict):
            raise ValueError("Arguments must be an object")
        if set(raw_arguments) - {"executable", "args", "cwd"}:
            raise ValueError("Only executable, args, and cwd are accepted")
        executable_value = raw_arguments.get("executable")
        args_value = raw_arguments.get("args", [])
        cwd_value = raw_arguments.get("cwd")
        if not isinstance(executable_value, str) or not executable_value.strip():
            raise ValueError("executable must be a non-empty string")
        if not isinstance(args_value, list) or not all(isinstance(arg, str) for arg in args_value):
            raise ValueError("args must be a list of strings")
        if cwd_value is not None and not isinstance(cwd_value, str):
            raise ValueError("cwd must be a string when provided")
        values = [executable_value, *args_value]
        if any("\x00" in value or "\r" in value or "\n" in value for value in values):
            raise ValueError("Command arguments cannot contain NUL or newline characters")
        executable = executable_value if Path(executable_value).is_absolute() else shutil.which(executable_value)
        if not executable or not Path(executable).is_file():
            raise FileNotFoundError(f"Executable not found: {executable_value}")
        cwd = None
        if cwd_value:
            cwd = str(Path(cwd_value).expanduser().resolve())
            if not Path(cwd).is_dir():
                raise NotADirectoryError(f"Working directory not found: {cwd}")
        if len(self._interactive_sessions) >= self._interactive_session_limit:
            raise RuntimeError("Interactive session limit reached; stop or finish an existing session first")

        master_fd, slave_fd = pty.openpty()
        try:
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            env = {key: value for key, value in os.environ.items()
                   if key in {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TMPDIR"}}
            env.setdefault("TERM", "xterm")
            async with self.semaphore:
                process = await asyncio.create_subprocess_exec(
                    executable, *args_value, cwd=cwd,
                    stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
                    env=env, start_new_session=True,
                )
        except Exception:
            os.close(master_fd)
            os.close(slave_fd)
            raise
        finally:
            try:
                os.close(slave_fd)
            except OSError:
                pass

        session_id = secrets.token_urlsafe(18)
        session: dict[str, object] = {
            "process": process,
            "master_fd": master_fd,
            "output": bytearray(),
            "cursor": 0,
            "truncated": False,
            "created_at": time.monotonic(),
            "timed_out": False,
            "reader_task": None,
            "watch_task": None,
        }
        self._interactive_sessions[session_id] = session
        session["reader_task"] = asyncio.create_task(self._read_interactive_output(session_id))
        session["watch_task"] = asyncio.create_task(self._watch_interactive_process(session_id))
        write_audit(self.config.audit_log, {
            "tool": "start_command", "session_id": session_id,
            "executable": executable_value, "args": args_value, "cwd": cwd,
        })
        return {"session_id": session_id, "status": "running", "message": "Use read_output to inspect output and send_input to answer prompts."}

    async def _read_interactive_output(self, session_id: str) -> None:
        import errno
        loop = asyncio.get_running_loop()
        session = self._interactive_sessions.get(session_id)
        if session is None:
            return
        fd = int(session["master_fd"])
        limit = self.config.max_output_bytes
        try:
            while True:
                ready = loop.create_future()
                loop.add_reader(fd, lambda: (not ready.done()) and ready.set_result(None))
                try:
                    await ready
                finally:
                    loop.remove_reader(fd)
                try:
                    chunk = os.read(fd, 4096)
                except BlockingIOError:
                    continue
                except OSError as error:
                    if error.errno in {errno.EIO, errno.EBADF}:
                        break
                    raise
                if not chunk:
                    break
                output = session["output"]
                assert isinstance(output, bytearray)
                remaining = limit - len(output)
                if remaining > 0:
                    output.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    session["truncated"] = True
        except asyncio.CancelledError:
            raise
        except Exception as error:
            session["reader_error"] = f"{type(error).__name__}: {error}"

    async def _watch_interactive_process(self, session_id: str) -> None:
        session = self._interactive_sessions.get(session_id)
        if session is None:
            return
        process = session["process"]
        assert isinstance(process, asyncio.subprocess.Process)
        try:
            await asyncio.wait_for(process.wait(), timeout=self.config.default_timeout_seconds)
        except TimeoutError:
            session["timed_out"] = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                process.kill()
            await process.wait()
        except asyncio.CancelledError:
            raise

    async def read_output(self, raw_arguments: object) -> dict[str, object]:
        if not isinstance(raw_arguments, dict) or set(raw_arguments) - {"session_id"}:
            raise ValueError("Arguments must contain only session_id")
        session_id = raw_arguments.get("session_id")
        if not isinstance(session_id, str) or session_id not in self._interactive_sessions:
            raise ValueError("Unknown interactive session_id")
        session = self._interactive_sessions[session_id]
        await asyncio.sleep(0.05)
        output = session["output"]
        assert isinstance(output, bytearray)
        cursor = int(session["cursor"])
        text = bytes(output[cursor:]).decode("utf-8", errors="replace")
        session["cursor"] = len(output)
        process = session["process"]
        assert isinstance(process, asyncio.subprocess.Process)
        reader_task = session["reader_task"]
        if process.returncode is not None and isinstance(reader_task, asyncio.Task):
            await asyncio.gather(reader_task, return_exceptions=True)
            output = session["output"]
            assert isinstance(output, bytearray)
            cursor = int(session["cursor"])
            if cursor < len(output):
                text += bytes(output[cursor:]).decode("utf-8", errors="replace")
                session["cursor"] = len(output)
        return {
            "session_id": session_id,
            "output": text,
            "status": "running" if process.returncode is None else "completed",
            "exit_code": process.returncode,
            "timed_out": bool(session["timed_out"]),
            "truncated": bool(session["truncated"]),
        }

    async def send_input(self, raw_arguments: object) -> dict[str, object]:
        if not isinstance(raw_arguments, dict) or set(raw_arguments) - {"session_id", "text", "append_newline"}:
            raise ValueError("Arguments must contain session_id, text, and optional append_newline")
        session_id = raw_arguments.get("session_id")
        value = raw_arguments.get("text")
        append_newline = raw_arguments.get("append_newline", True)
        if not isinstance(session_id, str) or session_id not in self._interactive_sessions:
            raise ValueError("Unknown interactive session_id")
        if not isinstance(value, str) or "\x00" in value:
            raise ValueError("text must be a string without NUL characters")
        if len(value) > 65536:
            raise ValueError("Input exceeds 65536 characters")
        if not isinstance(append_newline, bool):
            raise ValueError("append_newline must be a boolean")
        session = self._interactive_sessions[session_id]
        process = session["process"]
        assert isinstance(process, asyncio.subprocess.Process)
        if process.returncode is not None:
            raise ValueError("Command has already finished")
        payload = value + ("\n" if append_newline else "")
        fd = int(session["master_fd"])
        await asyncio.to_thread(os.write, fd, payload.encode("utf-8"))
        write_audit(self.config.audit_log, {"tool": "send_input", "session_id": session_id, "input_length": len(value)})
        return {"session_id": session_id, "status": "input_sent", "characters_sent": len(value)}

    async def stop_command(self, raw_arguments: object) -> dict[str, object]:
        if not isinstance(raw_arguments, dict) or set(raw_arguments) - {"session_id"}:
            raise ValueError("Arguments must contain only session_id")
        session_id = raw_arguments.get("session_id")
        if not isinstance(session_id, str) or session_id not in self._interactive_sessions:
            raise ValueError("Unknown interactive session_id")
        session = self._interactive_sessions.pop(session_id)
        process = session["process"]
        assert isinstance(process, asyncio.subprocess.Process)
        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2)
            except TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    process.kill()
                await process.wait()
        for task_name in ("watch_task", "reader_task"):
            task = session.get(task_name)
            if isinstance(task, asyncio.Task) and not task.done():
                task.cancel()
        tasks = [session[name] for name in ("watch_task", "reader_task") if isinstance(session.get(name), asyncio.Task)]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        try:
            os.close(int(session["master_fd"]))
        except OSError:
            pass
        write_audit(self.config.audit_log, {"tool": "stop_command", "session_id": session_id, "exit_code": process.returncode})
        return {"session_id": session_id, "status": "stopped", "exit_code": process.returncode}

    def _build(self, tool: ToolConfig, raw_arguments: object) -> tuple[list[str], str | None]:
        arguments = validate_arguments(tool, raw_arguments)
        executable = shutil.which(tool.executable) if not Path(tool.executable).is_absolute() else tool.executable
        if not executable or not Path(executable).is_file():
            raise FileNotFoundError(f"Executable not found: {tool.executable}")
        command = [executable]
        for template in tool.fixed_args:
            expanded = expand_argument(template, arguments)
            for parameter in tool.parameters:
                if parameter.kind == "string" and parameter.name in arguments:
                    value = str(arguments[parameter.name])
                    if "{"+parameter.name+"}" in template and parameter.name in {"path", "file", "directory", "repo", "output"}:
                        if parameter.name == "output" and not tool.allowed_paths:
                            raise ValueError("Output paths require configured allowed_paths")
                        if tool.allowed_paths:
                            validate_path(value, tool.allowed_paths)
                    if "{"+parameter.name+"}" in template and parameter.name in {"url", "uri"}:
                        validate_url_host(value, tool.allowed_hosts)
                    if "{"+parameter.name+"}" in template and parameter.name in {"target", "host"}:
                        validate_host(value, tool.allowed_hosts)
            command.append(expanded)
        working_directory = None
        if tool.working_directory:
            working_directory = expand_argument(tool.working_directory, arguments)
            working_directory = str(validate_path(working_directory, tool.allowed_paths))
        return command, working_directory

    async def run_dynamic(self, raw_arguments: object) -> dict[str, object]:
        if not self.config.enable_dynamic_command_tool:
            raise PermissionError("Dynamic command execution is disabled")
        if not isinstance(raw_arguments, dict):
            raise ValueError("Arguments must be an object")
        if set(raw_arguments) - {"executable", "args"}:
            raise ValueError("Only executable and args are accepted")
        executable_value = raw_arguments.get("executable")
        args_value = raw_arguments.get("args", [])
        if not isinstance(executable_value, str) or not executable_value.strip():
            raise ValueError("executable must be a non-empty string")
        if not isinstance(args_value, list) or not all(isinstance(arg, str) for arg in args_value):
            raise ValueError("args must be a list of strings")
        values = [executable_value, *args_value]
        if any("\x00" in value or "\r" in value or "\n" in value for value in values):
            raise ValueError("Command arguments cannot contain NUL or newline characters")
        executable = (executable_value if Path(executable_value).is_absolute()
                      else shutil.which(executable_value))
        if not executable or not Path(executable).is_file():
            raise FileNotFoundError(f"Executable not found: {executable_value}")
        command = [executable, *args_value]
        async with self.semaphore:
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=None,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={key: value for key, value in os.environ.items()
                         if key in {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM"}},
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=self.config.default_timeout_seconds
                    )
                except TimeoutError:
                    process.kill()
                    await process.communicate()
                    raise TimeoutError(
                        f"Dynamic command timed out after {self.config.default_timeout_seconds} seconds"
                    )
                limit = self.config.max_output_bytes
                result = {
                    "exit_code": process.returncode,
                    "stdout": stdout[:limit].decode("utf-8", errors="replace"),
                    "stderr": stderr[:limit].decode("utf-8", errors="replace"),
                    "truncated": len(stdout) > limit or len(stderr) > limit,
                }
                write_audit(self.config.audit_log, {
                    "tool": "run_command", "executable": executable_value,
                    "args": args_value, "exit_code": process.returncode,
                })
                return result
            except Exception as error:
                write_audit(self.config.audit_log, {
                    "tool": "run_command", "executable": executable_value,
                    "args": args_value, "error": type(error).__name__,
                })
                raise

    async def run_shell(self, raw_arguments: object) -> dict[str, object]:
        if not self.config.enable_shell_tool:
            raise PermissionError("Shell execution is disabled")
        if not isinstance(raw_arguments, dict):
            raise ValueError("Arguments must be an object")
        if set(raw_arguments) - {"script", "cwd"}:
            raise ValueError("Only script and cwd are accepted")
        script = raw_arguments.get("script")
        cwd_value = raw_arguments.get("cwd")
        if not isinstance(script, str) or not script.strip():
            raise ValueError("script must be a non-empty string")
        if "\\x00" in script:
            raise ValueError("Shell script cannot contain NUL characters")
        if cwd_value is not None and not isinstance(cwd_value, str):
            raise ValueError("cwd must be a string when provided")

        shell = self.config.shell_executable
        shell_path = shell if Path(shell).is_absolute() else shutil.which(shell)
        if not shell_path or not Path(shell_path).is_file():
            raise FileNotFoundError(f"Shell executable not found: {shell}")
        cwd = None
        if cwd_value:
            cwd = str(Path(cwd_value).expanduser().resolve())
            if not Path(cwd).is_dir():
                raise NotADirectoryError(f"Working directory not found: {cwd}")

        env = {key: value for key, value in os.environ.items()
               if key in {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TMPDIR"}}
        async with self.semaphore:
            try:
                process = await asyncio.create_subprocess_exec(
                    shell_path, "-c", script,
                    cwd=cwd,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    start_new_session=True,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=self.config.default_timeout_seconds
                    )
                except TimeoutError:
                    try:
                        os.killpg(process.pid, 9)
                    except (ProcessLookupError, PermissionError):
                        process.kill()
                    await process.communicate()
                    raise TimeoutError(
                        f"Shell command timed out after {self.config.default_timeout_seconds} seconds"
                    )
                limit = self.config.max_output_bytes
                result = {
                    "exit_code": process.returncode,
                    "stdout": stdout[:limit].decode("utf-8", errors="replace"),
                    "stderr": stderr[:limit].decode("utf-8", errors="replace"),
                    "truncated": len(stdout) > limit or len(stderr) > limit,
                    "shell": Path(shell_path).name,
                }
                write_audit(self.config.audit_log, {
                    "tool": "run_shell", "script": script, "cwd": cwd,
                    "exit_code": process.returncode,
                })
                return result
            except Exception as error:
                write_audit(self.config.audit_log, {
                    "tool": "run_shell", "script": script, "cwd": cwd,
                    "error": type(error).__name__,
                })
                raise

    async def run(self, tool: ToolConfig, raw_arguments: object) -> dict[str, object]:
        if not tool.enabled:
            raise PermissionError(f"Tool is disabled: {tool.name}")
        command, working_directory = self._build(tool, raw_arguments)
        async with self.semaphore:
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=working_directory,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env={key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TERM"}},
                )
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=tool.timeout_seconds)
                except TimeoutError:
                    process.kill()
                    await process.communicate()
                    raise TimeoutError(f"Tool timed out after {tool.timeout_seconds} seconds")
                limit = self.config.max_output_bytes
                output = stdout[:limit].decode("utf-8", errors="replace")
                error = stderr[:limit].decode("utf-8", errors="replace")
                result = {"exit_code": process.returncode, "stdout": output, "stderr": error, "truncated": len(stdout) > limit or len(stderr) > limit}
                write_audit(self.config.audit_log, {"tool": tool.name, "arguments": raw_arguments, "exit_code": process.returncode})
                return result
            except Exception as error:
                write_audit(self.config.audit_log, {"tool": tool.name, "arguments": raw_arguments, "error": type(error).__name__})
                raise
