#!/usr/bin/env python3
"""
Preprocessor for RecordMod episode recordings (behavioral cloning).

Turns episode files into model-ready numpy arrays, and transforms single live frames
at inference time through the same feature code, using the saved vocabulary and scaler.

Usage:
    python preprocess.py recordings/*.bin --out data/gruz_mother
"""

from __future__ import annotations

import argparse
import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from protocol import (
    EXPECTED_MAGIC,
    ActionButtons,
    EpisodeHeader,
    EpisodeReader,
    EpisodeStatus,
    FrameDataHeader,
    FrameFlags,
    KnightFlags,
)

# Feature definitions, in output order. cont = standardized; frac and bin are left as is.
KNIGHT_FEATURES = [
    ("dist_left_wall", "cont"),
    ("dist_right_wall", "cont"),
    ("dist_floor", "cont"),
    ("knight_vx", "cont"),
    ("knight_vy", "cont"),
    ("nail_cooldown", "cont"),
    ("invuln_remaining", "cont"),
    ("shadow_dash_cooldown", "cont"),
    ("on_ground", "bin"),
    ("is_dashing", "bin"),
    ("can_dash", "bin"),
    ("can_double_jump", "bin"),
    ("is_recoiling", "bin"),
    ("knight_facing_boss", "bin"),
]
BOSS_FEATURES = [
    ("dx", "cont"),
    ("dy", "cont"),
    ("gap_x", "cont"),
    ("gap_y", "cont"),
    ("boss_vx", "cont"),
    ("boss_vy", "cont"),
    ("fsm_state_time", "cont"),
    ("boss_invulnerable", "bin"),
    ("boss_facing_knight", "bin"),
]
# Inputs for the PPO value function only. Never feed these to the policy.
CRITIC_EXTRA_FEATURES = [
    ("knight_hp_frac", "frac"),
    ("boss_hp_frac", "frac"),
]
FEATURES = {
    "obs_knight": KNIGHT_FEATURES,
    "obs_boss": BOSS_FEATURES,
    "obs_critic_extra": CRITIC_EXTRA_FEATURES,
}

# FrameDataHeader fields read by the features, labels and aux arrays.
FRAME_FIELDS = {
    "frame_id": np.int64,
    "knight_x": np.float32,
    "knight_y": np.float32,
    "knight_vx": np.float32,
    "knight_vy": np.float32,
    "nail_cooldown": np.float32,
    "shadow_dash_cooldown": np.float32,
    "invuln_remaining": np.float32,
    "boss_x": np.float32,
    "boss_y": np.float32,
    "boss_vx": np.float32,
    "boss_vy": np.float32,
    "boss_hp": np.int64,
    "fsm_state_time": np.float32,
    "boss_bound_width": np.float32,
    "boss_bound_height": np.float32,
    "knight_flags": np.int64,
    "boss_fsm_state": np.int64,
    "knight_hp": np.int64,
    "is_done": np.int64,
    "flags": np.int64,
    "action_pressed": np.int64,
    "action_held": np.int64,
}

STD_FLOOR = 1e-6

_KNIGHT = {name: i for i, (name, _) in enumerate(KNIGHT_FEATURES)}
_BOSS = {name: i for i, (name, _) in enumerate(BOSS_FEATURES)}
_LEFT = ActionButtons.LEFT.bit_length() - 1
_RIGHT = ActionButtons.RIGHT.bit_length() - 1


@dataclass
class PreprocessConfig:
    decision_interval: int = 4  # K ticks per decision step
    keep_outcomes: tuple[int, ...] = (EpisodeStatus.BOSS_DEFEATED,)  # Aborted is always dropped
    val_fraction: float = 0.2
    seed: int = 0
    mirror_augment: bool = True  # Assumes a left-right symmetric arena and boss behavior
    include_entities: bool = False  # TODO: entity features (obs_entities, entity_mask) are not implemented
    fsm_time_clip: float = 3.0  # TODO: placeholder, pick from the boss's FSM state durations


@dataclass
class RawEpisode:
    path: str
    header: EpisodeHeader
    frames: dict[str, np.ndarray]  # One column per FRAME_FIELDS entry, cut after the terminal frame
    outcome: int  # Final is_done; Aborted when the recording has no terminal frame


def _columns(frames: list[FrameDataHeader]) -> dict[str, np.ndarray]:
    return {
        name: np.array([getattr(f, name) for f in frames], dtype=dtype)
        for name, dtype in FRAME_FIELDS.items()
    }


def _bit(values: np.ndarray, flag: int) -> np.ndarray:
    return (values & int(flag)) != 0


def _buttons(values: np.ndarray) -> np.ndarray:
    """(T,) button bitmasks -> (T, 8) bool, column i = bit i (ActionButtons order)."""
    return np.unpackbits(values.astype(np.uint8)[:, None], axis=1, bitorder="little").astype(bool)


def _observe(
    cols: dict[str, np.ndarray], header: EpisodeHeader, boss_hp_max: int, fsm_time_clip: float
) -> dict[str, np.ndarray]:
    """Unscaled observations for every frame in cols. Shared by build_dataset and transform_frame."""
    kf = cols["knight_flags"]
    ff = cols["flags"]
    dx = cols["boss_x"] - cols["knight_x"]
    dy = cols["boss_y"] - cols["knight_y"]
    knight_right = _bit(ff, FrameFlags.KNIGHT_FACING_RIGHT)
    boss_right = _bit(ff, FrameFlags.BOSS_FACING_RIGHT)

    knight = [
        cols["knight_x"] - header.arena_min_x,
        header.arena_max_x - cols["knight_x"],
        cols["knight_y"] - header.arena_min_y,
        cols["knight_vx"],
        cols["knight_vy"],
        cols["nail_cooldown"],
        cols["invuln_remaining"],
        cols["shadow_dash_cooldown"],
        _bit(kf, KnightFlags.ON_GROUND),
        _bit(kf, KnightFlags.IS_DASHING),
        _bit(kf, KnightFlags.CAN_DASH),
        _bit(kf, KnightFlags.CAN_DOUBLE_JUMP),
        _bit(kf, KnightFlags.IS_RECOILING),
        (knight_right & (dx >= 0)) | (~knight_right & (dx <= 0)),
    ]
    boss = [
        dx,
        dy,
        np.abs(dx) - (header.knight_bound_width + cols["boss_bound_width"]),
        np.abs(dy) - (header.knight_bound_height + cols["boss_bound_height"]),
        cols["boss_vx"],
        cols["boss_vy"],
        np.minimum(cols["fsm_state_time"], fsm_time_clip),
        _bit(ff, FrameFlags.BOSS_INVULNERABLE),
        (boss_right & (dx <= 0)) | (~boss_right & (dx >= 0)),
    ]
    critic_extra = [
        cols["knight_hp"] / header.max_health,
        cols["boss_hp"] / boss_hp_max,
    ]
    return {
        "obs_knight": np.stack(knight, axis=1).astype(np.float32),
        "obs_boss": np.stack(boss, axis=1).astype(np.float32),
        "obs_critic_extra": np.stack(critic_extra, axis=1).astype(np.float32),
    }


def _mirror(steps: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Horizontally mirrored copy of unscaled step arrays (episode_id is left to the caller)."""
    mirrored = dict(steps)

    knight = steps["obs_knight"].copy()
    left, right = _KNIGHT["dist_left_wall"], _KNIGHT["dist_right_wall"]
    knight[:, [left, right]] = knight[:, [right, left]]
    knight[:, _KNIGHT["knight_vx"]] *= -1
    mirrored["obs_knight"] = knight

    boss = steps["obs_boss"].copy()
    boss[:, [_BOSS["dx"], _BOSS["boss_vx"]]] *= -1
    mirrored["obs_boss"] = boss

    for key in ("label_pressed", "label_held_frac"):
        labels = steps[key].copy()
        labels[:, [_LEFT, _RIGHT]] = labels[:, [_RIGHT, _LEFT]]
        mirrored[key] = labels

    return mirrored


def _concat(parts: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    if not parts:
        return {}
    return {key: np.concatenate([p[key] for p in parts]) for key in parts[0]}


class Preprocessor:
    def __init__(self, config: PreprocessConfig):
        if config.include_entities:
            raise NotImplementedError("include_entities: entity features are not implemented yet")
        self.config = config
        self.boss_id: int | None = None
        self.fsm_vocab = np.zeros(0, dtype=np.int64)  # Sorted raw boss_fsm_state values; index i -> i + 1
        self.scaler: dict[str, tuple[np.ndarray, np.ndarray]] = {}  # key -> (mean, std); identity for frac/bin
        self._episode: tuple[EpisodeHeader, int] | None = None  # Live episode: (header, boss_hp_max)

    # =========================================================================
    # Parsing
    # =========================================================================

    def load_episode(self, path) -> RawEpisode | None:
        """Parses one recording. Returns None (with a warning) when the file is unusable."""
        header, frames = EpisodeReader.read_file(str(path))
        if not frames:
            warnings.warn(f"{path}: no frames, file dropped")
            return None

        cols = _columns([frame.header for frame in frames])

        gaps = np.flatnonzero(np.diff(cols["frame_id"]) != 1)
        if gaps.size:
            warnings.warn(f"{path}: frame_id gap after frame {cols['frame_id'][gaps[0]]}, file dropped")
            return None

        done = np.flatnonzero(cols["is_done"] != EpisodeStatus.IN_PROGRESS)
        if done.size == 0:
            return RawEpisode(str(path), header, cols, EpisodeStatus.ABORTED)

        end = done[0] + 1
        if end < len(frames):
            warnings.warn(f"{path}: dropped {len(frames) - end} frames after the terminal frame")
            cols = {name: column[:end] for name, column in cols.items()}
        return RawEpisode(str(path), header, cols, int(cols["is_done"][-1]))

    # =========================================================================
    # Dataset
    # =========================================================================

    def build_dataset(self, paths) -> tuple[dict, dict]:
        """Returns (train, val) dicts of arrays and fits the vocabulary and scaler on train."""
        cfg = self.config

        # 1. Parse and filter
        episodes = [ep for p in sorted(map(str, paths)) if (ep := self.load_episode(p)) is not None]
        boss_ids = {ep.header.boss_id for ep in episodes}
        assert len(boss_ids) == 1, f"Expected recordings of a single boss, got boss ids {sorted(boss_ids)}"
        self.boss_id = boss_ids.pop()
        episodes = [
            ep for ep in episodes
            if ep.outcome != EpisodeStatus.ABORTED and ep.outcome in cfg.keep_outcomes
        ]
        assert episodes, "No episodes left after filtering"

        # 2. Split by episode
        order = np.random.default_rng(cfg.seed).permutation(len(episodes))
        n_val = int(round(len(episodes) * cfg.val_fraction))
        val_ids = sorted(order[:n_val].tolist())
        train_ids = sorted(order[n_val:].tolist())

        # 3. FSM vocabulary from train. A zero low byte is the mod's unknown state and stays at index 0.
        states = np.unique(np.concatenate([episodes[i].frames["boss_fsm_state"] for i in train_ids]))
        self.fsm_vocab = states[(states & 0xFF) != 0]

        # 4. Unscaled features, labels and aux values
        train_parts = [self._episode_steps(episodes[i], i) for i in train_ids]
        val_parts = [self._episode_steps(episodes[i], i) for i in val_ids]

        # 5. Mirror-augment train
        if cfg.mirror_augment:
            mirrored = []
            for part in train_parts:
                m = _mirror(part)
                m["episode_id"] = part["episode_id"] + len(episodes)
                mirrored.append(m)
            train_parts += mirrored

        train, val = _concat(train_parts), _concat(val_parts)

        # 6. Fit the scaler on the cont columns of the augmented train set
        for key in ("obs_knight", "obs_boss"):
            cont = np.array([kind == "cont" for _, kind in FEATURES[key]])
            # float64, so the scaler survives the JSON round trip bit-exactly
            mean = np.where(cont, train[key].mean(axis=0, dtype=np.float64), 0.0)
            std = np.where(cont, np.maximum(train[key].std(axis=0, dtype=np.float64), STD_FLOOR), 1.0)
            self.scaler[key] = (mean, std)

        # 7. Standardize both splits
        for split in (train, val):
            split.update(self._scale(split))

        return train, val

    def _episode_steps(self, ep: RawEpisode, episode_id: int) -> dict[str, np.ndarray]:
        """Unscaled step arrays of one episode: windows [t, t+K) starting at the first frame."""
        cols = ep.frames
        n = len(cols["frame_id"])
        k = self.config.decision_interval

        starts = np.arange(0, n, k)
        if n - starts[-1] < k and cols["is_done"][-1] == EpisodeStatus.IN_PROGRESS:
            starts = starts[:-1]  # Partial final window without the terminal frame
        ends = np.minimum(starts + k, n)
        window = slice(0, ends[-1])

        step_cols = {name: column[starts] for name, column in cols.items()}
        steps = _observe(step_cols, ep.header, int(cols["boss_hp"][0]), self.config.fsm_time_clip)
        steps["fsm_idx"] = self._fsm_index(step_cols["boss_fsm_state"])

        steps["label_pressed"] = np.logical_or.reduceat(_buttons(cols["action_pressed"][window]), starts)
        held = np.add.reduceat(_buttons(cols["action_held"][window]).astype(np.float32), starts)
        steps["label_held_frac"] = held / (ends - starts)[:, None].astype(np.float32)

        flags = cols["flags"][window]
        steps["boss_hit_any"] = np.logical_or.reduceat(_bit(flags, FrameFlags.BOSS_HIT), starts)
        steps["knight_hit_any"] = np.logical_or.reduceat(_bit(flags, FrameFlags.KNIGHT_HIT), starts)

        nxt = np.append(starts[1:], n - 1)  # The last step uses the episode's final frame
        steps["boss_hp_delta"] = cols["boss_hp"][nxt] - cols["boss_hp"][starts]
        steps["knight_hp_delta"] = cols["knight_hp"][nxt] - cols["knight_hp"][starts]

        n_steps = len(starts)
        steps["episode_id"] = np.full(n_steps, episode_id, dtype=np.int64)
        steps["step"] = np.arange(n_steps, dtype=np.int64)
        steps["is_last"] = steps["step"] == n_steps - 1
        steps["episode_outcome"] = np.full(n_steps, ep.outcome, dtype=np.uint8)
        return steps

    def _fsm_index(self, raw: np.ndarray) -> np.ndarray:
        """Raw boss_fsm_state -> vocabulary index (1..N), 0 for values unseen in train."""
        idx = np.searchsorted(self.fsm_vocab, raw) + 1
        return np.where(np.isin(raw, self.fsm_vocab), idx, 0).astype(np.int64)

    def _scale(self, obs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        return {
            key: ((obs[key] - mean) / std).astype(np.float32)
            for key, (mean, std) in self.scaler.items()
            if key in obs
        }

    # =========================================================================
    # Inference
    # =========================================================================

    def start_episode(self, header: EpisodeHeader, first_frame: FrameDataHeader) -> None:
        assert header.boss_id == self.boss_id, (
            f"Preprocessor was fitted on boss {self.boss_id}, episode is boss {header.boss_id}"
        )
        self._episode = (header, first_frame.boss_hp)

    def transform_frame(self, frame: FrameDataHeader) -> dict:
        """One decision step: obs_knight, obs_boss, obs_critic_extra and fsm_idx."""
        assert self._episode is not None, "Call start_episode first"
        header, boss_hp_max = self._episode

        cols = _columns([frame])
        obs = _observe(cols, header, boss_hp_max, self.config.fsm_time_clip)
        obs.update(self._scale(obs))
        obs["fsm_idx"] = self._fsm_index(cols["boss_fsm_state"])
        return {key: value[0] for key, value in obs.items()}

    # =========================================================================
    # Artifacts
    # =========================================================================

    def save(self, path) -> None:
        artifacts = {
            "magic": EXPECTED_MAGIC,
            "config": asdict(self.config),
            "boss_id": self.boss_id,
            "fsm_vocab": self.fsm_vocab.tolist(),
            "scaler": {
                key: {"mean": mean.tolist(), "std": std.tolist()}
                for key, (mean, std) in self.scaler.items()
            },
            "features": {key: [name for name, _ in features] for key, features in FEATURES.items()},
        }
        Path(path).write_text(json.dumps(artifacts, indent=2))

    @classmethod
    def load(cls, path) -> Preprocessor:
        artifacts = json.loads(Path(path).read_text())
        assert artifacts["magic"] == EXPECTED_MAGIC, (
            f"Artifacts were fitted on format 0x{artifacts['magic']:X}, reader expects 0x{EXPECTED_MAGIC:X}"
        )
        config = PreprocessConfig(**artifacts["config"])
        config.keep_outcomes = tuple(config.keep_outcomes)

        pre = cls(config)
        pre.boss_id = artifacts["boss_id"]
        pre.fsm_vocab = np.array(artifacts["fsm_vocab"], dtype=np.int64)
        pre.scaler = {
            key: (np.array(s["mean"], dtype=np.float64), np.array(s["std"], dtype=np.float64))
            for key, s in artifacts["scaler"].items()
        }
        return pre


def main():
    parser = argparse.ArgumentParser(description="Build BC train/val arrays from RecordMod recordings.")
    parser.add_argument("recordings", nargs="+", type=Path, help="Episode .bin files")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()

    pre = Preprocessor(PreprocessConfig())
    train, val = pre.build_dataset(args.recordings)

    args.out.mkdir(parents=True, exist_ok=True)
    np.savez(args.out / "train.npz", **train)
    np.savez(args.out / "val.npz", **val)
    pre.save(args.out / "preprocessor.json")
    print(f"train: {len(train['step'])} steps, val: {len(val.get('step', []))} steps -> {args.out}")


if __name__ == "__main__":
    main()
