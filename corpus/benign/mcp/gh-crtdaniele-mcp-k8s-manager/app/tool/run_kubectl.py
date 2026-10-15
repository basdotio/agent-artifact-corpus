import subprocess

def tool_run_kubectl(command: str) -> str:
    try:
        result = subprocess.run(
            ["kubectl"] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Errore eseguendo il comando run_kubectl: {e.stderr}"