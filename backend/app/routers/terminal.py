import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.services.ssh import SSHService
import asyncssh

router = APIRouter(
    prefix="/terminal",
    tags=["terminal"],
)

logger = logging.getLogger("uvicorn")

@router.websocket("/ws/{profile_id}")
async def websocket_terminal(websocket: WebSocket, profile_id: int, db: Session = Depends(get_db)):
    await websocket.accept()
    
    profile = db.query(models.ServerProfile).filter(models.ServerProfile.id == profile_id).first()
    if not profile:
        await websocket.close(code=1008, reason="Profile not found")
        return

    logger.info(f"Starting terminal session for {profile.name} ({profile.ip_address})")
    
    ssh_service = SSHService(profile)
    
    try:
        # Establish SSH connection with PTY
        # We need to manually handle the connection here to keep it open for the session
        conn = await ssh_service._get_connection()
        
        async with conn:
            # Open a session with a PTY (pseudo-terminal)
            # request_pty='xterm' is crucial for terminal apps (vim, htop) to work
            # encoding='utf-8' ensures we send/recv strings, not bytes
            process = await conn.create_process(term_type='xterm', term_size=(80, 24), encoding='utf-8')
            
            async def forward_ssh_output():
                """Read from SSH stdout/stderr and send to WebSocket"""
                try:
                    while not process.stdout.at_eof():
                        data = await process.stdout.read(1024)
                        if data:
                            # xterm.js expects string or bytes. 
                            # asyncssh returns str if encoding is set, or bytes otherwise.
                            # We send text as is.
                            await websocket.send_text(data)
                except Exception as e:
                    logger.error(f"Error forwarding SSH output: {e}")

            async def forward_ws_input():
                """Read from WebSocket and send to SSH stdin"""
                try:
                    while True:
                        data = await websocket.receive_text()
                        
                        # Attempt to parse as JSON command (e.g. resize)
                        is_command = False
                        if data.strip().startswith('{'):
                            try:
                                cmd = json.loads(data)
                                if isinstance(cmd, dict) and 'cols' in cmd and 'rows' in cmd:
                                    process.set_terminal_size(cmd['cols'], cmd['rows'])
                                    is_command = True
                            except json.JSONDecodeError:
                                # Not valid JSON, treat as standard input (e.g. user typed '{')
                                pass
                        
                        if not is_command:
                            process.stdin.write(data)
                            # process.stdin.drain() # asyncssh docs say write is non-blocking/buffered
                            
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    process.terminate()
                except Exception as e:
                    logger.error(f"Error forwarding WS input: {e}")
                    process.terminate()

            # Run forwarding tasks concurrently
            output_task = asyncio.create_task(forward_ssh_output())
            input_task = asyncio.create_task(forward_ws_input())
            
            # Wait for the process to exit or tasks to fail
            await asyncio.wait([output_task, input_task], return_when=asyncio.FIRST_COMPLETED)
            
            # Cleanup
            output_task.cancel()
            input_task.cancel()
            
    except Exception as e:
        logger.error(f"SSH Session failed: {e}")
        await websocket.close(code=1011, reason=f"SSH Error: {str(e)}")
