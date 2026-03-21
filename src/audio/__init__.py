from .audio_manager import AudioManager

_shared_audio_manager: AudioManager | None = None


def get_shared_audio_manager() -> AudioManager:
    global _shared_audio_manager
    if _shared_audio_manager is None:
        _shared_audio_manager = AudioManager()
    return _shared_audio_manager


__all__ = ["AudioManager", "get_shared_audio_manager"]
