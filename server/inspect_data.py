#!/usr/bin/env python3
"""
CLI Data Inspector for Hollow Knight Binary Telemetry Recordings (.bin).

Usage:
    python inspect_data.py path/to/episode.bin
    python inspect_data.py path/to/episode.bin --frame 150
    python inspect_data.py path/to/episode.bin --last
"""

import argparse
import os
import sys

from protocol import (
    EXPECTED_MAGIC,
    ActionButtons,
    EntityFlags,
    EpisodeHeader,
    EpisodeReader,
    EpisodeStatus,
    Frame,
    FrameFlags,
    KnightFlags,
)


def format_buttons(b: ActionButtons) -> str:
    if b == ActionButtons.NONE:
        return "None"
    names = [
        flag.name
        for flag in ActionButtons
        if flag in b and flag.name is not None and flag != ActionButtons.NONE
    ]
    return " | ".join(names) if names else "None"


def format_knight_flags(f: KnightFlags) -> str:
    if f == KnightFlags.NONE:
        return "None"
    names = [
        flag.name
        for flag in KnightFlags
        if flag in f and flag.name is not None and flag != KnightFlags.NONE
    ]
    return " | ".join(names) if names else "None"


def format_frame_flags(f: FrameFlags) -> str:
    if f == FrameFlags.NONE:
        return "None"
    names = [
        flag.name
        for flag in FrameFlags
        if flag in f and flag.name is not None and flag != FrameFlags.NONE
    ]
    return " | ".join(names) if names else "None"


def print_episode_summary(header: EpisodeHeader, frames: list[Frame], filepath: str):
    file_size = os.path.getsize(filepath)
    num_frames = len(frames)
    duration_sec = num_frames * 0.02
    magic_ok = (
        "OK (0x3330415441444B48)"
        if header.magic == EXPECTED_MAGIC
        else f"INVALID (0x{header.magic:X})"
    )

    final_status = frames[-1].header.is_done.name if frames else "EMPTY"

    print("=" * 78)
    print(f" HOLLOW KNIGHT TELEMETRY INSPECTION: {os.path.basename(filepath)}")
    print("=" * 78)
    print(f"File Path:       {filepath}")
    print(f"File Size:       {file_size:,} bytes")
    print(f"Magic:           {magic_ok}")
    print(f"Boss:            {header.boss_name} (ID: {header.boss_id})")
    print(f"Difficulty:      {header.difficulty_name} (Tier {header.boss_difficulty})")
    print(f"Nail Damage:     {header.nail_damage}")
    print(f"Max Masks:       {header.max_health}")
    print(f"Total Frames:    {num_frames} ({duration_sec:.2f} seconds)")
    print(f"Final Outcome:   {final_status}")
    print("=" * 78)


def print_frame_detail(frame: Frame, total_frames: int):
    h = frame.header
    t_sec = h.frame_id * 0.02

    print(
        f"\n--- FRAME #{h.frame_id} / {total_frames - 1} (Time: {t_sec:.2f}s) | Status: {h.is_done.name} ---"
    )

    print("\n[KNIGHT]")
    print(f"  Position:      X={h.knight_x:7.2f}, Y={h.knight_y:7.2f}")
    print(f"  Velocity:      Vx={h.knight_vx:6.2f}, Vy={h.knight_vy:6.2f}")
    print(
        f"  Health & Soul: HP={h.knight_hp}, MP={h.knight_mp}, Soul Vessels={h.knight_mp_reserve}"
    )
    print(
        f"  Cooldowns:     Nail={h.nail_cooldown:4.2f}s | Dash={h.dash_cooldown:4.2f}s | Invuln={h.invuln_remaining:4.2f}s | Focus={h.focus_progress:4.2f}"
    )
    print(f"  Combat Flags:  {format_knight_flags(h.knight_flags)}")

    print("\n[BOSS]")
    print(f"  Position:      X={h.boss_x:7.2f}, Y={h.boss_y:7.2f}")
    print(f"  Velocity:      Vx={h.boss_vx:6.2f}, Vy={h.boss_vy:6.2f}")
    print(
        f"  Bounds:        Width={h.boss_bound_width:.2f}, Height={h.boss_bound_height:.2f}"
    )
    print(f"  Health:        HP={h.boss_hp}")
    print(
        f"  FSM State:     ID={h.boss_fsm_state} (Prev={h.prev_fsm_state}) | State Time={h.fsm_state_time:.2f}s"
    )
    print(f"  Frame Flags:   {format_frame_flags(h.flags)}")

    print("\n[INPUTS]")
    print(f"  Pressed (tap): {format_buttons(h.action_pressed)}")
    print(f"  Held (down):   {format_buttons(h.action_held)}")

    print(f"\n[DYNAMIC ENTITIES: {h.entity_count}]")
    if h.entity_count == 0 or not frame.entities:
        print("  (No dynamic hazards or projectiles active)")
    else:
        print(
            f"  {'#':<3} {'Type':<12} {'ID':<6} {'HP':<4} {'Pos (X, Y)':<18} {'Vel (Vx, Vy)':<18} {'Rot':<6} {'Prog':<6} {'Damages?':<8}"
        )
        print("  " + "-" * 88)
        for idx, ent in enumerate(frame.entities):
            pos_str = f"({ent.x:6.1f}, {ent.y:6.1f})"
            vel_str = f"({ent.vx:5.1f}, {ent.vy:5.1f})"
            damages = "YES" if (ent.flags & EntityFlags.DAMAGES_KNIGHT) else "WARN"
            print(
                f"  {idx:<3} {ent.kind.name:<12} {ent.entity_id:<6} {ent.hp:<4} {pos_str:<18} {vel_str:<18} {ent.rotation:5.1f}° {ent.progress:5.2f}s {damages:<8}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Inspect binary episode telemetry files (.bin)"
    )
    parser.add_argument("filepath", type=str, help="Path to the .bin episode file")
    parser.add_argument(
        "-f",
        "--frame",
        type=int,
        default=0,
        help="Nth frame index to inspect (default: 0)",
    )
    parser.add_argument(
        "--last",
        action="store_true",
        help="Inspect the final/terminal frame of the episode",
    )
    parser.add_argument(
        "--tail", type=int, default=None, help="Inspect the last N frames"
    )

    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print(f"Error: File not found at '{args.filepath}'", file=sys.stderr)
        sys.exit(1)

    try:
        header, frames = EpisodeReader.read_file(args.filepath)
    except Exception as e:
        print(f"Error reading telemetry file: {e}", file=sys.stderr)
        sys.exit(1)

    print_episode_summary(header, frames, args.filepath)

    if not frames:
        print("\n(Episode file contains 0 frames)")
        return

    if args.last:
        frame_idx = len(frames) - 1
        print_frame_detail(frames[frame_idx], len(frames))
    elif args.tail:
        start_idx = max(0, len(frames) - args.tail)
        for i in range(start_idx, len(frames)):
            print_frame_detail(frames[i], len(frames))
    else:
        frame_idx = max(0, min(args.frame, len(frames) - 1))
        print_frame_detail(frames[frame_idx], len(frames))


if __name__ == "__main__":
    main()
