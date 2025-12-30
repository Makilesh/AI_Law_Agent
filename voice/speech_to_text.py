"""
Speech-to-Text Module using RealtimeSTT
Efficient, modular implementation for real-time voice input
"""

import logging
from typing import Callable, Optional
from threading import Event

logger = logging.getLogger(__name__)

# Lazy import to avoid loading heavy dependencies at startup
_AudioToTextRecorder = None

def _get_recorder_class():
    """Lazy load RealtimeSTT to reduce startup time."""
    global _AudioToTextRecorder
    if _AudioToTextRecorder is None:
        try:
            from RealtimeSTT import AudioToTextRecorder
            _AudioToTextRecorder = AudioToTextRecorder
        except ImportError:
            logger.error("RealtimeSTT not installed. Run: pip install RealtimeSTT")
            raise
    return _AudioToTextRecorder


class SpeechToText:
    """
    Real-time Speech-to-Text wrapper using RealtimeSTT.
    Supports continuous listening with callbacks.
    """
    
    def __init__(
        self,
        model: str = "tiny.en",  # Whisper model: tiny.en, base.en, small.en
        language: str = "en",
        silero_sensitivity: float = 0.4,
        webrtc_sensitivity: int = 3,
        post_speech_silence_duration: float = 0.6,
        min_length_of_recording: float = 0.5,
        min_gap_between_recordings: float = 0.3,
    ):
        """
        Initialize STT with optimized settings for legal queries.
        
        Args:
            model: Whisper model size (tiny.en is fastest, small.en is most accurate)
            language: Target language code
            silero_sensitivity: Voice activity detection sensitivity (0-1)
            webrtc_sensitivity: WebRTC VAD sensitivity (0-3)
            post_speech_silence_duration: Silence duration to end recording
            min_length_of_recording: Minimum recording length in seconds
            min_gap_between_recordings: Gap between consecutive recordings
        """
        self.config = {
            "model": model,
            "language": language,
            "silero_sensitivity": silero_sensitivity,
            "webrtc_sensitivity": webrtc_sensitivity,
            "post_speech_silence_duration": post_speech_silence_duration,
            "min_length_of_recording": min_length_of_recording,
            "min_gap_between_recordings": min_gap_between_recordings,
        }
        self._recorder = None
        self._is_listening = False
        self._stop_event = Event()
        
    def _init_recorder(self, on_text: Optional[Callable[[str], None]] = None):
        """Initialize the recorder with current config."""
        RecorderClass = _get_recorder_class()
        
        recorder_config = {
            "model": self.config["model"],
            "language": self.config["language"],
            "silero_sensitivity": self.config["silero_sensitivity"],
            "webrtc_sensitivity": self.config["webrtc_sensitivity"],
            "post_speech_silence_duration": self.config["post_speech_silence_duration"],
            "min_length_of_recording": self.config["min_length_of_recording"],
            "min_gap_between_recordings": self.config["min_gap_between_recordings"],
            "spinner": False,  # Disable spinner for API use
            "enable_realtime_transcription": False,  # Final transcription only
        }
        
        if on_text:
            recorder_config["on_recording_stop"] = on_text
            
        self._recorder = RecorderClass(**recorder_config)
        
    def transcribe_once(self, timeout: float = 30.0) -> Optional[str]:
        """
        Listen for a single utterance and return transcription.
        
        Args:
            timeout: Maximum time to wait for speech in seconds
            
        Returns:
            Transcribed text or None if timeout/error
        """
        try:
            if not self._recorder:
                self._init_recorder()
                
            logger.info("Listening for speech...")
            text = self._recorder.text()
            
            if text and text.strip():
                logger.info(f"Transcribed: {text[:50]}...")
                return text.strip()
            return None
            
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None
            
    def start_continuous(self, on_text: Callable[[str], None]):
        """
        Start continuous listening with callback for each transcription.
        
        Args:
            on_text: Callback function receiving transcribed text
        """
        if self._is_listening:
            logger.warning("Already listening")
            return
            
        self._stop_event.clear()
        self._is_listening = True
        
        try:
            self._init_recorder(on_text)
            logger.info("Starting continuous STT...")
            
            while not self._stop_event.is_set():
                text = self._recorder.text()
                if text and text.strip() and on_text:
                    on_text(text.strip())
                    
        except Exception as e:
            logger.error(f"Continuous STT error: {e}")
        finally:
            self._is_listening = False
            
    def stop(self):
        """Stop continuous listening."""
        self._stop_event.set()
        self._is_listening = False
        if self._recorder:
            try:
                self._recorder.stop()
            except:
                pass
        logger.info("STT stopped")
        
    @property
    def is_listening(self) -> bool:
        """Check if currently listening."""
        return self._is_listening
        
    def __del__(self):
        """Cleanup on destruction."""
        self.stop()
