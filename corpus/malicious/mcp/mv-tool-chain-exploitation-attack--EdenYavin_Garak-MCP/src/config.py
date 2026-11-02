import os
from dotenv import load_dotenv
import requests
import subprocess
from typing import Dict, List, Optional

# Load environment variables
load_dotenv()

class ModelConfig:
    def __init__(self):
        self.parallel_attempts = 1  # Default value
        self.model_types = {
            "ollama": {
                "type": "rest",
                "api_url": "http://localhost:11434/api/generate",
                "models": self._get_ollama_models
            },
            "openai": {
                "type": "openai",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "models": self._get_openai_models
            },
            "huggingface": {
                "type": "huggingface",
                "api_key": os.getenv("HUGGINGFACE_API_KEY"),
                "models": self._get_huggingface_models
            },
            "ggml": {
                "type": "ggml",
                "models": self._get_ggml_models
            }
        }

    def _get_ollama_models(self) -> List[str]:
        """Get list of installed Ollama models"""
        try:
            response = requests.get('http://localhost:11434/api/tags')
            response.raise_for_status()
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Ollama models: {e}")
            return []

    def _get_openai_models(self) -> List[str]:
        """Get list of configured OpenAI models"""
        models = os.getenv("OPENAI_MODELS", "").split(",")
        return [model.strip() for model in models if model.strip()]

    def _get_huggingface_models(self) -> List[str]:
        """Get list of configured HuggingFace models"""
        models = os.getenv("HUGGINGFACE_MODELS", "").split(",")
        return [model.strip() for model in models if model.strip()]

    def _get_ggml_models(self) -> List[str]:
        """Get list of configured GGML models"""
        models = os.getenv("GGML_MODELS", "").split(",")
        return [model.strip() for model in models if model.strip()]

    def set_parallel_attempts(self, attempts: int):
        """
        Set the number of parallel attempts for attacks.
        
        Args:
            attempts (int): The number of parallel attempts to run
        """
        if attempts < 1:
            raise ValueError("Number of parallel attempts must be at least 1")
        self.parallel_attempts = attempts

    def get_rest_config(self, uri: str, model_name: str) -> Dict:
        """Get REST configuration for a given model name"""
        return {
            "uri": uri,
            "method": "post",
            "headers": {
                "Content-Type": "application/json"
                },
                "req_template_json_object": {
                    "model": model_name,
                    "prompt": "$INPUT",
                    "stream": False
                },
                "response_json": True,
                "response_json_field": "response"
            }
        
    def list_models(self, model_type: str) -> List[str]:
        """
        List available models for a given model type.
        
        Args:
            model_type (str): The type of model (ollama, openai, huggingface, ggml)
            
        Returns:
            List[str]: List of available model names
        """
        if model_type not in self.model_types:
            raise ValueError(f"Invalid model type: {model_type}")
        
        return self.model_types[model_type]["models"]()

    def get_model_type_info(self, model_type: str) -> Dict:
        """
        Get configuration information for a model type.
        
        Args:
            model_type (str): The type of model
            
        Returns:
            Dict: Configuration information for the model type
        """
        if model_type not in self.model_types:
            raise ValueError(f"Invalid model type: {model_type}")
        
        return self.model_types[model_type] 
    

if __name__ == "__main__":
    config = ModelConfig()
    print(config.list_models("ollama"))
    print(config.list_models("openai"))
    print(config.list_models("huggingface"))
    print(config.list_models("ggml"))
