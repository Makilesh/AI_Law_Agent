"""
Voice I/O Package for AI Legal Engine
Phase 5: Real-time Speech-to-Text and Text-to-Speech

Libraries: RealtimeSTT, RealtimeTTS, PyAudio, WebSockets
"""

from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from .voice_assistant import VoiceAssistant

__all__ = ["SpeechToText", "TextToSpeech", "VoiceAssistant"]
