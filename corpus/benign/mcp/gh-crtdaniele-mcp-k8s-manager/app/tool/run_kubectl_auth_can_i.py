import subprocess

def tool_run_kubectl_auth_can_i(command: str) -> str:
    try:
        result = subprocess.run(
            ["kubectl auth can-i"] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Errore eseguendo il comando run_kubectl_auth_can_i: {e.stderr}"