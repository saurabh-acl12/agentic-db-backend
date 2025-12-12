from typing import Optional, List, Dict, Any, Union
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import Generation, LLMResult
from pydantic import Field
import requests
import json

class OllamaLLM(LLM):
    """Wrapper around Ollama's API."""
    
    base_url: str = Field("http://localhost:11434")
    model: str = Field("gemma3:4b")  # Default to your local model
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    
    @property
    def _llm_type(self) -> str:
        return "ollama"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Call the Ollama API."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            }
        }
        
        if self.max_tokens:
            payload["options"]["num_predict"] = self.max_tokens
            
        if stop:
            payload["stop"] = stop
            
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "").strip()
        except Exception as e:
            raise Exception(f"Error calling Ollama API: {str(e)}")
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Async call to Ollama API."""
        import aiohttp
        
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
            }
        }
        
        if self.max_tokens:
            payload["options"]["num_predict"] = self.max_tokens
            
        if stop:
            payload["stop"] = stop
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                    return result.get("response", "").strip()
        except Exception as e:
            raise Exception(f"Error calling Ollama API: {str(e)}")
