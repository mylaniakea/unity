import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app import models, schemas_settings
from app.services.ai_provider import AIOrchestrator

async def test_ai_config():
    print("--- Testing AI Configuration & Orchestrator ---")
    
    # 1. Simulate Database Settings Object
    db_settings = models.Settings(
        id=1,
        providers={
            "ollama": {"url": "http://localhost:11434", "enabled": True},
            "openai": {"api_key": "sk-test-key", "enabled": True},
            "anthropic": {"api_key": "", "enabled": False}
        },
        active_model="llama3.2", # Global fallback
        primary_provider="ollama",
        fallback_provider="openai",
        system_prompt="Test Prompt"
    )
    
    print("1. DB Model created successfully.")

    # 2. Convert to Pydantic Schema (Logic used in routers/ai.py)
    # We need to ensure the dict structure matches what Pydantic expects
    # The models.Settings.providers is a JSON field (dict), schemas_settings.SettingsBase.providers is Dict
    
    try:
        settings_schema = schemas_settings.Settings.model_validate(db_settings)
        print("2. Pydantic validation successful.")
        print(f"   Providers: {settings_schema.providers.keys()}")
    except Exception as e:
        print(f"2. Pydantic validation FAILED: {e}")
        return

    # 3. Initialize Orchestrator
    try:
        orchestrator = AIOrchestrator(settings_schema.model_dump())
        print("3. AIOrchestrator initialized.")
    except Exception as e:
        print(f"3. AIOrchestrator init FAILED: {e}")
        return

    # 4. Test Model Fetching (Static lists for OpenAI to avoid network calls)
    print("4. Testing get_all_provider_models...")
    try:
        models_map = await orchestrator.get_all_provider_models()
        print(f"   Result: {models_map}")
        
        if "openai" in models_map and "gpt-4o" in models_map["openai"]:
            print("   SUCCESS: OpenAI models retrieved (static list).")
        else:
            print("   FAILURE: OpenAI models missing or incorrect.")
            
        if "anthropic" not in models_map:
            print("   SUCCESS: Anthropic skipped (disabled).")
        else:
            print("   FAILURE: Anthropic should be skipped.")

    except Exception as e:
        print(f"   Error fetching models: {e}")

if __name__ == "__main__":
    asyncio.run(test_ai_config())
