# Unity Tool Companion Integration Design

**Concept:** Unity as an AI-powered Homelab Agent that orchestrates and utilizes companion tool containers (Omni-Tools, IT-Tools) to perform tasks

**Status:** Concept / Design Phase  
**Date:** December 21, 2024

---

## 🎯 Vision

Transform Unity from a monitoring platform into an **intelligent homelab orchestrator** that can:
1. **Deploy companion tool containers** (Omni-Tools, IT-Tools) as sidecars
2. **Expose tool APIs** to Unity's backend for programmatic access
3. **Enable AI agent** to utilize these tools for homelab tasks
4. **Provide unified interface** for all homelab operations

### The Big Picture
```
User Request → Unity AI Agent → Analyzes Task → Selects Tools → Executes → Returns Result
                     ↓
            [Companion Pods]
            - Omni-Tools (image/video/data processing)
            - IT-Tools (dev utilities, converters)
            - Unity Plugins (monitoring, alerts)
```

---

## 🐳 Part 1: Companion Pod Architecture

### Deployment Strategy

**Option A: Docker Compose Stack (Recommended)**
```yaml
# unity-stack.docker-compose.yml
version: '3.9'

services:
  unity-backend:
    image: unity:latest
    container_name: unity-backend
    ports:
      - "8000:8000"
    environment:
      - OMNI_TOOLS_URL=http://omni-tools:80
      - IT_TOOLS_URL=http://it-tools:80
    networks:
      - unity-network
    depends_on:
      - omni-tools
      - it-tools

  omni-tools:
    image: iib0011/omni-tools:latest
    container_name: unity-omni-tools
    restart: unless-stopped
    networks:
      - unity-network
    # No external port - accessed via Unity proxy

  it-tools:
    image: corentinth/it-tools:latest
    container_name: unity-it-tools
    restart: unless-stopped
    networks:
      - unity-network
    # No external port - accessed via Unity proxy

  unity-frontend:
    image: unity-frontend:latest
    container_name: unity-frontend
    ports:
      - "3000:3000"
    networks:
      - unity-network
    depends_on:
      - unity-backend

networks:
  unity-network:
    driver: bridge
```

**Option B: Kubernetes Pod Sidecar Pattern**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: unity-with-tools
spec:
  containers:
  - name: unity-backend
    image: unity:latest
    ports:
    - containerPort: 8000
    env:
    - name: OMNI_TOOLS_URL
      value: "http://localhost:8080"
    - name: IT_TOOLS_URL
      value: "http://localhost:8081"
  
  - name: omni-tools
    image: iib0011/omni-tools:latest
    ports:
    - containerPort: 8080
  
  - name: it-tools
    image: corentinth/it-tools:latest
    ports:
    - containerPort: 8081
```

### Benefits of Companion Pods
- **Single deployment unit** - All components together
- **Internal networking** - Fast, secure communication
- **Unified lifecycle** - Deploy/update/scale together
- **Resource sharing** - Shared volumes, networks
- **No external exposure** - Tools only accessible via Unity

---

## 🔌 Part 2: Tool API Integration

### Exposing Tool Functionality via Unity API

Since Omni-Tools and IT-Tools are **browser-based** (client-side processing), we need to create a **headless API wrapper** around them.

#### Strategy 1: Selenium/Playwright Automation
```python
# backend/app/services/tool_proxy.py
from playwright.async_api import async_playwright
import json

class ToolProxyService:
    """
    Headless browser automation to interact with tool UIs
    """
    
    async def convert_docker_run_to_compose(self, docker_run_command: str) -> str:
        """Use IT-Tools Docker converter"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Navigate to IT-Tools converter
            await page.goto('http://it-tools/docker-run-to-compose')
            
            # Input docker run command
            await page.fill('textarea#input', docker_run_command)
            
            # Wait for conversion
            await page.wait_for_selector('.output')
            
            # Extract result
            result = await page.text_content('.output')
            
            await browser.close()
            return result
    
    async def generate_qr_code(self, text: str) -> bytes:
        """Use IT-Tools QR generator"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            await page.goto('http://it-tools/qr-code-generator')
            await page.fill('input#qr-text', text)
            
            # Wait for QR code generation
            await page.wait_for_selector('img.qr-code')
            
            # Screenshot QR code
            qr_element = await page.query_selector('img.qr-code')
            qr_image = await qr_element.screenshot()
            
            await browser.close()
            return qr_image
    
    async def convert_json_to_yaml(self, json_str: str) -> str:
        """Use IT-Tools JSON to YAML converter"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            await page.goto('http://it-tools/json-to-yaml')
            await page.fill('textarea.json-input', json_str)
            
            # Click convert button
            await page.click('button.convert')
            
            # Get YAML output
            yaml_output = await page.text_content('textarea.yaml-output')
            
            await browser.close()
            return yaml_output
```

#### Strategy 2: Direct Tool Integration (Better!)
Instead of browser automation, **extract and integrate tool logic directly**:

```python
# backend/app/services/docker_converter.py
import yaml

def docker_run_to_compose(docker_run_command: str) -> dict:
    """
    Parse docker run command and convert to docker-compose format
    (Implement IT-Tools logic directly in Python)
    """
    # Parse command arguments
    parts = docker_run_command.split()
    
    compose_config = {
        'version': '3.9',
        'services': {}
    }
    
    service_name = 'service'
    service = {}
    
    i = 0
    while i < len(parts):
        arg = parts[i]
        
        if arg == '--name':
            service_name = parts[i + 1]
            i += 2
        elif arg == '-p' or arg == '--publish':
            if 'ports' not in service:
                service['ports'] = []
            service['ports'].append(parts[i + 1])
            i += 2
        elif arg == '-v' or arg == '--volume':
            if 'volumes' not in service:
                service['volumes'] = []
            service['volumes'].append(parts[i + 1])
            i += 2
        elif arg == '-e' or arg == '--env':
            if 'environment' not in service:
                service['environment'] = []
            service['environment'].append(parts[i + 1])
            i += 2
        elif arg == '--restart':
            service['restart'] = parts[i + 1]
            i += 2
        elif not arg.startswith('-'):
            # This is the image
            service['image'] = arg
            i += 1
        else:
            i += 1
    
    service['container_name'] = service_name
    compose_config['services'][service_name] = service
    
    return compose_config

# API endpoint
@router.post("/tools/docker-run-to-compose")
async def convert_docker_run(command: str):
    compose_dict = docker_run_to_compose(command)
    compose_yaml = yaml.dump(compose_dict, default_flow_style=False)
    return {"compose": compose_yaml}
```

---

## 🤖 Part 3: AI Agent Integration

### Unity AI Agent with Tool Use

```python
# backend/app/services/ai_agent.py
from typing import List, Dict, Any
import anthropic  # or openai
from pydantic import BaseModel

class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class UnityAIAgent:
    """
    AI Agent that can use Unity tools and companion tools
    """
    
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.available_tools = self._register_tools()
    
    def _register_tools(self) -> List[Tool]:
        """Register all available tools"""
        return [
            Tool(
                name="docker_run_to_compose",
                description="Convert a docker run command to docker-compose.yml format",
                parameters={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The docker run command to convert"
                        }
                    },
                    "required": ["command"]
                }
            ),
            Tool(
                name="generate_qr_code",
                description="Generate a QR code for text or URL",
                parameters={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text or URL to encode in QR code"
                        }
                    },
                    "required": ["text"]
                }
            ),
            Tool(
                name="check_container_health",
                description="Check the health status of a Docker container",
                parameters={
                    "type": "object",
                    "properties": {
                        "container_name": {
                            "type": "string",
                            "description": "Name or ID of the container"
                        }
                    },
                    "required": ["container_name"]
                }
            ),
            Tool(
                name="convert_json_to_yaml",
                description="Convert JSON to YAML format",
                parameters={
                    "type": "object",
                    "properties": {
                        "json_string": {
                            "type": "string",
                            "description": "JSON string to convert"
                        }
                    },
                    "required": ["json_string"]
                }
            ),
            Tool(
                name="create_alert_rule",
                description="Create a new alert rule in Unity",
                parameters={
                    "type": "object",
                    "properties": {
                        "metric": {"type": "string"},
                        "threshold": {"type": "number"},
                        "notification_channel": {"type": "string"}
                    },
                    "required": ["metric", "threshold"]
                }
            ),
        ]
    
    async def process_request(self, user_message: str) -> str:
        """
        Process user request using AI with tool capabilities
        """
        messages = [
            {
                "role": "user",
                "content": user_message
            }
        ]
        
        # Send to Claude/GPT with tools
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            tools=[tool.dict() for tool in self.available_tools],
            messages=messages
        )
        
        # Check if AI wants to use tools
        if response.stop_reason == "tool_use":
            tool_results = []
            
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    
                    # Execute tool
                    result = await self._execute_tool(tool_name, tool_input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })
            
            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            
            final_response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=messages
            )
            
            return final_response.content[0].text
        
        else:
            return response.content[0].text
    
    async def _execute_tool(self, tool_name: str, parameters: Dict) -> Any:
        """Execute the requested tool"""
        if tool_name == "docker_run_to_compose":
            from .docker_converter import docker_run_to_compose
            return docker_run_to_compose(parameters["command"])
        
        elif tool_name == "generate_qr_code":
            from .tool_proxy import ToolProxyService
            proxy = ToolProxyService()
            qr_bytes = await proxy.generate_qr_code(parameters["text"])
            # Save to file and return path
            path = f"/tmp/qr_{hash(parameters['text'])}.png"
            with open(path, 'wb') as f:
                f.write(qr_bytes)
            return {"qr_code_path": path}
        
        elif tool_name == "check_container_health":
            import docker
            client = docker.from_env()
            container = client.containers.get(parameters["container_name"])
            return {
                "status": container.status,
                "health": container.attrs['State'].get('Health', {})
            }
        
        elif tool_name == "convert_json_to_yaml":
            import json, yaml
            json_obj = json.loads(parameters["json_string"])
            return yaml.dump(json_obj, default_flow_style=False)
        
        elif tool_name == "create_alert_rule":
            # Call Unity's alert system
            from .alerts import create_alert_rule
            return create_alert_rule(**parameters)
        
        else:
            return {"error": f"Unknown tool: {tool_name}"}


# API Endpoint for AI Agent
@router.post("/ai/chat")
async def ai_chat(message: str):
    agent = UnityAIAgent()
    response = await agent.process_request(message)
    return {"response": response}
```

### Example AI Agent Usage

**User:** "Convert this docker run command to compose: `docker run -d --name nginx -p 80:80 nginx:latest`"

**AI Agent:**
1. Recognizes need for `docker_run_to_compose` tool
2. Calls tool with command as parameter
3. Gets compose YAML back
4. Formats response for user

**User:** "Create a QR code for my Unity dashboard: https://unity.local"

**AI Agent:**
1. Calls `generate_qr_code` tool
2. Gets QR image path
3. Returns download link to user

**User:** "Monitor nginx container and alert me if CPU goes above 80%"

**AI Agent:**
1. Calls `check_container_health` to verify container exists
2. Calls `create_alert_rule` with appropriate parameters
3. Confirms alert rule created

---

## 🎨 Part 4: Unity UI Integration

### Tool Access via Unity Dashboard

```typescript
// frontend/src/components/ToolsPanel.tsx
import React, { useState } from 'react';

const ToolsPanel: React.FC = () => {
  const [dockerRun, setDockerRun] = useState('');
  const [composeOutput, setComposeOutput] = useState('');

  const convertToCompose = async () => {
    const response = await fetch('/api/tools/docker-run-to-compose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command: dockerRun })
    });
    
    const result = await response.json();
    setComposeOutput(result.compose);
  };

  return (
    <div className="tools-panel">
      <h2>🛠️ Unity Tools</h2>
      
      <div className="tool-section">
        <h3>Docker Run → Compose Converter</h3>
        <textarea 
          value={dockerRun}
          onChange={(e) => setDockerRun(e.target.value)}
          placeholder="Paste docker run command..."
          rows={4}
        />
        <button onClick={convertToCompose}>Convert</button>
        
        {composeOutput && (
          <pre className="compose-output">
            {composeOutput}
          </pre>
        )}
      </div>
      
      <div className="tool-section">
        <h3>🤖 AI Assistant</h3>
        <AIChat />
      </div>
    </div>
  );
};
```

---

## 🔄 Part 5: Reverse Proxy Integration

### Accessing Tools via Unity Subdirectories

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

# Proxy requests to companion tools
@app.get("/tools/omni/{path:path}")
async def proxy_omni_tools(path: str):
    """Proxy to Omni-Tools"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni-tools/{path}")
        return HTMLResponse(content=response.content, status_code=response.status_code)

@app.get("/tools/it/{path:path}")
async def proxy_it_tools(path: str):
    """Proxy to IT-Tools"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://it-tools/{path}")
        return HTMLResponse(content=response.content, status_code=response.status_code)

# User accesses:
# - http://unity.local/tools/omni/  → Omni-Tools UI
# - http://unity.local/tools/it/    → IT-Tools UI
# - http://unity.local/             → Unity Dashboard
```

---

## 📊 Implementation Phases

### Phase 1: Companion Pod Setup (1 week)
- [ ] Create unified docker-compose stack
- [ ] Configure internal networking
- [ ] Test tool accessibility from Unity backend
- [ ] Add environment variable configuration

### Phase 2: Direct Tool Integration (2 weeks)
- [ ] Implement docker-run-to-compose converter in Python
- [ ] Implement JSON/YAML converters
- [ ] Implement QR code generator
- [ ] Create REST API endpoints for tools
- [ ] Add tool usage to existing Unity plugins

### Phase 3: AI Agent Foundation (2 weeks)
- [ ] Integrate AI SDK (Anthropic/OpenAI)
- [ ] Implement tool registration system
- [ ] Create tool execution framework
- [ ] Build chat interface in frontend
- [ ] Test tool calling with AI

### Phase 4: Advanced Agent Capabilities (2-3 weeks)
- [ ] Multi-step task execution
- [ ] Context retention across conversations
- [ ] Proactive monitoring suggestions
- [ ] Automated remediation actions
- [ ] Natural language plugin configuration

### Phase 5: UI Polish & Integration (1 week)
- [ ] Unified tools dashboard
- [ ] Reverse proxy for tool UIs
- [ ] AI chat widget in sidebar
- [ ] Tool usage analytics
- [ ] Documentation and examples

---

## 🎯 Use Cases

### Homelab Operations
1. **User:** "My nginx container keeps crashing, help me debug it"
   **Agent:** Checks logs, finds OOM errors, suggests memory limit increase, offers to update docker-compose

2. **User:** "Convert all my docker run commands in this file to compose"
   **Agent:** Reads file, converts each command, creates single compose file

3. **User:** "Create QR codes for all my homelab services"
   **Agent:** Lists services, generates QR for each URL, creates downloadable PDF

4. **User:** "Setup monitoring for my new Plex container"
   **Agent:** Detects Plex container, suggests relevant metrics to track, creates plugin config, sets up alerts

### Developer Utilities
5. **User:** "Convert this JSON config to YAML for my K8s deployment"
   **Agent:** Uses converter tool, validates syntax, returns YAML

6. **User:** "Generate a secure JWT secret"
   **Agent:** Uses IT-Tools token generator, returns secure random string

### Automation
7. **User:** "Every day at 3am, check if any containers are using >90% memory"
   **Agent:** Creates scheduled job, configures alert, tests execution

---

## 🔒 Security Considerations

1. **Tool Isolation**: Companion tools run in isolated containers
2. **No External Access**: Tools only accessible via Unity proxy
3. **API Authentication**: All tool endpoints require Unity auth
4. **AI Safety**: Implement approval workflows for destructive actions
5. **Audit Logging**: Log all AI agent actions
6. **Rate Limiting**: Prevent AI agent abuse

---

## 📈 Future Enhancements

1. **Plugin Marketplace**: Community-contributed tools
2. **Tool Composition**: Chain multiple tools together
3. **Visual Workflow Builder**: Drag-and-drop tool workflows
4. **Voice Interface**: "Hey Unity, check my containers"
5. **Mobile App**: Tool access from phone
6. **Multi-Agent System**: Specialized agents for different tasks

---

**Status:** Ready for Phase 1 implementation! 🚀  
**Next Steps:** 
1. Create unified docker-compose stack
2. Test companion pod communication
3. Begin docker-run-to-compose implementation

