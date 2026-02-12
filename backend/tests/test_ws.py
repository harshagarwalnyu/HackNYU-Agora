import asyncio
import socketio

# Create client
sio = socketio.AsyncClient(logger=True, engineio_logger=True)

@sio.event
async def connect() -> None:
    print("Connected to server")
    
@sio.event
async def disconnect() -> None:
    print("Disconnected from server")

from typing import Dict, Any

@sio.event
async def session_initialized(data: Dict[str, Any]) -> None:
    print(f"Session initialized: {data}")
    # Send a text message
    await sio.emit('text_input', {'text': 'Explain quantum physics in simple terms.'})

@sio.event
async def transcript(data: Dict[str, Any]) -> None:
    print(f"Received transcript: {data}")

@sio.event
async def session_status(data: Dict[str, Any]) -> None:
    print(f"Session status: {data}")
    if data.get('status') == 'interrupted':
        print("SUCCESS: Interruption confirmed.")
        await sio.disconnect()

async def main() -> None:
    try:
        await sio.connect('http://localhost:8000')
        
        # Init session
        await sio.emit('init_session', {'user_id': 'debug_user', 'course_id': 'debug_course'})
        
        # Wait a bit then interrupt
        await asyncio.sleep(2)
        print("Sending interrupt signal...")
        await sio.emit('interrupt', {})
        
        # Wait for disconnection or timeout
        await sio.wait()
        
    except Exception as e:
        print(f"Error: {e}")
        if sio.connected:
            await sio.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
