"""Interface grafica com rosto animado simulando a assistente virtual Lucy."""

import math
import random
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from .commands import CommandProcessor, CommandResult
from .config import LanguageProfile, get_profile
from .voice import VoiceEngine


STATE_COLORS = {
    "idle": QtGui.QColor("#38bdf8"),       # Azul ciano calmo
    "listening": QtGui.QColor("#22d3ee"),  # Ciano neon atento
    "processing": QtGui.QColor("#a78bfa"), # Violeta processando
    "speaking": QtGui.QColor("#34d399"),   # Verde esmeralda falando
    "error": QtGui.QColor("#f87171"),      # Coral alerta
}


class VoiceBridge(QtCore.QObject):
    """Ponte thread-safe entre o motor de voz em background e a interface Qt."""

    state_changed = QtCore.Signal(str, str)
    audio_level_changed = QtCore.Signal(float)
    partial_text_received = QtCore.Signal(str)
    command_result_received = QtCore.Signal(object)
    voice_unavailable = QtCore.Signal(str)


class LucyFaceWidget(QtWidgets.QWidget):
    """Widget customizado que desenha e anima o rosto holografico da Lucy."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 300)
        self.setMouseTracking(True)

        self._state = "idle"
        self._phase = 0.0
        self._audio_level = 0.0
        self._smooth_level = 0.0

        # Olhos e piscada
        self._blink_progress = 0.0
        self._is_blinking = False
        self._blink_closing = True
        self._target_gaze = QtCore.QPointF(0.0, 0.0)
        self._current_gaze = QtCore.QPointF(0.0, 0.0)

        # Animacao de fala simulada quando Lucy responde
        self._speaking_ticks = 0

        # Cor interpolada
        self._current_color = QtGui.QColor(STATE_COLORS["idle"])

        # Timer principal a ~60 FPS
        self._anim_timer = QtCore.QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start(16)

        # Timer de piscada natural
        self._blink_timer = QtCore.QTimer(self)
        self._blink_timer.timeout.connect(self._start_blink)
        self._blink_timer.start(3200)

    def set_state(self, state: str) -> None:
        if state in STATE_COLORS:
            self._state = state
            if state == "speaking":
                self._speaking_ticks = 75  # ~1.2s de animacao labial

    def trigger_speaking(self, duration_ticks: int = 75) -> None:
        self._state = "speaking"
        self._speaking_ticks = duration_ticks

    def set_audio_level(self, level: float) -> None:
        self._audio_level = max(0.0, min(1.0, level))

    def _start_blink(self) -> None:
        if not self._is_blinking:
            self._is_blinking = True
            self._blink_closing = True
        self._blink_timer.setInterval(random.randint(2400, 5200))

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        w = max(1, self.width())
        h = max(1, self.height())
        nx = (event.position().x() / w - 0.5) * 2.0
        ny = (event.position().y() / h - 0.5) * 2.0
        self._target_gaze = QtCore.QPointF(
            max(-1.0, min(1.0, nx)),
            max(-1.0, min(1.0, ny)),
        )
        super().mouseMoveEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._target_gaze = QtCore.QPointF(0.0, 0.0)
        super().leaveEvent(event)

    def _on_tick(self) -> None:
        speed = 0.045 if self._state in ("listening", "processing", "speaking") else 0.022
        self._phase += speed

        # Retorno automatico de speaking/error para idle
        if self._speaking_ticks > 0:
            self._speaking_ticks -= 1
            if self._speaking_ticks == 0 and self._state == "speaking":
                self._state = "idle"

        # Suavizacao de nivel de audio
        target_level = self._audio_level
        if self._state == "speaking" and self._speaking_ticks > 0:
            target_level = max(
                target_level,
                0.35 + 0.35 * abs(math.sin(self._phase * 6.5)) * abs(math.cos(self._phase * 2.7)),
            )
        self._smooth_level += (target_level - self._smooth_level) * 0.25

        # Suavizacao de olhar
        if self._target_gaze.isNull() and self._state == "idle":
            idle_x = math.sin(self._phase * 0.6) * 0.15
            idle_y = math.cos(self._phase * 0.4) * 0.08
            desired = QtCore.QPointF(idle_x, idle_y)
        else:
            desired = self._target_gaze
        self._current_gaze += (desired - self._current_gaze) * 0.12

        # Animacao da piscada
        if self._is_blinking:
            if self._blink_closing:
                self._blink_progress += 0.22
                if self._blink_progress >= 1.0:
                    self._blink_progress = 1.0
                    self._blink_closing = False
            else:
                self._blink_progress -= 0.18
                if self._blink_progress <= 0.0:
                    self._blink_progress = 0.0
                    self._is_blinking = False

        # Interpolacao suave de cor
        target_color = STATE_COLORS.get(self._state, STATE_COLORS["idle"])
        r = int(self._current_color.red() + (target_color.red() - self._current_color.red()) * 0.12)
        g = int(self._current_color.green() + (target_color.green() - self._current_color.green()) * 0.12)
        b = int(self._current_color.blue() + (target_color.blue() - self._current_color.blue()) * 0.12)
        self._current_color = QtGui.QColor(r, g, b)

        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0 + math.sin(self._phase) * 3.0  # Flutuacao suave
        scale = min(w, h) / 300.0

        accent = self._current_color

        # Fundo radial sutil atras do rosto
        bg_grad = QtGui.QRadialGradient(cx, cy, 165 * scale)
        bg_color = QtGui.QColor(accent)
        bg_color.setAlpha(38 + int(self._smooth_level * 45))
        bg_grad.setColorAt(0.0, bg_color)
        bg_grad.setColorAt(0.7, QtGui.QColor(15, 23, 42, 20))
        bg_grad.setColorAt(1.0, QtGui.QColor(15, 23, 42, 0))
        painter.setBrush(bg_grad)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy), 165 * scale, 165 * scale)

        # Aneis HUD rotativos ao redor do rosto
        self._draw_hud_rings(painter, cx, cy, scale, accent)

        # Contorno estilizado da cabeca / rosto
        self._draw_head_contour(painter, cx, cy, scale, accent)

        # Sobrancelhas e olhos
        eye_y = cy - 18 * scale
        eye_dx = 44 * scale
        self._draw_eye(painter, cx - eye_dx, eye_y, scale, accent, is_left=True)
        self._draw_eye(painter, cx + eye_dx, eye_y, scale, accent, is_left=False)

        # Nariz minimalista holografico
        nose_pen = QtGui.QPen(QtGui.QColor(accent.red(), accent.green(), accent.blue(), 90), 1.6 * scale)
        nose_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(nose_pen)
        painter.drawLine(
            QtCore.QPointF(cx, cy + 2 * scale),
            QtCore.QPointF(cx - 3 * scale, cy + 16 * scale),
        )
        painter.drawLine(
            QtCore.QPointF(cx - 3 * scale, cy + 16 * scale),
            QtCore.QPointF(cx + 3 * scale, cy + 17 * scale),
        )

        # Boca / Equalizador de voz
        self._draw_mouth(painter, cx, cy + 44 * scale, scale, accent)

        # Barras laterais reativas de audio
        self._draw_audio_bars(painter, cx, cy, scale, accent)

    def _draw_hud_rings(
        self,
        painter: QtGui.QPainter,
        cx: float,
        cy: float,
        scale: float,
        accent: QtGui.QColor,
    ) -> None:
        ring_radius = 128 * scale + self._smooth_level * 8 * scale
        rect = QtCore.QRectF(
            cx - ring_radius,
            cy - ring_radius,
            ring_radius * 2,
            ring_radius * 2,
        )

        pen_outer = QtGui.QPen(QtGui.QColor(accent.red(), accent.green(), accent.blue(), 85), 2.0 * scale)
        pen_outer.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_outer)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        base_angle = (self._phase * 28.0) % 360.0
        for i in range(4):
            start_deg = base_angle + i * 90.0 + 12.0
            painter.drawArc(rect, int(start_deg * 16), int(58 * 16))

        inner_r = 114 * scale
        inner_rect = QtCore.QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)
        pen_inner = QtGui.QPen(QtGui.QColor(accent.red(), accent.green(), accent.blue(), 45), 1.2 * scale)
        pen_inner.setStyle(QtCore.Qt.PenStyle.DashLine)
        painter.setPen(pen_inner)
        painter.drawEllipse(inner_rect)

    def _draw_head_contour(
        self,
        painter: QtGui.QPainter,
        cx: float,
        cy: float,
        scale: float,
        accent: QtGui.QColor,
    ) -> None:
        path = QtGui.QPainterPath()
        # Silhueta suave de rosto feminino futurista
        path.moveTo(cx, cy - 92 * scale)
        path.cubicTo(
            cx + 72 * scale, cy - 92 * scale,
            cx + 88 * scale, cy - 28 * scale,
            cx + 76 * scale, cy + 28 * scale,
        )
        path.cubicTo(
            cx + 62 * scale, cy + 72 * scale,
            cx + 26 * scale, cy + 94 * scale,
            cx, cy + 96 * scale,
        )
        path.cubicTo(
            cx - 26 * scale, cy + 94 * scale,
            cx - 62 * scale, cy + 72 * scale,
            cx - 76 * scale, cy + 28 * scale,
        )
        path.cubicTo(
            cx - 88 * scale, cy - 28 * scale,
            cx - 72 * scale, cy - 92 * scale,
            cx, cy - 92 * scale,
        )

        fill_grad = QtGui.QLinearGradient(cx, cy - 92 * scale, cx, cy + 96 * scale)
        fill_grad.setColorAt(0.0, QtGui.QColor(30, 41, 59, 195))
        fill_grad.setColorAt(1.0, QtGui.QColor(15, 23, 42, 225))
        painter.setBrush(fill_grad)

        contour_pen = QtGui.QPen(QtGui.QColor(accent.red(), accent.green(), accent.blue(), 175), 2.2 * scale)
        painter.setPen(contour_pen)
        painter.drawPath(path)

        # Detalhes tecnologicos nas temporas
        node_color = QtGui.QColor(accent.red(), accent.green(), accent.blue(), 190)
        painter.setBrush(node_color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for sign in (-1, 1):
            painter.drawEllipse(QtCore.QPointF(cx + sign * 80 * scale, cy - 12 * scale), 3.2 * scale, 3.2 * scale)

    def _draw_eye(
        self,
        painter: QtGui.QPainter,
        ex: float,
        ey: float,
        scale: float,
        accent: QtGui.QColor,
        is_left: bool,
    ) -> None:
        # Sobrancelha expressiva
        brow_offset_y = -24 * scale
        brow_tilt = 0.0
        if self._state == "listening":
            brow_offset_y -= 4 * scale
            brow_tilt = -3 * scale if is_left else 3 * scale
        elif self._state == "error":
            brow_offset_y += 3 * scale
            brow_tilt = 5 * scale if is_left else -5 * scale
        elif self._state == "speaking":
            brow_offset_y -= 2 * scale

        brow_pen = QtGui.QPen(QtGui.QColor(accent.red(), accent.green(), accent.blue(), 200), 2.4 * scale)
        brow_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(brow_pen)
        painter.drawLine(
            QtCore.QPointF(ex - 16 * scale, ey + brow_offset_y - brow_tilt * 0.4),
            QtCore.QPointF(ex + 16 * scale, ey + brow_offset_y + brow_tilt * 0.4),
        )

        # Abertura do olho considerando piscada e estado
        open_factor = max(0.06, 1.0 - self._blink_progress)
        if self._state == "listening":
            open_factor = min(1.15, open_factor * 1.1)

        eye_w = 34 * scale
        eye_h = 20 * scale * open_factor

        # Brilho suave atras do olho
        glow = QtGui.QRadialGradient(ex, ey, 26 * scale)
        glow_col = QtGui.QColor(accent)
        glow_col.setAlpha(95)
        glow.setColorAt(0.0, glow_col)
        glow.setColorAt(1.0, QtGui.QColor(accent.red(), accent.green(), accent.blue(), 0))
        painter.setBrush(glow)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(ex, ey), 26 * scale, 22 * scale)

        # Formato do olho
        eye_rect = QtCore.QRectF(ex - eye_w / 2.0, ey - eye_h / 2.0, eye_w, eye_h)
        eye_clip = QtGui.QPainterPath()
        eye_clip.addRoundedRect(eye_rect, eye_h / 2.0, eye_h / 2.0)

        painter.save()
        painter.setClipPath(eye_clip)

        painter.setBrush(QtGui.QColor(10, 15, 28))
        painter.drawRect(eye_rect)

        if open_factor > 0.18:
            gx = self._current_gaze.x() * 6.5 * scale
            gy = self._current_gaze.y() * 3.5 * scale
            iris_r = 9.0 * scale

            iris_grad = QtGui.QRadialGradient(ex + gx, ey + gy, iris_r)
            iris_grad.setColorAt(0.0, QtGui.QColor("#ffffff"))
            iris_grad.setColorAt(0.35, accent)
            iris_grad.setColorAt(1.0, QtGui.QColor(accent.red(), accent.green(), accent.blue(), 70))

            painter.setBrush(iris_grad)
            painter.drawEllipse(QtCore.QPointF(ex + gx, ey + gy), iris_r, iris_r)

            # Pupila
            painter.setBrush(QtGui.QColor(10, 18, 35))
            painter.drawEllipse(QtCore.QPointF(ex + gx, ey + gy), 3.4 * scale, 3.4 * scale)

            # Reflexo especular
            painter.setBrush(QtGui.QColor(255, 255, 255, 230))
            painter.drawEllipse(
                QtCore.QPointF(ex + gx - 3.0 * scale, ey + gy - 3.0 * scale),
                2.0 * scale,
                2.0 * scale,
            )

        painter.restore()

        # Contorno do olho
        eye_pen = QtGui.QPen(accent, 1.8 * scale)
        painter.setPen(eye_pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        painter.drawPath(eye_clip)

    def _draw_mouth(
        self,
        painter: QtGui.QPainter,
        mx: float,
        my: float,
        scale: float,
        accent: QtGui.QColor,
    ) -> None:
        mouth_w = 42 * scale
        open_h = self._smooth_level * 18 * scale

        if self._state == "error":
            curve = -7 * scale
        elif self._state == "listening":
            curve = 3 * scale
        else:
            curve = 8 * scale

        mouth_pen = QtGui.QPen(accent, 2.4 * scale)
        mouth_pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(mouth_pen)

        if open_h < 2.2 * scale:
            # Boca fechada com expressao suave
            path = QtGui.QPainterPath()
            path.moveTo(mx - mouth_w / 2.0, my)
            path.quadTo(mx, my + curve, mx + mouth_w / 2.0, my)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawPath(path)
        else:
            # Boca aberta animada por fala / nivel de audio
            path = QtGui.QPainterPath()
            path.moveTo(mx - mouth_w / 2.0, my)
            path.quadTo(mx, my - open_h * 0.45, mx + mouth_w / 2.0, my)
            path.quadTo(mx, my + open_h + curve * 0.5, mx - mouth_w / 2.0, my)

            fill = QtGui.QColor(accent.red(), accent.green(), accent.blue(), 85)
            painter.setBrush(fill)
            painter.drawPath(path)

    def _draw_audio_bars(
        self,
        painter: QtGui.QPainter,
        cx: float,
        cy: float,
        scale: float,
        accent: QtGui.QColor,
    ) -> None:
        num_bars = 7
        bar_w = 3.2 * scale
        gap = 5.5 * scale
        total_w = num_bars * bar_w + (num_bars - 1) * gap
        start_x = cx - total_w / 2.0
        base_y = cy + 122 * scale

        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        for i in range(num_bars):
            wave = abs(math.sin(self._phase * 3.5 + i * 0.8))
            amp = 3.0 * scale + (self._smooth_level * 18.0 * scale * wave)
            if self._state == "idle" and self._smooth_level < 0.05:
                amp = 3.0 * scale + 2.0 * scale * wave

            alpha = 110 + int(min(145, self._smooth_level * 145))
            painter.setBrush(QtGui.QColor(accent.red(), accent.green(), accent.blue(), alpha))
            bx = start_x + i * (bar_w + gap)
            rect = QtCore.QRectF(bx, base_y - amp / 2.0, bar_w, amp)
            painter.drawRoundedRect(rect, bar_w / 2.0, bar_w / 2.0)


class CommandsDialog(QtWidgets.QDialog):
    """Janela auxiliar listando todos os comandos suportados no idioma atual."""

    def __init__(self, profile: LanguageProfile, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Comandos Disponiveis - Lucy" if profile.code == "pt" else "Available Commands - Lucy")
        self.resize(480, 420)
        self.setStyleSheet(
            """
            QDialog { background-color: #0f172a; color: #e2e8f0; }
            QListWidget {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
            }
            QPushButton {
                background-color: #0284c7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0ea5e9; }
            """
        )

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel(
            f"Gatilhos: {', '.join(profile.wake_words)}"
            if profile.code == "pt"
            else f"Wake words: {', '.join(profile.wake_words)}"
        )
        title.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        list_widget = QtWidgets.QListWidget()
        for phrases in profile.commands_grouped.keys():
            list_widget.addItem(" / ".join(phrases))
        layout.addWidget(list_widget)

        close_btn = QtWidgets.QPushButton("Fechar" if profile.code == "pt" else "Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)


class LucyWindow(QtWidgets.QMainWindow):
    """Janela principal da assistente virtual Lucy."""

    def __init__(self, lang: str = "pt", model_path: Optional[str] = None) -> None:
        super().__init__()
        self.profile = get_profile(lang)
        self.custom_model_path = model_path
        self._voice_available = True
        self._muted = False
        self._drag_pos: Optional[QtCore.QPoint] = None

        self.setWindowTitle(self.profile.app_name)
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Window
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(440, 620)

        self.processor = CommandProcessor(
            self.profile,
            on_exit=self._request_close,
            notify=True,
        )

        self.bridge = VoiceBridge()
        self.bridge.state_changed.connect(self._on_voice_state)
        self.bridge.audio_level_changed.connect(self._on_audio_level)
        self.bridge.partial_text_received.connect(self._on_partial_text)
        self.bridge.command_result_received.connect(self._on_command_result)
        self.bridge.voice_unavailable.connect(self._on_voice_unavailable)

        self.voice_engine: Optional[VoiceEngine] = None

        self._build_ui()
        self._start_voice_engine()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        outer_layout = QtWidgets.QVBoxLayout(central)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QtWidgets.QFrame()
        self.card.setObjectName("MainCard")
        self.card.setStyleSheet(
            """
            QFrame#MainCard {
                background-color: #0b1120;
                border: 1px solid #1e293b;
                border-radius: 18px;
            }
            QLabel { color: #e2e8f0; }
            QLineEdit {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #38bdf8; }
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #38bdf8;
            }
            QPushButton#PrimaryBtn {
                background-color: #0284c7;
                border-color: #0ea5e9;
                color: #ffffff;
            }
            QPushButton#PrimaryBtn:hover {
                background-color: #0ea5e9;
            }
            QPushButton#CloseBtn:hover {
                background-color: #dc2626;
                border-color: #ef4444;
                color: #ffffff;
            }
            """
        )
        outer_layout.addWidget(self.card)

        layout = QtWidgets.QVBoxLayout(self.card)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)

        # Cabecalho arrastavel
        header = QtWidgets.QHBoxLayout()
        title_lbl = QtWidgets.QLabel("LUCY // ASSISTENTE VIRTUAL")
        title_lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        header.addWidget(title_lbl)
        header.addStretch()

        self.lang_btn = QtWidgets.QPushButton(self.profile.code.upper())
        self.lang_btn.setFixedWidth(48)
        self.lang_btn.setToolTip("Alternar idioma (PT/EN)")
        self.lang_btn.clicked.connect(self._toggle_language)
        header.addWidget(self.lang_btn)

        help_btn = QtWidgets.QPushButton("?")
        help_btn.setFixedWidth(34)
        help_btn.setToolTip("Listar comandos")
        help_btn.clicked.connect(self._show_help_dialog)
        header.addWidget(help_btn)

        min_btn = QtWidgets.QPushButton("_")
        min_btn.setFixedWidth(34)
        min_btn.clicked.connect(self.showMinimized)
        header.addWidget(min_btn)

        close_btn = QtWidgets.QPushButton("X")
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedWidth(34)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # Rosto animado da Lucy
        self.face_widget = LucyFaceWidget()
        layout.addWidget(self.face_widget, stretch=1)

        # Status atual
        self.status_label = QtWidgets.QLabel(self.profile.messages["listening_wake"])
        self.status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(
            "color: #94a3b8; font-size: 12px; font-weight: 600; padding: 2px 6px;"
        )
        layout.addWidget(self.status_label)

        # Balao de dialogo / resposta
        self.dialog_box = QtWidgets.QLabel(
            "Ola! Diga 'Lucy' ou digite um comando abaixo."
            if self.profile.code == "pt"
            else "Hello! Say 'Lucy' or type a command below."
        )
        self.dialog_box.setWordWrap(True)
        self.dialog_box.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.dialog_box.setMinimumHeight(56)
        self.dialog_box.setStyleSheet(
            """
            background-color: #111c33;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 10px;
            color: #e2e8f0;
            font-size: 13px;
            """
        )
        layout.addWidget(self.dialog_box)

        # Barra de entrada de texto
        input_row = QtWidgets.QHBoxLayout()
        self.cmd_input = QtWidgets.QLineEdit()
        self.cmd_input.setPlaceholderText(
            "Digite um comando (ex: abrir terminal, ajuda)..."
            if self.profile.code == "pt"
            else "Type a command (e.g. open terminal, help)..."
        )
        self.cmd_input.returnPressed.connect(self._submit_text_command)
        input_row.addWidget(self.cmd_input, stretch=1)

        send_btn = QtWidgets.QPushButton("Enviar" if self.profile.code == "pt" else "Send")
        send_btn.setObjectName("PrimaryBtn")
        send_btn.clicked.connect(self._submit_text_command)
        input_row.addWidget(send_btn)
        self.send_btn = send_btn
        layout.addLayout(input_row)

        # Botoes de controle de voz
        controls_row = QtWidgets.QHBoxLayout()
        self.listen_btn = QtWidgets.QPushButton("Ouvir Agora" if self.profile.code == "pt" else "Listen Now")
        self.listen_btn.setObjectName("PrimaryBtn")
        self.listen_btn.clicked.connect(self._on_listen_now)
        controls_row.addWidget(self.listen_btn)

        self.mute_btn = QtWidgets.QPushButton("Silenciar Mic" if self.profile.code == "pt" else "Mute Mic")
        self.mute_btn.clicked.connect(self._toggle_mute)
        controls_row.addWidget(self.mute_btn)

        layout.addLayout(controls_row)

    def _start_voice_engine(self) -> None:
        if self.voice_engine:
            self.voice_engine.stop()

        self._voice_available = True
        self.listen_btn.setEnabled(True)
        self.mute_btn.setEnabled(True)

        self.voice_engine = VoiceEngine(
            profile=self.profile,
            processor=self.processor,
            model_path=self.custom_model_path,
            on_state_change=lambda s, m: self.bridge.state_changed.emit(s, m),
            on_audio_level=lambda lvl: self.bridge.audio_level_changed.emit(lvl),
            on_partial_text=lambda txt: self.bridge.partial_text_received.emit(txt),
            on_command_result=lambda res: self.bridge.command_result_received.emit(res),
            on_unavailable=lambda reason: self.bridge.voice_unavailable.emit(reason),
        )
        self.voice_engine.start()

    @QtCore.Slot(str, str)
    def _on_voice_state(self, state: str, message: str) -> None:
        self.face_widget.set_state(state)
        self.status_label.setText(message)

    @QtCore.Slot(float)
    def _on_audio_level(self, level: float) -> None:
        self.face_widget.set_audio_level(level)

    @QtCore.Slot(str)
    def _on_partial_text(self, text: str) -> None:
        self.status_label.setText(f"... {text}")

    @QtCore.Slot(object)
    def _on_command_result(self, result: CommandResult) -> None:
        if result.recognized:
            self.face_widget.trigger_speaking()
            self.dialog_box.setText(
                f"{result.reply}\n[{result.matched_phrase} - {result.confidence:.0f}%]"
            )
        else:
            self.face_widget.set_state("error")
            self.dialog_box.setText(result.reply)
            QtCore.QTimer.singleShot(1400, lambda: self.face_widget.set_state("idle"))

    @QtCore.Slot(str)
    def _on_voice_unavailable(self, reason: str) -> None:
        self._voice_available = False
        self.listen_btn.setEnabled(False)
        self.mute_btn.setEnabled(False)
        self.face_widget.set_state("idle")
        self.status_label.setText(self.profile.messages["text_only"])
        self.dialog_box.setText(reason)

    def _submit_text_command(self) -> None:
        text = self.cmd_input.text().strip()
        if not text:
            return
        self.cmd_input.clear()
        result = self.processor.process(text)
        self._on_command_result(result)

    def _on_listen_now(self) -> None:
        if self.voice_engine and self._voice_available:
            self.voice_engine.trigger_command_mode()

    def _toggle_mute(self) -> None:
        if not self.voice_engine or not self._voice_available:
            return
        self._muted = not self._muted
        self.voice_engine.set_muted(self._muted)
        if self.profile.code == "pt":
            self.mute_btn.setText("Ativar Mic" if self._muted else "Silenciar Mic")
        else:
            self.mute_btn.setText("Unmute Mic" if self._muted else "Mute Mic")

    def _toggle_language(self) -> None:
        next_lang = "en" if self.profile.code == "pt" else "pt"
        self.profile = get_profile(next_lang)
        self.processor.set_profile(self.profile)
        self.lang_btn.setText(self.profile.code.upper())
        self.setWindowTitle(self.profile.app_name)

        if self.profile.code == "pt":
            self.cmd_input.setPlaceholderText("Digite um comando (ex: abrir terminal, ajuda)...")
            self.send_btn.setText("Enviar")
            self.listen_btn.setText("Ouvir Agora")
            self.mute_btn.setText("Ativar Mic" if self._muted else "Silenciar Mic")
        else:
            self.cmd_input.setPlaceholderText("Type a command (e.g. open terminal, help)...")
            self.send_btn.setText("Send")
            self.listen_btn.setText("Listen Now")
            self.mute_btn.setText("Unmute Mic" if self._muted else "Mute Mic")

        self._start_voice_engine()

    def _show_help_dialog(self) -> None:
        dlg = CommandsDialog(self.profile, self)
        dlg.exec()

    def _request_close(self) -> None:
        QtCore.QTimer.singleShot(400, self.close)

    # Suporte para arrastar a janela sem bordas
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_pos is not None and event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.voice_engine:
            self.voice_engine.stop()
        super().closeEvent(event)


def run_gui(lang: str = "pt", model_path: Optional[str] = None) -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = LucyWindow(lang=lang, model_path=model_path)
    window.show()
    return app.exec()
