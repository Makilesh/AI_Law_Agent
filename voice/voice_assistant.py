"""
Voice Assistant Module - WebSocket endpoint for real-time voice chat
Integrates STT, TTS with the Legal AI chat endpoint
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class VoiceMessage:
    """Voice message structure for WebSocket communication."""
    type: str  # "transcript", "response", "error", "status"
    content: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))


class VoiceAssistant:
    """
    Voice Assistant for Legal AI Engine.
    Handles WebSocket connections for real-time voice I/O.
    """
    
    def __init__(self, chat_handler=None):
        """
        Initialize Voice Assistant.
        
        Args:
            chat_handler: Async function to process chat queries
                         Signature: async def handler(query: str, language: str) -> dict
        """
        self.chat_handler = chat_handler
        self._stt = None
        self._tts = None
        self._active_sessions: Dict[str, dict] = {}
        
    def _get_stt(self):
        """Lazy load STT."""
        if self._stt is None:
            from .speech_to_text import SpeechToText
            self._stt = SpeechToText(model="tiny.en")
        return self._stt
        
    def _get_tts(self):
        """Lazy load TTS."""
        if self._tts is None:
            from .text_to_speech import TextToSpeech
            self._tts = TextToSpeech(engine="system")
        return self._tts
        
    async def handle_websocket(self, websocket, session_id: str = "default"):
        """
        Handle WebSocket connection for voice chat.
        
        Protocol:
        - Client sends: {"type": "start_listening"} to begin STT
        - Client sends: {"type": "stop_listening"} to stop STT
        - Client sends: {"type": "text", "content": "query"} for text input
        - Server sends: {"type": "transcript", "content": "..."} for STT result
        - Server sends: {"type": "response", "content": "...", "metadata": {...}}
        - Server sends: {"type": "status", "content": "listening|processing|speaking"}
        - Server sends: {"type": "error", "content": "error message"}
        """
        self._active_sessions[session_id] = {"websocket": websocket, "listening": False}
        
        try:
            await self._send_status(websocket, "connected")
            
            # Handle FastAPI WebSocket - use receive_text() in a loop
            while True:
                try:
                    message = await websocket.receive_text()
                    await self._process_message(websocket, message, session_id)
                except Exception as e:
                    # Check if it's a disconnect
                    if "disconnect" in str(e).lower() or "closed" in str(e).lower():
                        break
                    raise
                
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self._send_error(websocket, str(e))
        finally:
            self._active_sessions.pop(session_id, None)
            
    async def _process_message(self, websocket, message: str, session_id: str):
        """Process incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            
            if msg_type == "start_listening":
                await self._start_listening(websocket, session_id)
                
            elif msg_type == "stop_listening":
                await self._stop_listening(session_id)
                
            elif msg_type == "text":
                content = data.get("content", "")
                language = data.get("language", "English")
                if content:
                    await self._process_query(websocket, content, language)
                    
            elif msg_type == "speak":
                content = data.get("content", "")
                if content:
                    await self._speak_text(websocket, content)
                    
            elif msg_type == "stop_speaking":
                self._get_tts().stop()
                
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON message")
        except Exception as e:
            await self._send_error(websocket, str(e))
            
    async def _start_listening(self, websocket, session_id: str):
        """Start STT listening."""
        session = self._active_sessions.get(session_id)
        if not session or session.get("listening"):
            return
            
        session["listening"] = True
        await self._send_status(websocket, "listening")
        
        # Run STT in thread to not block
        loop = asyncio.get_event_loop()
        
        def on_transcript(text):
            asyncio.run_coroutine_threadsafe(
                self._on_transcript(websocket, text, session_id),
                loop
            )
            
        await loop.run_in_executor(
            None,
            lambda: self._listen_once(on_transcript, session_id)
        )
        
    def _listen_once(self, callback, session_id: str):
        """Listen for one utterance."""
        try:
            stt = self._get_stt()
            text = stt.transcribe_once(timeout=30)
            if text:
                callback(text)
        except Exception as e:
            logger.error(f"STT listen error: {e}")
        finally:
            session = self._active_sessions.get(session_id)
            if session:
                session["listening"] = False
                
    async def _on_transcript(self, websocket, text: str, session_id: str):
        """Handle STT transcript."""
        await websocket.send_text(VoiceMessage(
            type="transcript",
            content=text
        ).to_json())
        
        # Auto-process the query
        await self._process_query(websocket, text, "English")
        
    async def _stop_listening(self, session_id: str):
        """Stop STT listening."""
        session = self._active_sessions.get(session_id)
        if session:
            session["listening"] = False
        self._get_stt().stop()
        
    async def _process_query(self, websocket, query: str, language: str):
        """Process text query through chat handler."""
        await self._send_status(websocket, "processing")
        
        try:
            if self.chat_handler:
                result = await self.chat_handler(query, language)
                response_text = result.get("response", "I couldn't process that query.")
                
                await websocket.send_text(VoiceMessage(
                    type="response",
                    content=response_text,
                    metadata={
                        "confidence": result.get("confidence"),
                        "source": result.get("source"),
                    }
                ).to_json())
                
                # Auto-speak response
                await self._speak_text(websocket, response_text)
            else:
                await self._send_error(websocket, "Chat handler not configured")
                
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            await self._send_error(websocket, f"Error processing query: {str(e)}")
            
    async def _speak_text(self, websocket, text: str):
        """Speak text using TTS."""
        await self._send_status(websocket, "speaking")
        
        try:
            tts = self._get_tts()
            loop = asyncio.get_event_loop()
            
            # Speak with blocking to ensure completion
            await loop.run_in_executor(None, lambda: tts.speak(text, block=True))
            
            # Add small delay to ensure audio finishes playing
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            await self._send_status(websocket, "ready")
            
    async def _send_status(self, websocket, status: str):
        """Send status update."""
        try:
            await websocket.send_text(VoiceMessage(
                type="status",
                content=status
            ).to_json())
        except Exception:
            pass  # Ignore send errors on closed connections
        
    async def _send_error(self, websocket, error: str):
        """Send error message."""
        try:
            await websocket.send_text(VoiceMessage(
                type="error",
                content=error
            ).to_json())
        except Exception:
            pass  # Ignore send errors on closed connections
        
    def cleanup(self):
        """Cleanup resources."""
        if self._stt:
            self._stt.stop()
        if self._tts:
            self._tts.stop()


# Standalone WebSocket server for testing
async def run_voice_server(host: str = "localhost", port: int = 8001, chat_handler=None):
    """
    Run standalone WebSocket server for voice assistant.
    
    Args:
        host: Server host
        port: Server port
        chat_handler: Chat processing function
    """
    try:
        import websockets
    except ImportError:
        logger.error("websockets not installed. Run: pip install websockets")
        return
        
    assistant = VoiceAssistant(chat_handler=chat_handler)
    
    async def handler(websocket, path):
        session_id = str(id(websocket))
        await assistant.handle_websocket(websocket, session_id)
        
    logger.info(f"Starting Voice WebSocket server on ws://{host}:{port}")
    
    async with websockets.serve(handler, host, port):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    # Test with mock handler
    async def mock_handler(query: str, language: str) -> dict:
        return {
            "response": f"You asked about: {query}",
            "confidence": 0.9,
            "source": "mock"
        }
        
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_voice_server(chat_handler=mock_handler))
