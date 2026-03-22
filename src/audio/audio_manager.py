from __future__ import annotations

from pathlib import Path
import random

import pygame


class AudioManager:
    """Centralized music and SFX manager backed by pygame.mixer."""

    music_extensions = (".mp3", ".ogg", ".wav")
    sfx_extensions = (".wav", ".ogg", ".mp3")
    movement_sfx_variants: dict[str, tuple[str, ...]] = {
        "walk": ("walk_1", "walk_2", "walk_3", "walk_4"),
        "jump": ("jump_1",),
        "dash": ("dash_1", "dash_2"),
        "land": ("land_1", "land_2"),
    }
    combat_attack_sfx_variants: dict[str, tuple[str, ...]] = {
        "sword": ("sword_swing_1", "sword_swing_2"),
        "hammer": ("hammer_swing_1", "hammer_swing_2"),
        "bow": ("bow_draw_1", "bow_draw_2"),
    }
    combat_hit_sfx_variants: dict[str, tuple[str, ...]] = {
        "sword": ("hit_1", "hit_2", "hit_3", "hit_4"),
        "hammer": ("hammer_hit_1", "hammer_hit_2"),
        "bow": ("bow_hit_1", "bow_hit_2"),
    }
    combat_combo_sfx_variants: tuple[str, ...] = ("combo_hit_1",)
    combat_ko_sfx_variants: tuple[str, ...] = ("KO_1", "KO_2", "KO_3", "KO_4", "KO_5")
    movement_opponent_volume_scale = 0.6

    def __init__(
        self,
        music_dir: Path | None = None,
        sfx_dir: Path | None = None,
        music_volume: float = 0.6,
        sfx_volume: float = 0.8,
    ) -> None:
        project_root = Path(__file__).resolve().parents[2]
        self.music_dir = music_dir or (project_root / "assets" / "audio" / "music")
        self.sfx_dir = sfx_dir or (project_root / "assets" / "audio" / "sfx")

        self._music_volume = self._clamp(music_volume)
        self._sfx_volume = self._clamp(sfx_volume)
        self._music_muted = False
        self._sfx_muted = False

        self._initialized = False
        self._preloaded = False
        self._enabled = True

        self._music_tracks: dict[str, Path] = {}
        self._sfx_sounds: dict[str, pygame.mixer.Sound] = {}
        self._current_music_track: str | None = None
        self._warned_missing_music: set[str] = set()
        self._warned_missing_sfx: set[str] = set()

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            pygame.mixer.music.set_volume(self._music_volume)
        except pygame.error as exc:
            self._enabled = False
            print(f"[audio] mixer init failed, audio disabled: {exc}")

    def preload(self) -> None:
        if self._preloaded:
            return
        self._preloaded = True

        if not self._enabled:
            return

        self._music_tracks = self._discover_files(self.music_dir, self.music_extensions)

        for key, path in self._discover_files(
            self.sfx_dir, self.sfx_extensions, recursive=True
        ).items():
            try:
                sound = pygame.mixer.Sound(str(path))
                sound.set_volume(self._sfx_volume)
                self._sfx_sounds[key] = sound
            except pygame.error as exc:
                print(f"[audio] failed to preload sfx '{path.name}': {exc}")

    def play_music(self, track: str, loops: int = -1, fade_ms: int = 400) -> bool:
        if not self._enabled or self._music_muted:
            return False
        if not self._initialized:
            self.initialize()
        if not self._preloaded:
            self.preload()

        music_path = self._music_tracks.get(track)
        if music_path is None:
            if track not in self._warned_missing_music:
                print(f"[audio] unknown music track: {track}")
                self._warned_missing_music.add(track)
            return False

        # Avoid unnecessary reload/restart of the same currently playing track.
        if self._current_music_track == track and pygame.mixer.music.get_busy():
            return True

        try:
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(self._music_volume)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self._current_music_track = track
            return True
        except pygame.error as exc:
            print(f"[audio] failed to play music '{track}': {exc}")
            return False

    def stop_music(self, fade_ms: int = 300) -> None:
        if not self._enabled:
            return
        if not self._initialized:
            self.initialize()
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()
        self._current_music_track = None

    def set_music_volume(self, volume: float) -> None:
        self._music_volume = self._clamp(volume)
        if not self._enabled or self._music_muted:
            return
        if not self._initialized:
            self.initialize()
        pygame.mixer.music.set_volume(self._music_volume)

    def play_sfx(self, name: str, volume: float | None = None, fallback: str | None = None) -> bool:
        if not self._enabled or self._sfx_muted:
            return False
        if not self._initialized:
            self.initialize()
        if not self._preloaded:
            self.preload()

        sound = self._sfx_sounds.get(name)
        if sound is None:
            if fallback:
                return self.play_sfx(fallback, volume)
            if name not in self._warned_missing_sfx:
                print(f"[audio] unknown sfx: {name}")
                self._warned_missing_sfx.add(name)
            return False

        target_volume = self._sfx_volume if volume is None else self._clamp(volume)
        channel = sound.play()
        if channel is None:
            return False
        channel.set_volume(target_volume)
        return True

    def play_movement_sfx(self, event: str, opponent: bool = False) -> bool:
        """Play a movement SFX event using preloaded sounds only."""
        keys = self.movement_sfx_variants.get(event)
        if not keys:
            return False
        volume_scale = self.movement_opponent_volume_scale if opponent else 1.0
        return self._play_variant_sfx(keys, volume_scale=volume_scale)

    def play_combat_attack_sfx(self, weapon_name: str, opponent: bool = False) -> bool:
        weapon_key = weapon_name.lower().strip()
        keys = self.combat_attack_sfx_variants.get(weapon_key)
        if not keys:
            return False
        volume_scale = self.movement_opponent_volume_scale if opponent else 1.0
        return self._play_variant_sfx(keys, volume_scale=volume_scale)

    def play_combat_hit_sfx(self, weapon_name: str) -> bool:
        weapon_key = weapon_name.lower().strip()
        keys = self.combat_hit_sfx_variants.get(weapon_key)
        if not keys:
            return False
        return self._play_variant_sfx(keys)

    def play_ko_sfx(self) -> bool:
        return self._play_variant_sfx(self.combat_ko_sfx_variants)

    def play_combo_sfx(self) -> bool:
        return self._play_variant_sfx(self.combat_combo_sfx_variants)

    def _play_variant_sfx(self, keys: tuple[str, ...], volume_scale: float = 1.0) -> bool:
        if not self._enabled or self._sfx_muted:
            return False
        if not self._initialized:
            self.initialize()
        if not self._preloaded:
            self.preload()

        # Pick one candidate and then fall back to the others if it's missing.
        choices = list(keys)
        if len(choices) > 1:
            first = random.choice(choices)
            choices.remove(first)
            choices.insert(0, first)

        sound: pygame.mixer.Sound | None = None
        for key in choices:
            sound = self._sfx_sounds.get(key)
            if sound is not None:
                break
        if sound is None:
            return False

        channel = sound.play()
        if channel is None:
            return False

        channel.set_volume(self._clamp(self._sfx_volume * volume_scale))
        return True

    def set_sfx_volume(self, volume: float) -> None:
        self._sfx_volume = self._clamp(volume)
        for sound in self._sfx_sounds.values():
            sound.set_volume(self._sfx_volume)

    def mute_music(self, muted: bool) -> None:
        self._music_muted = muted
        if not self._enabled:
            return
        if not self._initialized:
            self.initialize()
        pygame.mixer.music.set_volume(0.0 if muted else self._music_volume)

    def mute_sfx(self, muted: bool) -> None:
        self._sfx_muted = muted

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _discover_files(
        self, root: Path, extensions: tuple[str, ...], recursive: bool = False
    ) -> dict[str, Path]:
        files: dict[str, Path] = {}
        if not root.exists():
            return files

        paths = root.rglob("*") if recursive else root.iterdir()
        for path in sorted(paths):
            if not path.is_file():
                continue
            if path.suffix.lower() not in extensions:
                continue
            files[path.stem] = path
        return files
