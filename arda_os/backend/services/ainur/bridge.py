import httpx
import json
import logging

logger = logging.getLogger("ARDA_BRIDGE")

class OllamaBridge:
    def __init__(self, model="qwen2.5:7b", host="http://localhost:11434"):
        self.model = model
        self.host = host

    async def generate(self, prompt: str, format: str = "text") -> str:
        """The real speech of the bridge to the local Ollama substrate."""
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if format == "json":
            payload["format"] = "json"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=120.0)
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")
                else:
                    logger.error(f"Ollama error: {response.status_code} - {response.text}")
                    return ""
            except Exception as e:
                logger.error(f"Connection to Ollama failed: {e}")
                raise RuntimeError(f"Ollama bridge failure: {e}")
