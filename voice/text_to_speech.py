"""
Text-to-Speech Module using RealtimeTTS
Efficient, modular implementation for real-time voice output
"""

import logging
import asyncio
from typing import Optional, AsyncGenerator
from queue import Queue
from threading import Thread

logger = logging.getLogger(__name__)

# Lazy imports
_TextToAudioStream = None
_engines = {}

def _get_tts_class():
    """Lazy load RealtimeTTS."""
    global _TextToAudioStream
    if _TextToAudioStream is None:
        try:
            from RealtimeTTS import TextToAudioStream
            _TextToAudioStream = TextToAudioStream
        except ImportError:
            logger.error("RealtimeTTS not installed. Run: pip install RealtimeTTS")
            raise
    return _TextToAudioStream


def _get_engine(engine_type: str = "system"):
    """Get or create TTS engine (cached)."""
    global _engines
    
    if engine_type not in _engines:
        try:
            if engine_type == "system":
                from RealtimeTTS import SystemEngine
                _engines[engine_type] = SystemEngine()
            elif engine_type == "pyttsx3":
                from RealtimeTTS import PyttxEngine
                _engines[engine_type] = PyttxEngine()
            elif engine_type == "azure":
                from RealtimeTTS import AzureEngine
                _engines[engine_type] = AzureEngine()
            elif engine_type == "elevenlabs":
                from RealtimeTTS import ElevenlabsEngine
                _engines[engine_type] = ElevenlabsEngine()
            else:
                # Default to system
                from RealtimeTTS import SystemEngine
                _engines[engine_type] = SystemEngine()
        except ImportError as e:
            logger.warning(f"Engine {engine_type} not available: {e}, using system")
            from RealtimeTTS import SystemEngine
            _engines[engine_type] = SystemEngine()
            
    return _engines[engine_type]


class TextToSpeech:
    """
    Real-time Text-to-Speech wrapper using RealtimeTTS.
    Supports streaming text and async generation.
    """
    
    def __init__(
        self,
        engine: str = "system",  # system, pyttsx3, azure, elevenlabs
        rate: float = 1.0,
        volume: float = 1.0,
    ):
        """
        Initialize TTS with specified engine.
        
        Args:
            engine: TTS engine to use (system is most compatible)
            rate: Speech rate multiplier
            volume: Volume level (0.0-1.0)
        """
        self.engine_type = engine
        self.rate = rate
        self.volume = volume
        self._stream = None
        self._is_speaking = False
        
    def _init_stream(self):
        """Initialize TTS stream."""
        if self._stream is None:
            StreamClass = _get_tts_class()
            engine = _get_engine(self.engine_type)
            self._stream = StreamClass(engine)
            
    def speak(self, text: str, block: bool = True):
        """
        Speak text immediately.
        
        Args:
            text: Text to speak
            block: Wait for speech to complete
        """
        if not text or not text.strip():
            return
            
        try:
            self._init_stream()
            self._is_speaking = True
            
            logger.info(f"Speaking: {text[:50]}...")
            self._stream.feed(text)
            
            if block:
                self._stream.play()
            else:
                self._stream.play_async()
                
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            if block:
                self._is_speaking = False
                
    def speak_stream(self, text_generator):
        """
        Speak text as it streams in (for LLM responses).
        
        Args:
            text_generator: Generator yielding text chunks
        """
        try:
            self._init_stream()
            self._is_speaking = True
            
            for chunk in text_generator:
                if chunk:
                    self._stream.feed(chunk)
                    
            self._stream.play()
            
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
        self._is_speaking = False
        if self._stream:
            try:
                self._stream.stop()
            except:
                pass
        logger.info("TTS stopped")
        
    @property
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking
        
    def __del__(self):
        """Cleanup on destruction."""
        self.stop()


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
        self._thread = Thread(target=self._process_queue, daemon=True)
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
        """Stop the queue processor."""
        self._running = False
        self.tts.stop()
