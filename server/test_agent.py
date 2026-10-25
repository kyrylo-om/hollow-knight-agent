#!/usr/bin/env python3
"""
Test Agent for Hollow Knight TrainMod.
Computes test actions (10 ticks Left, 10 Pause, 10 Right, 10 Pause, + 3s Jump)
and drives the agent loop using TrainClient from tcp_client.py.
"""

from __future__ import annotations

import sys
from protocol import ActionButtons
from tcp_client import TrainClient


def compute_action(tick: int) -> tuple[ActionButtons, str]:
    """
    Computes the test action for a given physics tick:
    - 10 ticks Left, 10 ticks Pause, 10 ticks Right, 10 ticks Pause (40 ticks cycle)
    - Full jump every 3 seconds (150 ticks cycle), held for 18 ticks (~0.36s)
    """
    # 1. Horizontal movement cycle (40 ticks = 0.8s at 50 Hz)
    horiz_phase = tick % 40
    if 0 <= horiz_phase < 10:
        horiz_action = ActionButtons.LEFT
        horiz_desc = "LEFT"
    elif 10 <= horiz_phase < 20:
        horiz_action = ActionButtons.NONE
        horiz_desc = "PAUSE"
    elif 20 <= horiz_phase < 30:
        horiz_action = ActionButtons.RIGHT
        horiz_desc = "RIGHT"
    else:
        horiz_action = ActionButtons.NONE
        horiz_desc = "PAUSE"

    # 2. Jump cycle (150 ticks = 3.0s at 50 Hz)
    jump_phase = tick % 150
    if 0 <= jump_phase < 18:
        jump_action = ActionButtons.JUMP
        jump_desc = "+ JUMP"
    else:
        jump_action = ActionButtons.NONE
        jump_desc = ""

    action = horiz_action | jump_action
    desc = f"{horiz_desc} {jump_desc}".strip()
    return action, desc


def run_agent_loop(client: TrainClient) -> None:
    """Executes the lockstep action loop with TrainClient."""
    tick = 0
    print(
        f"{'Tick':>6} | {'Frame':>6} | {'Knight Pos':>16} | {'HP':>4} | "
        f"{'Boss HP':>7} | {'Action Sent':<16} | {'Entities':>8}"
    )
    print("-" * 80)

    while True:
        # 1. Receive telemetry frame from TrainMod
        frame_hdr, entities = client.receive_frame()

        # 2. Compute action for this tick
        action, action_desc = compute_action(tick)

        # 3. Send action packet to game
        client.send_action(step_id=tick, action=action, command_flags=0)

        # 4. Log progress periodically or during jumps
        if tick % 5 == 0 or (tick % 150 < 18 and tick % 2 == 0):
            kpos_str = f"({frame_hdr.knight_x:6.2f}, {frame_hdr.knight_y:5.2f})"
            print(
                f"{tick:6d} | {frame_hdr.frame_id:6d} | {kpos_str:>16} | "
                f"{frame_hdr.knight_hp:4d} | {frame_hdr.boss_hp:7d} | "
                f"{action_desc:<16} | {len(entities):8d}"
            )

        tick += 1


def main():
    client = TrainClient()
    try:
        client.connect()
        run_agent_loop(client)
    except KeyboardInterrupt:
        print("\n[Ctrl+C] Stopping test agent...")
    except ConnectionError as e:
        print(f"\n[Connection Closed] {e}")
    finally:
        client.close()
        print("Player controls restored in game.")


if __name__ == "__main__":
    main()
