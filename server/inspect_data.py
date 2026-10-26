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
    FRAME_DT,
    EntityFlags,
    EpisodeHeader,
    EpisodeReader,
    EpisodeStatus,
    Frame,
    flag_names,
)


def print_episode_summary(header: EpisodeHeader, frames: list[Frame], filepath: str):
    file_size = os.path.getsize(filepath)
    num_frames = len(frames)
    duration_sec = num_frames * FRAME_DT

    final_status = frames[-1].header.is_done.name if frames else "EMPTY"

    print("=" * 78)
    print(f" HOLLOW KNIGHT TELEMETRY INSPECTION: {os.path.basename(filepath)}")
    print("=" * 78)
    print(f"File Path:       {filepath}")
    print(f"File Size:       {file_size:,} bytes")
    print(f"Magic:           0x{header.magic:X}")
    print(f"Boss:            {header.boss_name} (ID: {header.boss_id})")
    print(f"Difficulty:      {header.difficulty_name} (Tier {header.boss_difficulty})")
    print(f"Nail Damage:     {header.nail_damage}")
    print(f"Max Masks:       {header.max_health}")
    print(f"Total Frames:    {num_frames} ({duration_sec:.2f} seconds)")
    print(f"Final Outcome:   {final_status}")
    print("=" * 78)


def print_frame_detail(frame: Frame, total_frames: int):
    h = frame.header
    t_sec = h.frame_id * FRAME_DT

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
    print(f"  Combat Flags:  {flag_names(h.knight_flags)}")

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
    print(f"  Frame Flags:   {flag_names(h.flags)}")

    print("\n[INPUTS]")
    print(f"  Pressed (tap): {flag_names(h.action_pressed)}")
    print(f"  Held (down):   {flag_names(h.action_held)}")

    print(f"\n[DYNAMIC ENTITIES: {h.entity_count}]")
    if not frame.entities:
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
        args.tail = 1
    if args.tail:
        selected = frames[-args.tail:]
    else:
        selected = [frames[max(0, min(args.frame, len(frames) - 1))]]
    for frame in selected:
        print_frame_detail(frame, len(frames))


if __name__ == "__main__":
    main()
