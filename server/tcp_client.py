"""
TCP client for communicating with Hollow Knight's TrainMod server.
Handles socket transport, connection retries, binary handshakes,
and lockstep telemetry frame reception & action dispatch.
"""

from __future__ import annotations

import socket
import time

from protocol import (
    ENTITY_STRUCT,
    FRAME_STRUCT,
    HANDSHAKE_MAGIC,
    HANDSHAKE_STRUCT,
    HEADER_STRUCT,
    ActionButtons,
    ActionPacket,
    EntityData,
    EpisodeHeader,
    FrameDataHeader,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11451


def read_exact(sock: socket.socket, num_bytes: int) -> bytes:
    """Reads exactly num_bytes from a socket or raises ConnectionError on EOF."""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            raise ConnectionError("Socket connection closed by server.")
        buf.extend(chunk)
    return bytes(buf)


class TrainClient:
    """
    Client interface managing lockstep TCP communication with Hollow Knight TrainMod.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.header: EpisodeHeader | None = None
        self.is_connected: bool = False

    def connect(self, retry_interval: float = 1.0) -> EpisodeHeader:
        """
        Connects to TrainMod, retrying until the server is listening, and completes the handshake.
        """
        print(f"Connecting to Hollow Knight TrainMod at {self.host}:{self.port}...")
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.connect((self.host, self.port))
                self.sock = sock
                self.is_connected = True
                print("Connected to TrainMod server!")
                break
            except (ConnectionRefusedError, OSError):
                print(
                    f"Waiting for Hollow Knight TrainMod on {self.port}... "
                    f"(retrying in {retry_interval:.1f}s)"
                )
                time.sleep(retry_interval)

        return self._perform_handshake()

    def _perform_handshake(self) -> EpisodeHeader:
        """Reads EpisodeFileHeader from server and sends Handshake ACK."""
        assert self.sock is not None, "Socket must be connected before handshake."
        print("Performing handshake with game server...")

        # 1. Read 16-byte EpisodeFileHeader from server
        header_raw = read_exact(self.sock, HEADER_STRUCT.size)
        self.header = EpisodeHeader.unpack(header_raw)
        print(
            f"Received Episode Header: Boss '{self.header.boss_name}' (ID: {self.header.boss_id}), "
            f"Difficulty: {self.header.difficulty_name}, Nail: {self.header.nail_damage}, "
            f"Masks: {self.header.max_health}"
        )

        # 2. Send 4-byte Handshake Ack ("HKRD")
        ack_bytes = HANDSHAKE_STRUCT.pack(HANDSHAKE_MAGIC)
        self.sock.sendall(ack_bytes)
        print("Handshake acknowledged (HKRD). Starting lockstep loop!\n")
        return self.header

    def receive_frame(self) -> tuple[FrameDataHeader, list[EntityData]]:
        """
        Receives a telemetry frame from TrainMod:
        - 84-byte FrameDataHeader
        - Trailing EntityData items (40 bytes each) if entity_count > 0
        """
        if self.sock is None or not self.is_connected:
            raise ConnectionError("Cannot receive frame: Not connected to TrainMod.")

        # 1. Read 84-byte FrameDataHeader
        frame_raw = read_exact(self.sock, FRAME_STRUCT.size)
        frame_hdr = FrameDataHeader.unpack(frame_raw)

        # 2. Read dynamic entities if present
        entities: list[EntityData] = []
        if frame_hdr.entity_count > 0:
            ent_raw = read_exact(self.sock, ENTITY_STRUCT.size * frame_hdr.entity_count)
            for i in range(frame_hdr.entity_count):
                offset = i * ENTITY_STRUCT.size
                entities.append(EntityData.unpack(ent_raw[offset : offset + ENTITY_STRUCT.size]))

        return frame_hdr, entities

    def send_action(
        self,
        step_id: int,
        action: ActionButtons,
        command_flags: int = 0,
    ) -> None:
        """
        Sends an 8-byte ActionPacket back to TrainMod in lockstep.
        """
        if self.sock is None or not self.is_connected:
            raise ConnectionError("Cannot send action: Not connected to TrainMod.")

        packet = ActionPacket(
            step_id=step_id,
            action_held=action,
            command_flags=command_flags,
        )
        self.sock.sendall(packet.pack())

    def step(
        self,
        step_id: int,
        action: ActionButtons,
        command_flags: int = 0,
    ) -> tuple[FrameDataHeader, list[EntityData]]:
        """
        Convenience lockstep step: sends action and waits for the next telemetry frame.
        """
        self.send_action(step_id, action, command_flags)
        return self.receive_frame()

    def close(self) -> None:
        """Closes the connection cleanly."""
        self.is_connected = False
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        print("TrainClient connection closed.")

    def __enter__(self) -> TrainClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
