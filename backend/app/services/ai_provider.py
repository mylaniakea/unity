from abc import ABC, abstractmethod
import httpx
from typing import Dict, Any, List

class AIProvider(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key", "")
        self.url = config.get("url", "")
        self.enabled = config.get("enabled", False)

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        """Send chat messages to provider"""
        pass

    @abstractmethod
    async def generate(self, prompt: str, model: str) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get a list of available models for this provider"""
        pass

class OllamaProvider(AIProvider):
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        if not self.enabled: return "Provider disabled"
        url = f"{self.url.rstrip('/')}/api/chat"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json={"model": model, "messages": messages, "stream": False}, timeout=60.0)
                res.raise_for_status()
                return res.json().get("message", {}).get("content", "No content")
        except Exception as e:
            raise Exception(f"Ollama Error: {str(e)}")

    async def generate(self, prompt: str, model: str) -> str:
        if not self.enabled: return "Provider disabled"
        url = f"{self.url.rstrip('/')}/api/generate"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=60.0)
                res.raise_for_status()
                return res.json().get("response", "No response")
        except Exception as e:
            raise Exception(f"Ollama Error: {str(e)}")

    async def get_available_models(self) -> List[str]:
        if not self.enabled: return []
        url = f"{self.url.rstrip('/')}/api/tags"
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(url, timeout=30.0)
                res.raise_for_status()
                return [m["name"] for m in res.json().get("models", [])]
        except Exception as e:
            print(f"Ollama model fetch error: {e}")
            return []

class OpenAIProvider(AIProvider):
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        if not self.enabled: return "Provider disabled"
        if not self.api_key: raise Exception("OpenAI API key not configured.")
        try:
            async with httpx.AsyncClient() as client:
                # Basic OpenAI Chat Completion
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": model, "messages": messages},
                    timeout=60.0
                )
                res.raise_for_status()
                return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"OpenAI Error: {str(e)}")

    async def generate(self, prompt: str, model: str) -> str:
        return await self.chat([{"role": "user", "content": prompt}], model)
    
    async def get_available_models(self) -> List[str]:
        if not self.enabled or not self.api_key: return []
        return ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]

class AnthropicProvider(AIProvider):
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
        if not self.enabled: return "Provider disabled"
        if not self.api_key: raise Exception("Anthropic API key not configured.")
        try:
             async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={"model": model, "messages": messages, "max_tokens": 1024},
                    timeout=60.0
                )
                res.raise_for_status()
                return res.json()["content"][0]["text"]
        except Exception as e:
            raise Exception(f"Anthropic Error: {str(e)}")

    async def generate(self, prompt: str, model: str) -> str:
        return await self.chat([{"role": "user", "content": prompt}], model)

    async def get_available_models(self) -> List[str]:
        if not self.enabled or not self.api_key: return []
        return ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]

# Google (Gemini) - Simplified for example
class GoogleProvider(AIProvider):
    async def chat(self, messages: List[Dict[str, str]], model: str) -> str:
         if not self.enabled: return "Provider disabled"
         if not self.api_key: raise Exception("Google API key not configured.")
         # Google implementation logic using generatingContent (can be REST or SDK)
         # Using REST for consistency
         url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
         
         # Convert OpenAI format messages to Google format
         contents = []
         for m in messages:
             role = "user" if m["role"] == "user" else "model"
             contents.append({"role": role, "parts": [{"text": m["content"]}]})

         try:
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json={"contents": contents}, timeout=60.0)
                res.raise_for_status()
                return res.json()["candidates"][0]["content"]["parts"][0]["text"]
         except Exception as e:
             raise Exception(f"Google Error: {str(e)}")

    async def generate(self, prompt: str, model: str) -> str:
        return await self.chat([{"role": "user", "content": prompt}], model)

    async def get_available_models(self) -> List[str]:
        if not self.enabled or not self.api_key: return []
        return ["gemini-pro", "gemini-1.5-pro-latest"]

class AIOrchestrator:
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.providers: Dict[str, AIProvider] = {
            "ollama": OllamaProvider(settings["providers"].get("ollama", {})),
            "openai": OpenAIProvider(settings["providers"].get("openai", {})),
            "anthropic": AnthropicProvider(settings["providers"].get("anthropic", {})),
            "google": GoogleProvider(settings["providers"].get("google", {}))
        }
    
    def get_provider(self, name: str) -> AIProvider:
        # Ensure provider exists, otherwise return a disabled default or raise error
        provider = self.providers.get(name)
        if provider and provider.enabled: # Only return enabled providers
            return provider
        # Fallback to a default disabled provider or raise an error if strict
        # For now, let's return a dummy disabled provider if the requested one isn't enabled
        class DisabledProvider(AIProvider):
            async def chat(self, messages: List[Dict[str, str]], model: str) -> str: return "Provider disabled or not configured."
            async def generate(self, prompt: str, model: str) -> str: return "Provider disabled or not configured."
            async def get_available_models(self) -> List[str]: return []
        return DisabledProvider({"enabled": False})

    async def chat(self, messages: List[Dict[str, str]], model: str = None) -> str:
        # Get provider-specific active model
        provider_name = self.settings.get("primary_provider", "ollama")
        provider_config = self.settings["providers"].get(provider_name, {})
        active_model_for_provider = provider_config.get("active_model") or self.settings.get("active_model", "")
        
        # If a model is explicitly passed to chat, use it. Otherwise, use the provider's active model.
        target_model = model or active_model_for_provider
        if not target_model:
            raise Exception(f"No active model configured for provider {provider_name}")

        primary_provider_instance = self.get_provider(provider_name)

        try:
            print(f"Attempting Primary: {provider_name} with model {target_model}")
            return await primary_provider_instance.chat(messages, target_model)
        except Exception as e:
            print(f"Primary ({provider_name}) failed ({e}), attempting Fallback...")
            fallback_name = self.settings.get("fallback_provider", "ollama")
            fallback_config = self.settings["providers"].get(fallback_name, {})
            active_model_for_fallback = fallback_config.get("active_model") or self.settings.get("active_model", "")
            
            target_model_fallback = model or active_model_for_fallback
            if not target_model_fallback:
                 raise Exception(f"No active model configured for fallback provider {fallback_name}")

            fallback_provider_instance = self.get_provider(fallback_name)
            try:
                return await fallback_provider_instance.chat(messages, target_model_fallback)
            except Exception as e2:
                return f"Both providers failed. Primary ({provider_name}): {e}, Fallback ({fallback_name}): {e2}"
    
    async def generate(self, prompt: str, model: str = None) -> str:
        # Re-use chat logic for generation
        return await self.chat([{"role": "user", "content": prompt}], model)
    
    async def get_all_provider_models(self) -> Dict[str, List[str]]:
        all_models = {}
        for name, provider_instance in self.providers.items():
            if provider_instance.enabled: # Only fetch models for enabled providers
                try:
                    models = await provider_instance.get_available_models()
                    all_models[name] = models
                except Exception as e:
                    print(f"Error fetching models for {name}: {e}")
                    all_models[name] = [] # Return empty list on error
        return all_models
