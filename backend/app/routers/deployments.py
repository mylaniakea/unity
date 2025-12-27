"""
Deployments API Router

REST API for managing Docker Compose stacks.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.deployment_manager import deployment_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/deployments", tags=["Deployments"])


# Pydantic models
class StackCreate(BaseModel):
    name: str = Field(..., description="Stack name")
    compose_content: str = Field(..., description="Docker Compose YAML content")
    deploy: bool = Field(True, description="Deploy immediately after creation")


class StackUpdate(BaseModel):
    compose_content: str = Field(..., description="Updated Docker Compose YAML content")
    redeploy: bool = Field(True, description="Redeploy after update")


class StackResponse(BaseModel):
    name: str
    path: str
    compose_file: str
    status: Optional[str] = None
    containers: int = 0
    running: int = 0
    created_at: str
    updated_at: str


class StackDetailResponse(StackResponse):
    compose_content: str
    compose_data: dict


class ConvertDockerRunRequest(BaseModel):
    docker_run_command: str = Field(..., description="Docker run command to convert")


class ConvertDockerRunResponse(BaseModel):
    compose_content: str


# Endpoints
@router.get("/stacks", response_model=List[StackResponse])
async def list_stacks():
    """List all stacks."""
    try:
        stacks = deployment_manager.list_stacks()
        return stacks
    except Exception as e:
        logger.error(f"Error listing stacks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stacks/{stack_name}")
async def get_stack(stack_name: str):
    """Get detailed information about a stack."""
    try:
        stack = deployment_manager.get_stack(stack_name)
        if not stack:
            raise HTTPException(status_code=404, detail=f"Stack '{stack_name}' not found")
        return stack
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stacks", response_model=StackDetailResponse, status_code=201)
async def create_stack(stack: StackCreate):
    """Create a new stack."""
    try:
        result = await deployment_manager.create_stack(
            name=stack.name,
            compose_content=stack.compose_content,
            deploy=stack.deploy
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/stacks/{stack_name}", response_model=StackDetailResponse)
async def update_stack(stack_name: str, stack: StackUpdate):
    """Update an existing stack."""
    try:
        result = await deployment_manager.update_stack(
            name=stack_name,
            compose_content=stack.compose_content,
            redeploy=stack.redeploy
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/stacks/{stack_name}", status_code=204)
async def delete_stack(
    stack_name: str,
    stop_containers: bool = Query(True, description="Stop containers before deleting")
):
    """Delete a stack."""
    try:
        await deployment_manager.delete_stack(stack_name, stop_containers=stop_containers)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stacks/{stack_name}/start")
async def start_stack(stack_name: str):
    """Start a stopped stack."""
    try:
        result = await deployment_manager.start_stack(stack_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stacks/{stack_name}/stop")
async def stop_stack(stack_name: str):
    """Stop a running stack."""
    try:
        result = await deployment_manager.stop_stack(stack_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error stopping stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stacks/{stack_name}/restart")
async def restart_stack(stack_name: str):
    """Restart a stack."""
    try:
        result = await deployment_manager.restart_stack(stack_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error restarting stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stacks/{stack_name}/logs")
async def get_stack_logs(
    stack_name: str,
    follow: bool = Query(False, description="Follow logs in real-time"),
    tail: int = Query(100, description="Number of lines from end")
):
    """
    Stream logs from all containers in a stack.
    Uses Server-Sent Events for live streaming when follow=true.
    """
    try:
        async def log_generator():
            """Generate log lines for streaming."""
            async for log_line in deployment_manager.get_stack_logs(stack_name, follow=follow, tail=tail):
                yield f"data: {log_line}\n\n"
        
        if follow:
            return StreamingResponse(
                log_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # Return all logs at once
            logs = []
            async for log_line in deployment_manager.get_stack_logs(stack_name, follow=False, tail=tail):
                logs.append(log_line)
            return {"logs": logs}
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting logs for stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stacks/{stack_name}/metrics")
async def get_stack_metrics(stack_name: str):
    """Get resource metrics for a stack."""
    try:
        metrics = deployment_manager.get_stack_metrics(stack_name)
        return metrics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting metrics for stack {stack_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert", response_model=ConvertDockerRunResponse)
async def convert_docker_run(request: ConvertDockerRunRequest):
    """
    Convert a docker run command to Docker Compose format.
    
    This is a simplified converter - for production use, consider integrating
    with composerize or a similar tool.
    """
    try:
        # Basic conversion logic (placeholder for now)
        # In production, you'd want to use a proper parser like composerize
        command = request.docker_run_command.strip()
        
        # Extract container name
        import re
        name_match = re.search(r'--name\s+(\S+)', command)
        container_name = name_match.group(1) if name_match else 'app'
        
        # Extract image
        image_match = re.search(r'\s+([^\s-]+:[^\s]+|\S+/\S+:\S+)(?:\s|$)', command)
        image = image_match.group(1) if image_match else 'nginx:latest'
        
        # Extract ports
        ports = []
        port_matches = re.finditer(r'-p\s+(\d+):(\d+)', command)
        for match in port_matches:
            ports.append(f"      - \"{match.group(1)}:{match.group(2)}\"")
        
        # Extract volumes
        volumes = []
        volume_matches = re.finditer(r'-v\s+([^:]+):([^\s]+)', command)
        for match in volume_matches:
            volumes.append(f"      - \"{match.group(1)}:{match.group(2)}\"")
        
        # Extract environment variables
        envs = []
        env_matches = re.finditer(r'-e\s+(\S+)', command)
        for match in envs_matches:
            envs.append(f"      - {match.group(1)}")
        
        # Build compose file
        compose = f"""version: '3.8'

services:
  {container_name}:
    image: {image}
    container_name: {container_name}
"""
        
        if ports:
            compose += "    ports:\n" + "\n".join(ports) + "\n"
        
        if volumes:
            compose += "    volumes:\n" + "\n".join(volumes) + "\n"
        
        if envs:
            compose += "    environment:\n" + "\n".join(envs) + "\n"
        
        compose += "    restart: unless-stopped\n"
        
        return {"compose_content": compose}
    
    except Exception as e:
        logger.error(f"Error converting docker run command: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to convert: {str(e)}")
