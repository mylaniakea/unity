# LLM Routing Architecture - Unity

## Overview

Unity has a built-in LLM routing layer that supports multiple AI providers with intelligent fallback and model selection. The system is designed to route requests to different LLM providers based on availability, cost, performance, and tenant preferences.

## Current Implementation

### Supported Providers

Located in: `backend/app/services/ai_provider.py`

1. **OllamaProvider** - Local/self-hosted models
   - Endpoint: `/api/chat`, `/api/generate`
   - Use case: Privacy-first, no-cost inference
   - Models: Any Ollama-compatible model (llama2, mistral, codellama, etc.)

2. **OpenAIProvider** - OpenAI API
   - Models: GPT-4, GPT-3.5-turbo, etc.
   - Use case: High-quality general-purpose inference
   - Requires: API key

3. **AnthropicProvider** - Claude API
   - Models: Claude 3 (Opus, Sonnet, Haiku)
   - Use case: Long context, reasoning tasks
   - Requires: API key

4. **GoogleProvider** - Google AI/Vertex
   - Models: Gemini Pro, Gemini Ultra
   - Use case: Multimodal, Google ecosystem
   - Requires: API key or service account

5. **DisabledProvider** - Fallback
   - Returns disabled message when provider inactive

### Provider Interface

```python
class AIProvider(ABC):
    async def chat(messages, model) -> str
    async def generate(prompt, model) -> str
    async def get_available_models() -> List[str]
```

### Configuration

Providers configured via:
- Environment variables (API keys)
- Database settings per tenant
- Runtime enable/disable flags

```python
config = {
    "api_key": "...",
    "url": "http://localhost:11434",  # For Ollama
    "enabled": True
}
```

## Architecture Diagram

```
┌─────────────┐
│   Client    │
│  (Frontend) │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│      AI Router / Manager            │
│  (backend/app/routers/ai.py)        │
│                                     │
│  - Request validation               │
│  - Tenant isolation                 │
│  - Provider selection               │
│  - Rate limiting                    │
│  - Cost tracking                    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│     Provider Manager                │
│  (backend/app/services/ai.py)       │
│                                     │
│  - Load balancing                   │
│  - Failover logic                   │
│  - Model routing                    │
│  - Caching layer                    │
└──────┬──────────────────────────────┘
       │
       ├──────┬──────┬──────┬─────────┐
       ▼      ▼      ▼      ▼         ▼
   ┌──────┐ ┌───┐ ┌──────┐ ┌──────┐ ┌────┐
   │Ollama│ │OAI│ │Anthr│ │Google│ │Dis│
   └──────┘ └───┘ └──────┘ └──────┘ └────┘
```

## Routing Strategies

### 1. Provider Selection

**Current:** Manual selection via API request

**Proposed Enhancement:**
- **Cost-based**: Route to cheapest available provider
- **Performance-based**: Route based on latency requirements
- **Model-based**: Auto-select provider based on model availability
- **Tenant-based**: Per-tenant provider preferences
- **Task-based**: Different providers for different task types

### 2. Fallback Chain

Example fallback sequence:
```
1. Ollama (local, free) 
   ↓ if unavailable
2. OpenAI GPT-3.5 (fast, cheap)
   ↓ if unavailable  
3. Anthropic Claude Haiku (fallback)
   ↓ if all fail
4. Return error with retry suggestion
```

### 3. Load Balancing

For multiple instances of same provider:
- Round-robin across endpoints
- Least-connections routing
- Health-check based selection

## Storage Integration

### Current Plugin Coverage

Unity has 36 monitoring plugins, including storage-related:
- **disk-monitor**: Local disk usage
- **smart-monitor**: Drive health via SMART
- **zfs-btrfs-monitor**: Advanced filesystem monitoring
- **postgres-monitor**: Database storage metrics
- **mongodb-monitor**: NoSQL storage metrics
- **redis-monitor**: Cache storage metrics
- **influxdb-monitor**: Time-series storage metrics
- **sqlite-monitor**: Embedded DB storage

### Storage Orchestration Opportunities

**LLM + Storage Integration:**

1. **RAG (Retrieval-Augmented Generation)**
   - Vector embeddings in PostgreSQL (pgvector)
   - Knowledge base in existing `knowledge_items` table
   - Plugin data as retrieval source

2. **Model Storage Management**
   - Track Ollama models (disk usage, versions)
   - Auto-cleanup of unused models
   - Model registry with metadata

3. **Inference Cache**
   - Redis for prompt/response caching
   - Reduce API costs and latency
   - Configurable TTL per tenant

4. **Conversation History**
   - PostgreSQL for chat history
   - Per-tenant isolation
   - Export/import capabilities

## Enhancement Roadmap

### Phase 1: Smart Routing (Current → Next)
- [ ] Implement automatic provider fallback
- [ ] Add cost tracking per request
- [ ] Model availability checking
- [ ] Provider health monitoring

### Phase 2: Performance Optimization
- [ ] Response caching (Redis)
- [ ] Streaming responses
- [ ] Batch request handling
- [ ] Connection pooling

### Phase 3: Advanced Features
- [ ] Multi-model ensemble routing
- [ ] A/B testing framework
- [ ] Custom model fine-tuning support
- [ ] Edge model deployment

### Phase 4: Storage Orchestration
- [ ] Vector database for RAG
- [ ] Automated model lifecycle management
- [ ] S3/MinIO integration for model artifacts
- [ ] Backup/restore for conversation history

## API Examples

### Current Usage

```bash
# Chat with specific provider
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama",
    "model": "llama2",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Generate with fallback
curl -X POST http://localhost:8000/api/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "auto",
    "prompt": "Explain Docker",
    "fallback": true
  }'
```

### Proposed Enhancement

```bash
# Smart routing based on requirements
curl -X POST http://localhost:8000/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": {
      "max_cost": 0.001,
      "max_latency_ms": 2000,
      "min_quality": "high"
    },
    "messages": [{"role": "user", "content": "Complex reasoning task"}]
  }'
```

## Configuration Example

`backend/app/config/ai_routing.yaml`:

```yaml
routing:
  default_strategy: cost_optimized
  
  strategies:
    cost_optimized:
      - provider: ollama
        max_load: 0.8
      - provider: openai
        model: gpt-3.5-turbo
        max_cost_per_1k: 0.002
      - provider: anthropic
        model: claude-3-haiku
    
    performance:
      - provider: openai
        model: gpt-4-turbo
      - provider: anthropic
        model: claude-3-opus
    
    privacy_first:
      - provider: ollama
        require_local: true

  caching:
    enabled: true
    backend: redis
    ttl: 3600
    
  rate_limits:
    per_tenant: 1000/hour
    per_provider: 10000/hour
```

## Monitoring

Track via plugins and metrics:
- Request count per provider
- Average latency per provider
- Cost per tenant
- Cache hit rate
- Failover frequency
- Model availability

Integration with existing `plugin_metrics` table for unified monitoring.

## Next Steps

1. ✅ Health check endpoints added
2. ⏳ Implement provider failover logic
3. ⏳ Add Redis caching layer
4. ⏳ Create AI routing configuration system
5. ⏳ Build storage orchestration for models
6. ⏳ Add vector database for RAG
