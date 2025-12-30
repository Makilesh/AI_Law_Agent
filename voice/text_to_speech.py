"""
Text-to-Speech Module using pyttsx3
Creates fresh engine for each call to avoid event loop issues
"""

import logging
import asyncio
import threading
from typing import Optional
from queue import Queue

logger = logging.getLogger(__name__)

# Global lock to prevent concurrent TTS access
_tts_lock = threading.Lock()


class TextToSpeech:
    """
    Text-to-Speech using pyttsx3.
    Creates fresh engine for each speech to avoid state issues.
    """
    
    def __init__(
        self,
        engine: str = "system",
        rate: int = 150,
        volume: float = 1.0,
    ):
        """
        Initialize TTS.
        
        Args:
            engine: Engine type (uses pyttsx3)
            rate: Speech rate (words per minute)
            volume: Volume level (0.0-1.0)
        """
        self.engine_type = engine
        self.rate = rate
        self.volume = volume
        self._is_speaking = False
        self._stop_requested = False
        
    def speak(self, text: str, block: bool = True):
        """
        Speak text immediately.
        
        Args:
            text: Text to speak
            block: Wait for speech to complete
        """
        if not text or not text.strip():
            return
            
        self._stop_requested = False
        self._is_speaking = True
        
        try:
            with _tts_lock:
                import pyttsx3
                
                # Create completely fresh engine each time
                engine = pyttsx3.init()
                engine.setProperty('rate', self.rate)
                engine.setProperty('volume', self.volume)
                
                # Limit text length for very long responses
                if len(text) > 1500:
                    text = text[:1500] + "... Response truncated for audio."
                
                logger.info(f"Speaking: {text[:50]}...")
                engine.say(text)
                engine.runAndWait()
                
                # Cleanup engine to avoid event loop issues
                try:
                    engine.stop()
                except:
                    pass
                del engine
                    
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            self._is_speaking = False
                
    def speak_stream(self, text_generator):
        """
        Speak text as it streams in.
        
        Args:
            text_generator: Generator yielding text chunks
        """
        try:
            # Collect all chunks first
            full_text = ""
            for chunk in text_generator:
                if chunk and not self._stop_requested:
                    full_text += chunk
                    
            # Speak collected text
            self.speak(full_text, block=True)
                
        except Exception as e:
            logger.error(f"Stream TTS error: {e}")
        finally:
            self._is_speaking = False
            
    async def speak_async(self, text: str):
        """
        Speak text asynchronously.
        
        Args:
            text: Text to speak
        """
        if not text or not text.strip():
            return
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self.speak(text, block=True))
        
    def stop(self):
        """Stop current speech."""
        self._stop_requested = True
        self._is_speaking = False
        logger.info("TTS stopped")
        
    @property
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking
        
    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.stop()
        except:
            pass


class AsyncTTSQueue:
    """
    Async queue for TTS with priority support.
    Useful for handling multiple responses.
    """
    
    def __init__(self, tts: Optional[TextToSpeech] = None):
        self.tts = tts or TextToSpeech()
        self._queue = Queue()
        self._running = False
        self._thread = None
        
    def start(self):
        """Start the TTS queue processor."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
        
    def _process_queue(self):
        """Process queued speech requests."""
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                if text:
                    self.tts.speak(text, block=True)
            except:
                continue
                
    def enqueue(self, text: str):
        """Add text to speech queue."""
        if text and text.strip():
            self._queue.put(text)
            
    def stop(self):
        """Stop queue processor."""
        self._running = False
        self.tts.stop()
        if self._thread:
            self._thread.join(timeout=1)
