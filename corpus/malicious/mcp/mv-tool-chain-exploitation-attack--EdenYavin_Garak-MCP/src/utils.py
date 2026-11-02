import requests
import subprocess

def get_installed_ollama_models():
    """
    Fetch a list of all installed Ollama models.
    
    Returns:
        list: A list of installed model names
    """
    try:
        response = requests.get('http://localhost:11434/api/tags')
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        return [model['name'] for model in data.get('models', [])]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Ollama models: {e}")
        return []

def get_terminal_commands_output(command: list[str]):
    """
    Run a command in the terminal and return the output and process ID.
    
    Returns:
        tuple: A tuple containing (output_lines, process_id)
    """
    try:
        # Run the command and capture both stdout and stderr
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        print(f"Process ID: {process.pid}")
        
        # Read output in real-time
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                line = line.strip()
                if line:  # Only add non-empty lines
                    output_lines.append(line)
                    print(line)  # Print output in real-time
        
        # Get any remaining output
        remaining_output, stderr = process.communicate()
        if remaining_output:
            lines = [line.strip() for line in remaining_output.split('\n') if line.strip()]
            output_lines.extend(lines)
            for line in lines:
                print(line)
        
        if stderr:
            print(f"Error output: {stderr}")
            
        return output_lines, process.pid
    except subprocess.SubprocessError as e:
        print(f"Error running command {command}: {e}")
        return [], None


def generate_ollama_response(model: str, prompt: str) -> str:
    """
    Generate a response from an Ollama model.

    Args:
        model (str): The name of the Ollama model to use (e.g., "llama3.2:3b")
        prompt (str): The prompt to send to the model

    Returns:
        str: The model's response
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"Error generating response from Ollama: {e}")
        return ""


if __name__ == "__main__":
    
    print("\nAvailable Garak probes:")
    probes, pid = get_terminal_commands_output(['garak', '--list_probes'])
    print(f"Process ID: {pid}")
    for probe in probes:
        print(f"- {probe}") 