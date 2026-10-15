import subprocess

def tool_run_kubectx(command: str) -> str:
    try:
        result = subprocess.run(
            ["kubectx"] + command.split(),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Errore eseguendo il comando run_kubectx: {e.stderr}"