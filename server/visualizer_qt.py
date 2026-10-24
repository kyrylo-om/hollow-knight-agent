"""
Hollow Knight Binary Telemetry Visualizer (Qt6 Desktop Application).

Features:
- Hardware-accelerated 2D arena canvas rendering game entities as viewed from binary telemetry
- Timeline scrub slider with smooth 0-latency scrubbing across thousands of frames
- Arrow-key frame-by-frame navigation (Left/Right, Shift+Left/Right, Spacebar play/pause)
- Scrollable telemetry sidebar with real-time Knight, Boss, and Controller inputs
- Expandable "show more" accordion tree view for dynamic entities (hazards, projectiles, shockwaves)
- Mouse wheel zoom & pan in the arena view
"""

import math
import os
import sys

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from boss_states import get_fsm_state_name
from protocol import (
    ActionButtons,
    EntityData,
    EntityFlags,
    EntityType,
    EpisodeHeader,
    EpisodeReader,
    EpisodeStatus,
    Frame,
    FrameFlags,
    KnightFlags,
)


# 1. 2D Arena Canvas Widget


class ArenaCanvas(QWidget):
    """
    Renders the game scene in 2D coordinate space as captured by binary telemetry.
    Supports zoom (mouse wheel) and pan (click-and-drag).
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(600, 450)
        self.setStyleSheet("background-color: #111318; border-radius: 8px;")

        # World camera settings (Unity arena coordinates)
        # False Knight arena is roughly X in [12, 48], Y in [25, 43]
        self.cam_center_x = 30.0
        self.cam_center_y = 33.0
        self.zoom = 24.0  # Pixels per Unity unit

        # Drag state
        self._dragging = False
        self._last_mouse_pos = None

        # Current frame to render
        self.current_frame: Frame | None = None
        self.header: EpisodeHeader | None = None

    def set_frame(self, frame: Frame, header: EpisodeHeader | None = None):
        self.current_frame = frame
        if header is not None:
            self.header = header
        self.update()

    def reset_camera(self):
        self.cam_center_x = 30.0
        self.cam_center_y = 33.0
        self.zoom = 24.0
        self.update()

    # Coordinate Transforms

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """Convert Unity world coordinates (Y up) to Qt widget pixels (Y down)."""
        w = self.width()
        h = self.height()
        sx = w / 2.0 + (wx - self.cam_center_x) * self.zoom
        sy = h / 2.0 - (wy - self.cam_center_y) * self.zoom
        return sx, sy

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert Qt widget pixels to Unity world coordinates."""
        w = self.width()
        h = self.height()
        wx = (sx - w / 2.0) / self.zoom + self.cam_center_x
        wy = (h / 2.0 - sy) / self.zoom + self.cam_center_y
        return wx, wy

    # Mouse Events (Pan & Zoom)

    def wheelEvent(self, event: QWheelEvent):
        degrees = event.angleDelta().y() / 8.0
        factor = 1.03 if degrees > 0 else 0.97
        self.zoom = max(8.0, min(80.0, self.zoom * factor))
        self.update()

    def mousePressEvent(self, event):
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._dragging = True
            self._last_mouse_pos = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_mouse_pos:
            pos = event.position().toPoint()
            delta = pos - self._last_mouse_pos
            self._last_mouse_pos = pos
            self.cam_center_x -= delta.x() / self.zoom
            self.cam_center_y += delta.y() / self.zoom
            self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def mouseDoubleClickEvent(self, event):
        self.reset_camera()

    # Painting

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)

            w = self.width()
            h = self.height()

            # Background
            painter.fillRect(0, 0, w, h, QColor("#111318"))

            # Arena bounds & grid
            self._draw_arena_grid(painter)

            if not self.current_frame:
                # Placeholder text if no episode loaded
                painter.setPen(QColor("#64748b"))
                painter.setFont(QFont("Arial", 14))
                painter.drawText(
                    self.rect(),
                    Qt.AlignCenter,
                    "Open a .bin telemetry recording to begin inspection",
                )
                return

            f = self.current_frame
            hdr = f.header

            # 1. Draw Boss
            self._draw_boss(painter, hdr)

            # 2. Draw Dynamic Entities (hazards, projectiles, shockwaves)
            for ent in f.entities:
                self._draw_entity(painter, ent)

            # 3. Draw Knight
            self._draw_knight(painter, hdr)

            # 4. Canvas HUD Overlay
            self._draw_hud_overlay(painter, hdr)
        finally:
            painter.end()

    def _draw_arena_grid(self, p: QPainter):
        """Draws arena floor at Y=26.2, side walls, and background distance reference lines."""
        # Arena floor is at Y ~ 26.2
        floor_y = 26.2
        _, s_floor_y = self.world_to_screen(0, floor_y)

        # Ground block
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1e222d"))
        p.drawRect(0, int(s_floor_y), self.width(), int(self.height() - s_floor_y))

        # Solid floor edge
        p.setPen(QPen(QColor("#38bdf8"), 2.0))
        p.drawLine(0, int(s_floor_y), self.width(), int(s_floor_y))

        # Grid lines every 5 world units
        p.setPen(QPen(QColor("#1e293b"), 1.0, Qt.DashLine))
        start_x, end_x = 10, 50
        for x in range(start_x, end_x + 1, 5):
            sx, _ = self.world_to_screen(x, 0)
            p.drawLine(int(sx), 0, int(sx), int(s_floor_y))

        # Ceiling reference (Y=42)
        _, s_ceil_y = self.world_to_screen(0, 42.0)
        p.setPen(QPen(QColor("#334155"), 1.0, Qt.DotLine))
        p.drawLine(0, int(s_ceil_y), self.width(), int(s_ceil_y))

        # Left wall (X=14) and Right wall (X=46)
        s_left_x, _ = self.world_to_screen(14.0, 0)
        s_right_x, _ = self.world_to_screen(46.0, 0)
        p.setPen(QPen(QColor("#334155"), 1.5, Qt.DashLine))
        p.drawLine(int(s_left_x), 0, int(s_left_x), int(s_floor_y))
        p.drawLine(int(s_right_x), 0, int(s_right_x), int(s_floor_y))

    def _draw_knight(self, p: QPainter, h):
        """Renders the player Knight with direction, combat status, and velocity vector."""
        sx, sy = self.world_to_screen(h.knight_x, h.knight_y)

        # Dimensions: roughly 1.3 x 1.8 units in world space
        kw = 1.3 * self.zoom
        kh = 1.8 * self.zoom

        flags = h.knight_flags
        is_facing_right = bool(h.flags & FrameFlags.KNIGHT_FACING_RIGHT)
        is_invuln = bool(flags & KnightFlags.IS_INVULNERABLE)
        is_dash = bool(flags & KnightFlags.IS_DASHING)
        is_attack = bool(flags & KnightFlags.IS_ATTACKING)

        p.save()
        p.translate(sx, sy)

        # 1. Motion blur / dash trail
        if is_dash:
            dash_offset = -kw * 0.8 if is_facing_right else kw * 0.8
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(56, 189, 248, 70))
            p.drawRoundedRect(QRectF(dash_offset - kw / 2, -kh / 2, kw, kh), 6, 6)

        # 2. Invulnerability glow
        if is_invuln:
            p.setPen(QPen(QColor("#facc15"), 3.0, Qt.DashLine))
            p.setBrush(QColor(250, 204, 21, 40))
            p.drawRoundedRect(QRectF(-kw / 2 - 4, -kh / 2 - 4, kw + 8, kh + 8), 10, 10)

        # 3. Main Knight Body (Cyan capsule)
        body_color = QColor("#38bdf8") if not is_invuln else QColor("#e0f2fe")
        p.setPen(QPen(QColor("#0284c7"), 2.0))
        p.setBrush(body_color)
        p.drawRoundedRect(QRectF(-kw / 2, -kh / 2, kw, kh), 6, 6)

        # 4. Facing Eye Indicator
        eye_x = kw * 0.2 if is_facing_right else -kw * 0.2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0f172a"))
        p.drawEllipse(QPointF(eye_x, -kh * 0.15), 3.5, 3.5)

        # 5. Nail Swing Slash Arc
        if is_attack:
            p.setPen(QPen(QColor("#ffffff"), 3.0, Qt.SolidLine, Qt.RoundCap))
            slash_x = kw * 0.6 if is_facing_right else -kw * 0.6
            path = QPainterPath()
            path.moveTo(slash_x, -kh * 0.6)
            path.quadTo(slash_x * 1.5, 0, slash_x, kh * 0.6)
            p.drawPath(path)

        p.restore()

        # 6. Velocity Vector Arrow (Cyan)
        self._draw_velocity_vector(
            p, sx, sy, h.knight_vx, h.knight_vy, QColor("#38bdf8")
        )

        # 7. Name Tag
        p.setPen(QColor("#bae6fd"))
        p.setFont(QFont("Arial", 9, QFont.Bold))
        tag = f"Knight [HP:{h.knight_hp}]"
        p.drawText(int(sx - 35), int(sy - kh / 2 - 6), tag)

    def _draw_boss(self, p: QPainter, h):
        """Renders the Boss bounding box, facing, health bar, and FSM state label."""
        sx, sy = self.world_to_screen(h.boss_x, h.boss_y)

        # Dimensions from bounding box half-extents
        bw = (h.boss_bound_width * 2.0 if h.boss_bound_width > 0 else 4.2) * self.zoom
        bh = (h.boss_bound_height * 2.0 if h.boss_bound_height > 0 else 4.5) * self.zoom

        facing_right = bool(h.flags & FrameFlags.BOSS_FACING_RIGHT)
        is_invuln = bool(h.flags & FrameFlags.BOSS_INVULNERABLE)
        was_hit = bool(h.flags & FrameFlags.BOSS_HIT)

        p.save()
        p.translate(sx, sy)

        # Body Box
        fill_color = QColor("#f43f5e") if not was_hit else QColor("#ffffff")
        border_color = QColor("#be123c") if not is_invuln else QColor("#fbbf24")
        p.setPen(QPen(border_color, 2.5))
        p.setBrush(QColor(fill_color.red(), fill_color.green(), fill_color.blue(), 180))
        p.drawRoundedRect(QRectF(-bw / 2, -bh / 2, bw, bh), 8, 8)

        # Facing Eye
        eye_x = bw * 0.25 if facing_right else -bw * 0.25
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#4c0519"))
        p.drawEllipse(QPointF(eye_x, -bh * 0.1), 5.0, 5.0)

        p.restore()

        # Velocity Vector Arrow (Crimson)
        self._draw_velocity_vector(p, sx, sy, h.boss_vx, h.boss_vy, QColor("#f43f5e"))

        # Overhead Health Bar & FSM State Label
        state_str = get_fsm_state_name(h.boss_fsm_state)
        p.setPen(QColor("#fecdd3"))
        p.setFont(QFont("Arial", 9, QFont.Bold))
        state_label = f"Boss: {state_str} ({h.fsm_state_time:.1f}s) | HP:{h.boss_hp}"
        p.drawText(int(sx - 70), int(sy - bh / 2 - 12), state_label)

    def _draw_entity(self, p: QPainter, ent: EntityData):
        """Renders dynamic entities (falling rocks, projectiles, shockwaves, telegraph warnings)."""
        sx, sy = self.world_to_screen(ent.x, ent.y)

        # Width and height (2 * extents)
        ew = (ent.bound_width * 2.0 if ent.bound_width > 0 else 1.2) * self.zoom
        eh = (ent.bound_height * 2.0 if ent.bound_height > 0 else 1.2) * self.zoom

        damages_knight = bool(ent.flags & EntityFlags.DAMAGES_KNIGHT)
        is_warn = not damages_knight

        p.save()
        p.translate(sx, sy)
        p.rotate(-ent.rotation)  # Qt clockwise rotation

        if damages_knight:
            # Actively damaging hazard / projectile
            if ent.kind == EntityType.SHOCKWAVE:
                p.setPen(QPen(QColor("#06b6d4"), 3.0))
                p.setBrush(QColor(6, 182, 212, 100))
                p.drawRoundedRect(QRectF(-ew / 2, -eh / 2, ew, eh), 4, 4)
            elif ent.kind == EntityType.PROJECTILE:
                p.setPen(QPen(QColor("#facc15"), 2.0))
                p.setBrush(QColor(250, 204, 21, 190))
                p.drawPolygon(
                    [
                        QPointF(-ew / 2, -eh / 2),
                        QPointF(ew / 2, 0),
                        QPointF(-ew / 2, eh / 2),
                    ]
                )
            else:
                # Hazard / Falling Rock
                p.setPen(QPen(QColor("#ea580c"), 2.0))
                p.setBrush(QColor(249, 115, 22, 180))
                p.drawRect(QRectF(-ew / 2, -eh / 2, ew, eh))
                p.drawLine(int(-ew / 2), int(-eh / 2), int(ew / 2), int(eh / 2))
                p.drawLine(int(ew / 2), int(-eh / 2), int(-ew / 2), int(eh / 2))
        else:
            # Warning telegraph (non-damaging countdown)
            p.setPen(QPen(QColor("#eab308"), 2.0, Qt.DashLine))
            p.setBrush(QColor(234, 179, 8, 50))
            p.drawRect(QRectF(-ew / 2, -eh / 2, ew, eh))

        p.restore()

        # Velocity arrow
        self._draw_velocity_vector(p, sx, sy, ent.vx, ent.vy, QColor("#fb923c"))

        # Label & Telegraph countdown
        p.setFont(QFont("Arial", 8))
        if is_warn and ent.progress > 0:
            p.setPen(QColor("#fef08a"))
            p.drawText(int(sx - 20), int(sy - eh / 2 - 4), f"WARN {ent.progress:.2f}s")
        else:
            p.setPen(QColor("#cbd5e1"))
            p.drawText(int(sx - 15), int(sy - eh / 2 - 4), f"#{ent.entity_id}")

    def _draw_velocity_vector(
        self, p: QPainter, sx: float, sy: float, vx: float, vy: float, color: QColor
    ):
        """Draws a directional velocity arrow from center."""
        speed = math.sqrt(vx * vx + vy * vy)
        if speed < 0.2:
            return

        scale = 0.12 * self.zoom
        end_x = sx + vx * scale
        end_y = sy - vy * scale

        p.setPen(QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(sx, sy), QPointF(end_x, end_y))

        # Arrow head
        angle = math.atan2(-vy, vx)
        arrow_size = 5.0
        p.drawLine(
            QPointF(end_x, end_y),
            QPointF(
                end_x - arrow_size * math.cos(angle - math.pi / 6),
                end_y - arrow_size * math.sin(angle - math.pi / 6),
            ),
        )
        p.drawLine(
            QPointF(end_x, end_y),
            QPointF(
                end_x - arrow_size * math.cos(angle + math.pi / 6),
                end_y - arrow_size * math.sin(angle + math.pi / 6),
            ),
        )

    def _draw_hud_overlay(self, p: QPainter, h):
        """Draws canvas corner badges (Time, Frame, Outcome)."""
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(15, 23, 42, 190))
        p.drawRoundedRect(QRectF(12, 12, 230, 48), 6, 6)

        t_sec = h.frame_id * 0.02
        p.setPen(QColor("#f8fafc"))
        p.setFont(QFont("Arial", 10, QFont.Bold))
        p.drawText(22, 32, f"Frame: #{h.frame_id}  ({t_sec:.2f}s)")

        status_color = (
            "#22c55e"
            if h.is_done == EpisodeStatus.IN_PROGRESS
            else ("#ef4444" if h.is_done == EpisodeStatus.KNIGHT_DIED else "#eab308")
        )
        p.setPen(QColor(status_color))
        p.setFont(QFont("Arial", 9))
        p.drawText(22, 50, f"Status: {h.is_done.name}")


# 2. Timeline Controls Widget


class TimelineControls(QWidget):
    """
    Scrubbing slider, playback buttons, and speed controls for episode navigation.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget { background-color: #161822; color: #f1f5f9; }
            QSlider::groove:horizontal { height: 6px; background: #334155; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: #38bdf8; border-radius: 3px; }
            QSlider::handle:horizontal {
                background: #f8fafc; border: 2px solid #0284c7; width: 16px; margin-top: -5px; margin-bottom: -5px; border-radius: 8px;
            }
            QPushButton {
                background-color: #242938; border: 1px solid #3b4256; border-radius: 4px; padding: 5px 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #333a4e; }
            QPushButton:pressed { background-color: #1e293b; }
            QPushButton:focus, QSlider:focus, QComboBox:focus, QCheckBox:focus { outline: none; }
            QComboBox { background-color: #242938; border: 1px solid #3b4256; border-radius: 4px; padding: 4px; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # 1. Scrub Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.setTracking(True)
        self.slider.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.slider)

        # 2. Controls Row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)

        self.btn_step_back_10 = QPushButton("<< 10")
        self.btn_step_back = QPushButton("<")
        self.btn_play = QPushButton("▶ Play")
        self.btn_step_fwd = QPushButton(">")
        self.btn_step_fwd_10 = QPushButton("10 >>")

        for btn in (
            self.btn_step_back_10,
            self.btn_step_back,
            self.btn_play,
            self.btn_step_fwd,
            self.btn_step_fwd_10,
        ):
            btn.setFocusPolicy(Qt.NoFocus)

        ctrl_row.addWidget(self.btn_step_back_10)
        ctrl_row.addWidget(self.btn_step_back)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_step_fwd)
        ctrl_row.addWidget(self.btn_step_fwd_10)

        # Speed Selector
        ctrl_row.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1.0x", "2.0x", "4.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFocusPolicy(Qt.NoFocus)
        ctrl_row.addWidget(self.speed_combo)

        # Auto-loop checkbox
        self.chk_loop = QCheckBox("Loop")
        self.chk_loop.setChecked(True)
        self.chk_loop.setFocusPolicy(Qt.NoFocus)
        ctrl_row.addWidget(self.chk_loop)

        # Status text
        ctrl_row.addStretch()
        self.lbl_info = QLabel("Frame: 0 / 0 (0.00s)")
        self.lbl_info.setStyleSheet(
            "color: #94a3b8; font-family: Menlo, Monaco, 'Courier New', monospace;"
        )
        ctrl_row.addWidget(self.lbl_info)

        layout.addLayout(ctrl_row)


# 3. Telemetry Sidebar (Scrollable Cards + "Show More" Entity Tree)


class TelemetrySidebar(QScrollArea):
    """
    Scrollable inspector sidebar showing full decoded telemetry data for the current frame.
    Includes an expandable accordion tree for dynamic entities.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.header: EpisodeHeader | None = None
        self.setWidgetResizable(True)
        self.setMinimumWidth(380)
        self.setStyleSheet("""
            QScrollArea { background-color: #0f1117; border: none; }
            QWidget#SidebarContent { background-color: #0f1117; }
            QFrame.Card {
                background-color: #171b26; border: 1px solid #283046; border-radius: 8px; margin-bottom: 6px; padding: 10px;
            }
            QLabel.CardTitle {
                color: #38bdf8; font-size: 13px; font-weight: bold; margin-bottom: 6px;
            }
            QLabel.FieldLabel {
                color: #94a3b8; font-size: 11px;
            }
            QLabel.FieldValue {
                color: #f1f5f9; font-size: 11px; font-family: Menlo, Monaco, 'Courier New', monospace;
            }
            QTreeWidget {
                background-color: #11141e; border: 1px solid #283046; border-radius: 6px; color: #f1f5f9; font-size: 11px;
            }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:hover { background-color: #1e2638; }
            QTreeWidget::item:selected { background-color: #2563eb; }
        """)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("SidebarContent")
        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        self.setWidget(self.content_widget)

        self._build_header_card()
        self._build_knight_card()
        self._build_boss_card()
        self._build_inputs_card()
        self._build_entities_card()
        self.main_layout.addStretch()

    # Form Layout Helpers

    def _create_form(self) -> QFormLayout:
        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 4)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(4)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        return form

    def _add_form_row(
        self,
        form: QFormLayout,
        label_text: str,
        value_widget: QWidget,
    ):
        lbl = QLabel(label_text)
        lbl.setProperty("class", "FieldLabel")
        lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        if isinstance(value_widget, QLabel):
            value_widget.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value_widget.setWordWrap(True)
            value_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        form.addRow(lbl, value_widget)

    # Card Builders

    def _build_header_card(self):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)

        title = QLabel("EPISODE INFORMATION")
        title.setProperty("class", "CardTitle")
        layout.addWidget(title)

        form = self._create_form()
        self.lbl_ep_boss = QLabel("-")
        self.lbl_ep_boss.setProperty("class", "FieldValue")
        self._add_form_row(form, "Boss:", self.lbl_ep_boss)

        self.lbl_ep_diff = QLabel("-")
        self.lbl_ep_diff.setProperty("class", "FieldValue")
        self._add_form_row(form, "Difficulty:", self.lbl_ep_diff)

        self.lbl_ep_nail = QLabel("-")
        self.lbl_ep_nail.setProperty("class", "FieldValue")
        self._add_form_row(form, "Nail Damage:", self.lbl_ep_nail)

        self.lbl_ep_masks = QLabel("-")
        self.lbl_ep_masks.setProperty("class", "FieldValue")
        self._add_form_row(form, "Max Masks:", self.lbl_ep_masks)

        layout.addLayout(form)
        self.main_layout.addWidget(card)

    def _build_knight_card(self):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)

        title = QLabel("KNIGHT STATUS")
        title.setProperty("class", "CardTitle")
        layout.addWidget(title)

        form = self._create_form()
        self.lbl_k_hp = QLabel("-")
        self.lbl_k_hp.setProperty("class", "FieldValue")
        self._add_form_row(form, "Health (HP):", self.lbl_k_hp)

        self.lbl_k_mp = QLabel("-")
        self.lbl_k_mp.setProperty("class", "FieldValue")
        self._add_form_row(form, "Soul (MP):", self.lbl_k_mp)

        self.lbl_k_pos = QLabel("-")
        self.lbl_k_pos.setProperty("class", "FieldValue")
        self._add_form_row(form, "Position (X, Y):", self.lbl_k_pos)

        self.lbl_k_vel = QLabel("-")
        self.lbl_k_vel.setProperty("class", "FieldValue")
        self._add_form_row(form, "Velocity (Vx, Vy):", self.lbl_k_vel)

        self.lbl_k_nail_cd = QLabel("-")
        self.lbl_k_nail_cd.setProperty("class", "FieldValue")
        self._add_form_row(form, "Nail CD:", self.lbl_k_nail_cd)

        self.lbl_k_dash_cd = QLabel("-")
        self.lbl_k_dash_cd.setProperty("class", "FieldValue")
        self._add_form_row(form, "Dash CD:", self.lbl_k_dash_cd)

        self.lbl_k_invuln = QLabel("-")
        self.lbl_k_invuln.setProperty("class", "FieldValue")
        self._add_form_row(form, "Invulnerability:", self.lbl_k_invuln)

        layout.addLayout(form)

        # Combat Flags Pills
        flags_lbl = QLabel("Combat Flags:")
        flags_lbl.setProperty("class", "FieldLabel")
        layout.addWidget(flags_lbl)
        self.lbl_k_flags = QLabel("-")
        self.lbl_k_flags.setWordWrap(True)
        self.lbl_k_flags.setStyleSheet(
            "color: #38bdf8; font-size: 10px; font-family: Menlo, Monaco, 'Courier New', monospace; padding-bottom: 2px;"
        )
        layout.addWidget(self.lbl_k_flags)

        self.main_layout.addWidget(card)

    def _build_boss_card(self):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)

        title = QLabel("BOSS STATUS")
        title.setProperty("class", "CardTitle")
        title.setStyleSheet("color: #f43f5e; font-weight: bold;")
        layout.addWidget(title)

        form = self._create_form()
        self.lbl_b_hp = QLabel("-")
        self.lbl_b_hp.setProperty("class", "FieldValue")
        self._add_form_row(form, "Health:", self.lbl_b_hp)

        self.lbl_b_fsm = QLabel("-")
        self.lbl_b_fsm.setProperty("class", "FieldValue")
        self.lbl_b_fsm.setStyleSheet(
            "color: #fca5a5; font-weight: bold; font-family: Menlo, Monaco, 'Courier New', monospace;"
        )
        self._add_form_row(form, "FSM State:", self.lbl_b_fsm)

        self.lbl_b_prev_fsm = QLabel("-")
        self.lbl_b_prev_fsm.setProperty("class", "FieldValue")
        self.lbl_b_prev_fsm.setStyleSheet(
            "color: #cbd5e1; font-family: Menlo, Monaco, 'Courier New', monospace;"
        )
        self._add_form_row(form, "Prev State:", self.lbl_b_prev_fsm)

        self.lbl_b_time = QLabel("-")
        self.lbl_b_time.setProperty("class", "FieldValue")
        self._add_form_row(form, "State Time:", self.lbl_b_time)

        self.lbl_b_pos = QLabel("-")
        self.lbl_b_pos.setProperty("class", "FieldValue")
        self._add_form_row(form, "Position (X, Y):", self.lbl_b_pos)

        self.lbl_b_vel = QLabel("-")
        self.lbl_b_vel.setProperty("class", "FieldValue")
        self._add_form_row(form, "Velocity (Vx, Vy):", self.lbl_b_vel)

        self.lbl_b_bounds = QLabel("-")
        self.lbl_b_bounds.setProperty("class", "FieldValue")
        self._add_form_row(form, "Bounds (W, H):", self.lbl_b_bounds)

        self.lbl_b_signals = QLabel("-")
        self.lbl_b_signals.setProperty("class", "FieldValue")
        self._add_form_row(form, "Frame Signals:", self.lbl_b_signals)

        layout.addLayout(form)
        self.main_layout.addWidget(card)

    def _build_inputs_card(self):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)

        title = QLabel("CONTROLLER INPUTS")
        title.setProperty("class", "CardTitle")
        title.setStyleSheet("color: #a78bfa; font-weight: bold;")
        layout.addWidget(title)

        form = self._create_form()
        self.lbl_in_held = QLabel("None")
        self.lbl_in_held.setStyleSheet(
            "color: #38bdf8; font-weight: bold; font-family: Menlo, Monaco, 'Courier New', monospace;"
        )
        self._add_form_row(form, "Held (Down):", self.lbl_in_held)

        self.lbl_in_pressed = QLabel("None")
        self.lbl_in_pressed.setStyleSheet(
            "color: #facc15; font-weight: bold; font-family: Menlo, Monaco, 'Courier New', monospace;"
        )
        self._add_form_row(form, "Pressed (Tap):", self.lbl_in_pressed)

        layout.addLayout(form)
        self.main_layout.addWidget(card)

    def _build_entities_card(self):
        card = QFrame()
        card.setProperty("class", "Card")
        layout = QVBoxLayout(card)

        # Header with entity count and toggle buttons
        hdr_row = QHBoxLayout()
        self.lbl_entities_title = QLabel("DYNAMIC ENTITIES (0)")
        self.lbl_entities_title.setProperty("class", "CardTitle")
        self.lbl_entities_title.setStyleSheet("color: #fb923c; font-weight: bold;")
        hdr_row.addWidget(self.lbl_entities_title)
        hdr_row.addStretch()

        self.btn_expand_all = QPushButton("Expand All")
        self.btn_expand_all.setStyleSheet("padding: 2px 6px; font-size: 10px;")
        self.btn_expand_all.setFocusPolicy(Qt.NoFocus)
        self.btn_collapse_all = QPushButton("Collapse")
        self.btn_collapse_all.setStyleSheet("padding: 2px 6px; font-size: 10px;")
        self.btn_collapse_all.setFocusPolicy(Qt.NoFocus)
        hdr_row.addWidget(self.btn_expand_all)
        hdr_row.addWidget(self.btn_collapse_all)
        layout.addLayout(hdr_row)

        # Collapsible Tree Widget ("Show More" accordion style)
        self.tree_entities = QTreeWidget()
        self.tree_entities.setHeaderHidden(True)
        self.tree_entities.setMinimumHeight(220)
        self.tree_entities.setFocusPolicy(Qt.NoFocus)
        self.btn_expand_all.clicked.connect(self.tree_entities.expandAll)
        self.btn_collapse_all.clicked.connect(self.tree_entities.collapseAll)

        layout.addWidget(self.tree_entities)
        self.main_layout.addWidget(card)

    # Update Telemetry Display

    def update_header(self, header: EpisodeHeader):
        self.header = header
        self.lbl_ep_boss.setText(f"{header.boss_name} (ID: {header.boss_id})")
        self.lbl_ep_diff.setText(
            f"{header.difficulty_name} (Tier {header.boss_difficulty})"
        )
        self.lbl_ep_nail.setText(str(header.nail_damage))
        self.lbl_ep_masks.setText(str(header.max_health))

    def update_frame(self, frame: Frame):
        h = frame.header

        # 1. Knight Card
        max_hp = self.header.max_health if self.header else 9
        self.lbl_k_hp.setText(f"{h.knight_hp} / {max_hp}")
        self.lbl_k_mp.setText(f"{h.knight_mp} / 99 (+{h.knight_mp_reserve}v)")
        self.lbl_k_pos.setText(f"({h.knight_x:6.2f}, {h.knight_y:6.2f})")
        self.lbl_k_vel.setText(f"({h.knight_vx:5.2f}, {h.knight_vy:5.2f})")
        self.lbl_k_nail_cd.setText(f"{max(0.0, h.nail_cooldown):.2f}s")
        self.lbl_k_dash_cd.setText(f"{max(0.0, h.dash_cooldown):.2f}s")
        self.lbl_k_invuln.setText(f"{max(0.0, h.invuln_remaining):.2f}s")

        active_kflags = [
            fl.name
            for fl in KnightFlags
            if fl in h.knight_flags and fl != KnightFlags.NONE
        ]
        self.lbl_k_flags.setText(" | ".join(active_kflags) if active_kflags else "None")

        # 2. Boss Card
        self.lbl_b_hp.setText(f"{h.boss_hp} HP")
        state_name = get_fsm_state_name(h.boss_fsm_state)
        prev_state_name = get_fsm_state_name(h.prev_fsm_state)
        self.lbl_b_fsm.setText(state_name)
        self.lbl_b_prev_fsm.setText(prev_state_name)
        self.lbl_b_time.setText(f"{h.fsm_state_time:.2f}s")
        self.lbl_b_pos.setText(f"({h.boss_x:6.2f}, {h.boss_y:6.2f})")
        self.lbl_b_vel.setText(f"({h.boss_vx:5.2f}, {h.boss_vy:5.2f})")
        self.lbl_b_bounds.setText(
            f"W: {h.boss_bound_width:.2f}, H: {h.boss_bound_height:.2f}"
        )

        active_bflags = [
            fl.name for fl in FrameFlags if fl in h.flags and fl != FrameFlags.NONE
        ]
        self.lbl_b_signals.setText(
            " | ".join(active_bflags) if active_bflags else "None"
        )

        # 3. Inputs Card
        held = [
            b.name
            for b in ActionButtons
            if b in h.action_held and b != ActionButtons.NONE
        ]
        pressed = [
            b.name
            for b in ActionButtons
            if b in h.action_pressed and b != ActionButtons.NONE
        ]
        self.lbl_in_held.setText(" | ".join(held) if held else "None")
        self.lbl_in_pressed.setText(" | ".join(pressed) if pressed else "None")

        # 4. Entities Accordion ("Show More" style)
        self._update_entities_tree(frame.entities)

    def _update_entities_tree(self, entities: list[EntityData]):
        self.lbl_entities_title.setText(f"DYNAMIC ENTITIES ({len(entities)})")
        self.tree_entities.clear()

        if not entities:
            item = QTreeWidgetItem(["(No active dynamic entities this frame)"])
            item.setForeground(0, QBrush(QColor("#64748b")))
            self.tree_entities.addTopLevelItem(item)
            return

        for idx, ent in enumerate(entities):
            damages = bool(ent.flags & EntityFlags.DAMAGES_KNIGHT)
            status_tag = (
                "DAMAGING" if damages else f"WARN (Telegraph: {ent.progress:.2f}s)"
            )

            # Top-Level Root Item (Summary)
            root = QTreeWidgetItem(
                [f"[#{idx}] {ent.kind.name} - ID: {ent.entity_id}  [{status_tag}]"]
            )
            if damages:
                root.setForeground(0, QBrush(QColor("#f97316")))
            else:
                root.setForeground(0, QBrush(QColor("#facc15")))
            root.setFont(0, QFont("Arial", 10, QFont.Bold))

            # Collapsible Child Items ("Show More" details)
            c1 = QTreeWidgetItem(
                [f"  Position:       X = {ent.x:6.2f}, Y = {ent.y:6.2f}"]
            )
            c2 = QTreeWidgetItem(
                [f"  Velocity:       Vx = {ent.vx:5.2f}, Vy = {ent.vy:5.2f}"]
            )
            c3 = QTreeWidgetItem(
                [
                    f"  Bounds:         Width = {ent.bound_width:.2f}, Height = {ent.bound_height:.2f}"
                ]
            )
            c4 = QTreeWidgetItem([f"  Rotation:       {ent.rotation:5.1f}°"])
            c5 = QTreeWidgetItem([f"  Progress:       {ent.progress:5.2f}s remaining"])
            c6 = QTreeWidgetItem([f"  Health:         {ent.hp} HP"])

            flag_desc = []
            if ent.flags & EntityFlags.FACING_RIGHT:
                flag_desc.append("FACING_RIGHT")
            if ent.flags & EntityFlags.INVULNERABLE:
                flag_desc.append("INVULNERABLE")
            if ent.flags & EntityFlags.DAMAGES_KNIGHT:
                flag_desc.append("DAMAGES_KNIGHT")
            c7 = QTreeWidgetItem(
                [f"  Flags:          {' | '.join(flag_desc) if flag_desc else 'None'}"]
            )

            for c in (c1, c2, c3, c4, c5, c6, c7):
                c.setForeground(0, QBrush(QColor("#cbd5e1")))
                root.addChild(c)

            self.tree_entities.addTopLevelItem(root)

        # Expand top-level roots by default so they're immediately visible
        self.tree_entities.expandAll()


# 4. Main Application Window


class TelemetryVisualizerWindow(QMainWindow):
    """
    Top-level application window containing Canvas, Timeline, and Sidebar.
    """

    def __init__(self, filepath: str | None = None):
        super().__init__()
        self.setWindowTitle("Hollow Knight Telemetry Visualizer")
        self.resize(1280, 800)

        self.frames: list[Frame] = []
        self.header: EpisodeHeader | None = None
        self.current_idx: int = 0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0

        # Synchronized 50 Hz timer (20 ms interval)
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(self._on_play_tick)

        self._build_ui()
        self._build_menu()

        # Global event filter to intercept navigation keys regardless of widget focus
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

        if filepath and os.path.exists(filepath):
            self.load_file(filepath)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Splitter dividing Left (Canvas + Timeline) and Right (Sidebar)
        splitter = QSplitter(Qt.Horizontal)

        # Left Container
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.canvas = ArenaCanvas()
        self.controls = TimelineControls()
        left_layout.addWidget(self.canvas, stretch=1)
        left_layout.addWidget(self.controls)

        splitter.addWidget(left_widget)

        # Right Container
        self.sidebar = TelemetrySidebar()
        splitter.addWidget(self.sidebar)

        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([840, 440])

        main_layout.addWidget(splitter)

        # Wire Timeline Events
        self.controls.slider.valueChanged.connect(self.set_frame_index)
        self.controls.btn_play.clicked.connect(self.toggle_play)
        self.controls.btn_step_back.clicked.connect(lambda: self.step_frame(-1))
        self.controls.btn_step_fwd.clicked.connect(lambda: self.step_frame(1))
        self.controls.btn_step_back_10.clicked.connect(lambda: self.step_frame(-10))
        self.controls.btn_step_fwd_10.clicked.connect(lambda: self.step_frame(10))
        self.controls.speed_combo.currentTextChanged.connect(self._on_speed_changed)

    def _build_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        act_open = QAction("Open Recording...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._on_open_dialog)
        file_menu.addAction(act_open)

        act_reset_cam = QAction("Reset Camera", self)
        act_reset_cam.setShortcut("R")
        act_reset_cam.triggered.connect(self.canvas.reset_camera)
        file_menu.addAction(act_reset_cam)

        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

    # Loading Episode

    def load_file(self, filepath: str):
        try:
            self.header, self.frames = EpisodeReader.read_file(filepath)
        except Exception as e:
            print(f"Error loading file: {e}", file=sys.stderr)
            return

        filename = os.path.basename(filepath)
        self.setWindowTitle(f"Hollow Knight Telemetry Visualizer - {filename}")

        self.controls.slider.setRange(0, max(0, len(self.frames) - 1))
        self.sidebar.update_header(self.header)

        self.current_idx = 0
        self.set_frame_index(0)

    def _on_open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Episode Recording",
            ".",
            "Binary Telemetry (*.bin);;All Files (*)",
        )
        if path:
            self.load_file(path)

    # Frame Navigation

    def set_frame_index(self, idx: int):
        if not self.frames:
            return

        idx = max(0, min(idx, len(self.frames) - 1))
        self.current_idx = idx

        # Block slider signal to prevent recursion
        self.controls.slider.blockSignals(True)
        self.controls.slider.setValue(idx)
        self.controls.slider.blockSignals(False)

        frame = self.frames[idx]
        t_sec = frame.header.frame_id * 0.02
        self.controls.lbl_info.setText(
            f"Frame: {idx} / {len(self.frames) - 1} ({t_sec:.2f}s)"
        )

        self.canvas.set_frame(frame, self.header)
        self.sidebar.update_frame(frame)

    def step_frame(self, delta: int):
        if not self.frames:
            return
        new_idx = self.current_idx + delta
        if new_idx >= len(self.frames):
            if self.controls.chk_loop.isChecked():
                new_idx = 0
            else:
                new_idx = len(self.frames) - 1
                if self.is_playing:
                    self.toggle_play()
        elif new_idx < 0:
            new_idx = 0

        self.set_frame_index(new_idx)

    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.controls.btn_play.setText("⏸ Pause")
            interval_ms = int(20.0 / self.playback_speed)
            self.play_timer.start(interval_ms)
        else:
            self.controls.btn_play.setText("▶ Play")
            self.play_timer.stop()

    def _on_play_tick(self):
        self.step_frame(1)

    def _on_speed_changed(self, text: str):
        speed_map = {"0.25x": 0.25, "0.5x": 0.5, "1.0x": 1.0, "2.0x": 2.0, "4.0x": 4.0}
        self.playback_speed = speed_map.get(text, 1.0)
        if self.is_playing:
            interval_ms = max(1, int(20.0 / self.playback_speed))
            self.play_timer.start(interval_ms)

    # Global Keyboard Shortcuts & Event Filter

    def eventFilter(self, watched, event):
        if event.type() == QEvent.KeyPress:
            key = event.key()
            modifiers = event.modifiers()

            if key == Qt.Key_Space:
                self.toggle_play()
                return True
            elif key == Qt.Key_Left:
                step = -10 if (modifiers & Qt.ShiftModifier) else -1
                self.step_frame(step)
                return True
            elif key == Qt.Key_Right:
                step = 10 if (modifiers & Qt.ShiftModifier) else 1
                self.step_frame(step)
                return True
            elif key == Qt.Key_Home:
                self.set_frame_index(0)
                return True
            elif key == Qt.Key_End:
                if self.frames:
                    self.set_frame_index(len(self.frames) - 1)
                return True
            elif key == Qt.Key_R:
                self.canvas.reset_camera()
                return True

        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key_Space:
            self.toggle_play()
        elif key == Qt.Key_Left:
            step = -10 if (modifiers & Qt.ShiftModifier) else -1
            self.step_frame(step)
        elif key == Qt.Key_Right:
            step = 10 if (modifiers & Qt.ShiftModifier) else 1
            self.step_frame(step)
        elif key == Qt.Key_Home:
            self.set_frame_index(0)
        elif key == Qt.Key_End:
            if self.frames:
                self.set_frame_index(len(self.frames) - 1)
        elif key == Qt.Key_R:
            self.canvas.reset_camera()
        else:
            super().keyPressEvent(event)


# 5. CLI Entrypoint


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Hollow Knight Telemetry Visualizer (Qt6)"
    )
    parser.add_argument(
        "filepath", nargs="?", default=None, help="Path to .bin episode recording"
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Helvetica Neue", 10))

    # Dark Theme Palette
    app.setStyleSheet("""
        QMainWindow { background-color: #0b0d13; }
        QToolTip { color: #ffffff; background-color: #1e293b; border: 1px solid #334155; }
    """)

    window = TelemetryVisualizerWindow(filepath=args.filepath)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
