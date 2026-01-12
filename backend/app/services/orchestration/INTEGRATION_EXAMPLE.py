"""
Integration Example: How to use the Intent Parser in API endpoints

This file shows how to integrate the Intent Parser into FastAPI routers
for the orchestration API.

DO NOT USE THIS FILE DIRECTLY - it's an example/template for creating
actual router endpoints in app/routers/orchestration/
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.database import get_db
from app.services.orchestration.intent_parser import IntentParser
from app.routers.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class CommandParseRequest(BaseModel):
    """Request to parse a natural language command"""
    command: str = Field(..., description="Natural language deployment command")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "command": "install postgres with 10GB storage",
                "context": {}
            }
        }


class CommandParseResponse(BaseModel):
    """Response with parsed deployment intent"""
    success: bool
    intent: Dict[str, Any]
    conversational_response: str
    deployment_intent: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "intent": {
                    "action": "install",
                    "application": "postgresql",
                    "confidence": 0.90,
                    "parameters": {"storage": "10Gi"},
                    "dependencies": [],
                    "reasoning": "PostgreSQL database with 10GB storage..."
                },
                "conversational_response": "I'll help you install postgresql...",
                "deployment_intent": {
                    "intent_id": "intent_20260104_123456",
                    "action": "install",
                    "status": "ready"
                }
            }
        }


class QuickActionRequest(BaseModel):
    """Request for quick action extraction"""
    command: str


class QuickActionResponse(BaseModel):
    """Response with just the action"""
    command: str
    action: str
    application: Optional[str] = None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/parse", response_model=CommandParseResponse)
async def parse_deployment_command(
    request: CommandParseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parse a natural language deployment command into structured intent.

    This endpoint uses AI to understand deployment commands and extract:
    - Action to perform (install, update, remove, scale, etc.)
    - Application to target (postgres, nginx, authentik, etc.)
    - Parameters (storage, replicas, version, domain, etc.)
    - Dependencies and reasoning

    Example commands:
    - "install authentik"
    - "scale nginx to 3 replicas"
    - "deploy postgres with 10GB storage"
    - "remove redis"

    Returns:
    - Parsed intent with confidence score
    - Conversational explanation
    - Deployment intent ready for execution
    """
    try:
        # Initialize parser
        parser = IntentParser(db)

        # Parse command
        intent = await parser.parse_command(
            command_text=request.command,
            user_context=request.context
        )

        # Generate conversational response
        conversational_response = await parser.generate_conversational_response(intent)

        # Build deployment intent
        deployment_intent = parser.build_deployment_intent(intent)

        return CommandParseResponse(
            success=True,
            intent=intent,
            conversational_response=conversational_response,
            deployment_intent=deployment_intent
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse command: {str(e)}"
        )


@router.post("/action", response_model=QuickActionResponse)
async def extract_action(
    request: QuickActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Quickly extract just the action and application from a command.

    Useful for UI hints or command validation without full parsing.

    Example:
    - Command: "scale nginx to 3"
    - Returns: {action: "scale", application: "nginx"}
    """
    try:
        parser = IntentParser(db)

        # Extract action and application
        action = await parser.extract_intent(request.command)
        application = await parser.extract_application(request.command)

        return QuickActionResponse(
            command=request.command,
            action=action,
            application=application
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract action: {str(e)}"
        )


@router.get("/context")
async def get_deployment_context(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current deployment context (clusters, deployments, blueprints).

    This shows what information the intent parser uses to make decisions.
    """
    try:
        parser = IntentParser(db)
        context = await parser.gather_context()

        return {
            "success": True,
            "context": context
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to gather context: {str(e)}"
        )


@router.get("/applications")
async def list_supported_applications():
    """
    List all applications recognized by the intent parser.

    Returns application names and their aliases.
    """
    return {
        "success": True,
        "applications": IntentParser.APPLICATIONS
    }


@router.get("/actions")
async def list_supported_actions():
    """
    List all actions supported by the intent parser.

    Actions include: install, update, remove, scale, restart, status, configure
    """
    return {
        "success": True,
        "actions": IntentParser.ACTIONS
    }


# ============================================================================
# EXAMPLE USAGE IN OTHER CODE
# ============================================================================

async def example_usage_in_service():
    """
    Example: How to use the intent parser in service layer code
    """
    from app.database import SessionLocal

    db = SessionLocal()

    try:
        # Initialize parser
        parser = IntentParser(db)

        # Parse a command
        intent = await parser.parse_command("install authentik")

        # Check confidence
        if intent['confidence'] < 0.5:
            print("Low confidence - asking for clarification")
            for question in intent['clarifications_needed']:
                print(f"  - {question}")
            return

        # Check if confirmation needed
        deployment_intent = parser.build_deployment_intent(intent)
        if deployment_intent['requires_confirmation']:
            print("Confirmation required before proceeding")
            print(f"Action: {deployment_intent['action']}")
            print(f"Application: {deployment_intent['application']}")
            return

        # Execute deployment (would call orchestration engine)
        print(f"Executing: {intent['action']} {intent['application']}")
        print(f"Parameters: {intent['parameters']}")

        # Install dependencies first
        for dep in intent['dependencies']:
            print(f"  Installing dependency: {dep}")
            # await orchestration_engine.deploy(dep)

        # Then install main application
        # await orchestration_engine.deploy(intent['application'], intent['parameters'])

        print("Deployment complete!")

    finally:
        db.close()


# ============================================================================
# WEBSOCKET EXAMPLE (for real-time chat interface)
# ============================================================================

from fastapi import WebSocket
import json

@router.websocket("/ws/chat")
async def orchestration_chat(
    websocket: WebSocket,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for conversational orchestration interface.

    Client sends natural language commands, receives real-time responses.
    """
    await websocket.accept()

    parser = IntentParser(db)

    try:
        while True:
            # Receive command from client
            data = await websocket.receive_text()
            message = json.loads(data)

            command = message.get("command", "")

            # Parse command
            intent = await parser.parse_command(command)

            # Generate response
            response = await parser.generate_conversational_response(intent)

            # Send response back
            await websocket.send_json({
                "type": "response",
                "intent": intent,
                "response": response,
                "requires_confirmation": intent.get('confidence', 0) < 0.7
            })

            # If high confidence and no clarifications, could auto-execute
            if intent['confidence'] > 0.8 and not intent['clarifications_needed']:
                # Auto-execute or ask for final confirmation
                await websocket.send_json({
                    "type": "ready_to_execute",
                    "intent_id": parser.build_deployment_intent(intent)['intent_id']
                })

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


# ============================================================================
# CURL EXAMPLES
# ============================================================================

"""
# Parse a deployment command
curl -X POST http://localhost:8000/api/orchestration/parse \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "install postgres with 10GB storage"
  }'

# Quick action extraction
curl -X POST http://localhost:8000/api/orchestration/action \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "command": "scale nginx to 3"
  }'

# Get deployment context
curl http://localhost:8000/api/orchestration/context \
  -H "Authorization: Bearer YOUR_TOKEN"

# List supported applications
curl http://localhost:8000/api/orchestration/applications

# List supported actions
curl http://localhost:8000/api/orchestration/actions
"""
