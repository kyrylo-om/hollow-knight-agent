"""
Binary protocol definition matching Hollow Knight telemetry structs.
All binary structures use little-endian byte ordering (<) with Pack = 1.
"""

from __future__ import annotations

import struct
import warnings
from collections.abc import Iterator
from dataclasses import dataclass
from enum import IntEnum, IntFlag


# Enums and Flags
class ActionButtons(IntFlag):
    NONE = 0
    JUMP = 1 << 0
    ATTACK = 1 << 1
    DASH = 1 << 2
    CAST_FOCUS = 1 << 3
    LEFT = 1 << 4
    RIGHT = 1 << 5
    UP = 1 << 6
    DOWN = 1 << 7


class KnightFlags(IntFlag):
    NONE = 0
    ON_GROUND = 1 << 0
    TOUCHING_WALL = 1 << 1
    WALL_SLIDING = 1 << 2
    IS_DASHING = 1 << 3
    IS_INVULNERABLE = 1 << 4
    CAN_DOUBLE_JUMP = 1 << 5
    CAN_DASH = 1 << 6
    CAN_ATTACK = 1 << 7
    IS_FOCUSING = 1 << 8
    IS_RECOILING = 1 << 9
    IS_ATTACKING = 1 << 10
    IS_CASTING = 1 << 11
    IS_SHADOW_DASHING = 1 << 12


class FrameFlags(IntFlag):
    NONE = 0
    BOSS_FACING_RIGHT = 1 << 0
    KNIGHT_FACING_RIGHT = 1 << 1
    BOSS_INVULNERABLE = 1 << 2
    BOSS_HIT = 1 << 3
    KNIGHT_HIT = 1 << 4


class EntityFlags(IntFlag):
    NONE = 0
    FACING_RIGHT = 1 << 0
    INVULNERABLE = 1 << 1
    DAMAGES_KNIGHT = 1 << 2


class EntityType(IntEnum):
    UNKNOWN = 0
    PROJECTILE = 1
    HAZARD = 2
    MINION = 3
    SHOCKWAVE = 4


class EpisodeStatus(IntEnum):
    IN_PROGRESS = 0
    KNIGHT_DIED = 1
    BOSS_DEFEATED = 2
    ABORTED = 3


BOSS_NAMES = {
    0: "Unknown",
    1: "Gruz Mother",
    2: "Vengefly King",
    3: "Brooding Mawlek",
    4: "False Knight",
    5: "Failed Champion",
    6: "Hornet Protector",
    7: "Hornet Sentinel",
    8: "Massive Moss Charger",
    9: "Flukemarm",
    10: "Mantis Lords",
    11: "Sisters of Battle",
    12: "Oblobbles",
    13: "Hive Knight",
    14: "Broken Vessel",
    15: "Lost Kin",
    16: "Nosk",
    17: "Winged Nosk",
    18: "The Collector",
    19: "God Tamer",
    20: "Crystal Guardian",
    21: "Enraged Guardian",
    22: "Uumuu",
    23: "Traitor Lord",
    24: "Grey Prince Zote",
    25: "Soul Warrior",
    26: "Soul Master",
}

# Struct Formats & Dataclasses

EXPECTED_MAGIC = 0x3430415441444B48  # "HKDATA04" in ASCII little-endian

# 1. EpisodeFileHeader: 40 bytes (<Q 6f BBBB i)
# Magic (8), ArenaMinX (4), ArenaMaxX (4), ArenaMinY (4), ArenaMaxY (4),
# KnightBoundWidth (4), KnightBoundHeight (4),
# BossId (1), BossDifficulty (1), NailDamage (1), MaxHealth (1), Reserved (4)
HEADER_STRUCT = struct.Struct("<Q 6f BBBB i")

# 2. FrameDataHeader: 88 bytes
# Offsets 0..71: I (4) + 9f (36) + 4f (16) + i (4) + 3f (12) = 72B
# Offsets 72..77: 3H (6B)
# Offsets 78..85: 8B (8B)
# Offsets 86..87: H (2B)
FRAME_STRUCT = struct.Struct("<I 13f i 3f 3H 8B H")

# 3. EntityData: 40 bytes
# Offsets 0..31: 8f (32B)
# Offsets 32..35: 2h (4B)
# Offsets 36..37: 2B (2B)
# Offsets 38..39: H (2B)
ENTITY_STRUCT = struct.Struct("<8f 2h 2B H")

# 4. ActionPacket: 8 bytes
# Offsets 0..3: I (4B step_id)
# Offset 4: B (1B action_held)
# Offset 5: B (1B command_flags)
# Offsets 6..7: H (2B reserved)
ACTION_PACKET_STRUCT = struct.Struct("<I B B H")
HANDSHAKE_MAGIC = 0x4B485244  # "HKRD" in ASCII little-endian (4 bytes)
HANDSHAKE_STRUCT = struct.Struct("<I")

assert HEADER_STRUCT.size == 40, (
    f"EpisodeFileHeader size must be 40, got {HEADER_STRUCT.size}"
)
assert FRAME_STRUCT.size == 88, (
    f"FrameDataHeader size must be 88, got {FRAME_STRUCT.size}"
)
assert ENTITY_STRUCT.size == 40, f"EntityData size must be 40, got {ENTITY_STRUCT.size}"
assert ACTION_PACKET_STRUCT.size == 8, f"ActionPacket size must be 8, got {ACTION_PACKET_STRUCT.size}"
assert HANDSHAKE_STRUCT.size == 4, f"Handshake size must be 4, got {HANDSHAKE_STRUCT.size}"


@dataclass
class ActionPacket:
    step_id: int
    action_held: ActionButtons
    command_flags: int = 0
    reserved: int = 0

    def pack(self) -> bytes:
        return ACTION_PACKET_STRUCT.pack(
            self.step_id, int(self.action_held), self.command_flags, self.reserved
        )

    @classmethod
    def unpack(cls, buffer: bytes) -> ActionPacket:
        step_id, action_held, cmd_flags, res = ACTION_PACKET_STRUCT.unpack(buffer[:8])
        return cls(step_id, ActionButtons(action_held), cmd_flags, res)



@dataclass
class EpisodeHeader:
    magic: int
    arena_min_x: float
    arena_max_x: float
    arena_min_y: float
    arena_max_y: float
    knight_bound_width: float
    knight_bound_height: float
    boss_id: int
    boss_difficulty: int
    nail_damage: int
    max_health: int
    reserved: int

    @property
    def boss_name(self) -> str:
        return BOSS_NAMES.get(self.boss_id, f"Boss_{self.boss_id}")

    @property
    def difficulty_name(self) -> str:
        return (
            ["Attuned", "Ascended", "Radiant"][self.boss_difficulty]
            if self.boss_difficulty in (0, 1, 2)
            else str(self.boss_difficulty)
        )

    def pack(self) -> bytes:
        return HEADER_STRUCT.pack(
            self.magic,
            self.arena_min_x,
            self.arena_max_x,
            self.arena_min_y,
            self.arena_max_y,
            self.knight_bound_width,
            self.knight_bound_height,
            self.boss_id,
            self.boss_difficulty,
            self.nail_damage,
            self.max_health,
            self.reserved,
        )

    @classmethod
    def unpack(cls, buffer: bytes) -> EpisodeHeader:
        (
            magic,
            min_x,
            max_x,
            min_y,
            max_y,
            knight_bw,
            knight_bh,
            boss_id,
            boss_diff,
            nail_dmg,
            max_hp,
            res,
        ) = HEADER_STRUCT.unpack(buffer[:40])
        return cls(
            magic,
            min_x,
            max_x,
            min_y,
            max_y,
            knight_bw,
            knight_bh,
            boss_id,
            boss_diff,
            nail_dmg,
            max_hp,
            res,
        )


@dataclass
class EntityData:
    x: float
    y: float
    vx: float
    vy: float
    bound_width: float
    bound_height: float
    rotation: float
    progress: float
    entity_id: int
    hp: int
    kind: EntityType
    flags: EntityFlags
    reserved: int

    @classmethod
    def unpack(cls, buffer: bytes) -> EntityData:
        (x, y, vx, vy, bw, bh, rot, prog, ent_id, hp, kind_b, flags_b, res) = (
            ENTITY_STRUCT.unpack(buffer[:40])
        )
        return cls(
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            bound_width=bw,
            bound_height=bh,
            rotation=rot,
            progress=prog,
            entity_id=ent_id,
            hp=hp,
            kind=EntityType(kind_b)
            if kind_b in EntityType._value2member_map_
            else EntityType.UNKNOWN,
            flags=EntityFlags(flags_b),
            reserved=res,
        )


@dataclass
class FrameDataHeader:
    frame_id: int
    knight_x: float
    knight_y: float
    knight_vx: float
    knight_vy: float
    nail_cooldown: float
    dash_cooldown: float
    shadow_dash_cooldown: float
    invuln_remaining: float
    focus_progress: float
    boss_x: float
    boss_y: float
    boss_vx: float
    boss_vy: float
    boss_hp: int
    fsm_state_time: float
    boss_bound_width: float
    boss_bound_height: float
    knight_flags: KnightFlags
    boss_fsm_state: int
    prev_fsm_state: int
    knight_hp: int
    knight_mp: int
    knight_mp_reserve: int
    is_done: EpisodeStatus
    entity_count: int
    flags: FrameFlags
    action_pressed: ActionButtons
    action_held: ActionButtons
    reserved: int

    @classmethod
    def unpack(cls, buffer: bytes) -> FrameDataHeader:
        (
            frame_id,
            kx,
            ky,
            kvx,
            kvy,
            nail_cd,
            dash_cd,
            shadow_dash_cd,
            invuln,
            focus,
            bx,
            by,
            bvx,
            bvy,
            boss_hp,
            fsm_time,
            bbw,
            bbh,
            k_flags,
            b_fsm,
            prev_fsm,
            khp,
            kmp,
            kmp_res,
            is_done,
            ent_count,
            flags,
            act_pressed,
            act_held,
            res,
        ) = FRAME_STRUCT.unpack(buffer[:88])

        return cls(
            frame_id=frame_id,
            knight_x=kx,
            knight_y=ky,
            knight_vx=kvx,
            knight_vy=kvy,
            nail_cooldown=nail_cd,
            dash_cooldown=dash_cd,
            shadow_dash_cooldown=shadow_dash_cd,
            invuln_remaining=invuln,
            focus_progress=focus,
            boss_x=bx,
            boss_y=by,
            boss_vx=bvx,
            boss_vy=bvy,
            boss_hp=boss_hp,
            fsm_state_time=fsm_time,
            boss_bound_width=bbw,
            boss_bound_height=bbh,
            knight_flags=KnightFlags(k_flags),
            boss_fsm_state=b_fsm,
            prev_fsm_state=prev_fsm,
            knight_hp=khp,
            knight_mp=kmp,
            knight_mp_reserve=kmp_res,
            is_done=EpisodeStatus(is_done)
            if is_done in EpisodeStatus._value2member_map_
            else EpisodeStatus.IN_PROGRESS,
            entity_count=ent_count,
            flags=FrameFlags(flags),
            action_pressed=ActionButtons(act_pressed),
            action_held=ActionButtons(act_held),
            reserved=res,
        )


@dataclass
class Frame:
    header: FrameDataHeader
    entities: list[EntityData]


# Stream / File Reader


class EpisodeReader:
    """Reads binary episode recordings saved by RecordMod."""

    @staticmethod
    def _read_header(f, filepath: str) -> EpisodeHeader:
        """Reads the EpisodeHeader and rejects files of any other format version."""
        header_bytes = f.read(HEADER_STRUCT.size)
        if len(header_bytes) < HEADER_STRUCT.size:
            raise ValueError(f"{filepath}: file too small for header: {len(header_bytes)} bytes")

        header = EpisodeHeader.unpack(header_bytes)
        if header.magic != EXPECTED_MAGIC:
            raise ValueError(
                f"{filepath}: bad magic 0x{header.magic:X} (expected 0x{EXPECTED_MAGIC:X})"
            )
        return header

    @staticmethod
    def _read_frame(f, filepath: str) -> Frame | None:
        """Reads one frame; returns None at EOF and drops a truncated final frame with a warning."""
        frame_bytes = f.read(FRAME_STRUCT.size)
        if not frame_bytes:
            return None
        if len(frame_bytes) < FRAME_STRUCT.size:
            warnings.warn(f"{filepath}: dropped truncated final frame header")
            return None
        fh = FrameDataHeader.unpack(frame_bytes)

        ent_bytes = f.read(fh.entity_count * ENTITY_STRUCT.size)
        if len(ent_bytes) < fh.entity_count * ENTITY_STRUCT.size:
            warnings.warn(f"{filepath}: dropped final frame {fh.frame_id} with truncated entities")
            return None
        entities = [
            EntityData.unpack(ent_bytes[i * ENTITY_STRUCT.size : (i + 1) * ENTITY_STRUCT.size])
            for i in range(fh.entity_count)
        ]
        return Frame(header=fh, entities=entities)

    @staticmethod
    def read_file(filepath: str) -> tuple[EpisodeHeader, list[Frame]]:
        with open(filepath, "rb") as f:
            header = EpisodeReader._read_header(f, filepath)

            frames: list[Frame] = []
            while (frame := EpisodeReader._read_frame(f, filepath)) is not None:
                frames.append(frame)

            return header, frames

    @staticmethod
    def iterate_file(filepath: str) -> Iterator[tuple[EpisodeHeader, Frame]]:
        """Memory-efficient generator yielding one frame at a time."""
        with open(filepath, "rb") as f:
            header = EpisodeReader._read_header(f, filepath)

            while (frame := EpisodeReader._read_frame(f, filepath)) is not None:
                yield header, frame
