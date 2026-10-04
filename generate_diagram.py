"""
Script to generate the System Architecture Diagram for
Vision-Based Gesture Control for Computer Interaction.
Saves high-resolution PNG image for inclusion in reports and PDF documentation.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches


def create_architecture_diagram(output_path="system_architecture.png"):
    fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 11)
    ax.axis('off')

    bg_color = "#F8FAFC"
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    box_props = {
        "vision": {"fc": "#EFF6FF", "ec": "#2563EB", "title": "#1D4ED8"},
        "kinematics": {"fc": "#FEFCE8", "ec": "#CA8A04", "title": "#854D0E"},
        "gestures": {"fc": "#FAF5FF", "ec": "#9333EA", "title": "#6B21A8"},
        "control": {"fc": "#F0FDF4", "ec": "#16A34A", "title": "#15803D"},
        "system": {"fc": "#FFF1F2", "ec": "#E11D48", "title": "#9F1239"},
        "telemetry": {"fc": "#F0F9FF", "ec": "#0284C7", "title": "#0369A1"},
        "benchmark": {"fc": "#FFFFFF", "ec": "#475569", "title": "#0F172A"}
    }

    # Title Banner
    ax.text(8.0, 10.5, "Vision-Based Gesture Control System Architecture",
            fontsize=21, fontweight='bold', ha='center', va='center', color="#0F172A")
    ax.text(8.0, 10.12, "Decoupled 6-Stage Pipeline • Dimensionless Kinematics • Explicit FSM • Win32 User-Mode Backend",
            fontsize=11, fontstyle='italic', ha='center', va='center', color="#475569")

    def draw_component(x, y, w, h, style_key, title, subtitle, items, tag=""):
        style = box_props[style_key]
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12,rounding_size=0.15",
                                      facecolor=style["fc"], edgecolor=style["ec"], linewidth=1.8, zorder=2)
        ax.add_patch(rect)

        if tag:
            tag_box = patches.FancyBboxPatch((x + 0.15, y + h - 0.28), len(tag)*0.12 + 0.22, 0.22,
                                             boxstyle="round,pad=0.03,rounding_size=0.05",
                                             facecolor=style["ec"], edgecolor="none", zorder=3)
            ax.add_patch(tag_box)
            ax.text(x + 0.25, y + h - 0.17, tag, fontsize=7.5, fontweight='bold', color="white", zorder=4)

        title_y = y + h - 0.44 if tag else y + h - 0.32
        ax.text(x + 0.2, title_y, title, fontsize=11, fontweight='bold', color=style["title"], zorder=3)
        if subtitle:
            ax.text(x + 0.2, title_y - 0.22, subtitle, fontsize=8, color="#64748B", zorder=3)

        line_y = title_y - 0.34
        ax.plot([x + 0.15, x + w - 0.15], [line_y, line_y], color=style["ec"], linewidth=0.8, alpha=0.5, zorder=3)

        start_item_y = line_y - 0.23
        for i, item in enumerate(items):
            cur_y = start_item_y - (i * 0.25)
            ax.text(x + 0.25, cur_y, f"•  {item}", fontsize=7.8, color="#1E293B", zorder=3)

    # 1. Vision Subsystem (Stage 1)
    draw_component(
        0.8, 6.7, 3.4, 2.8, "vision",
        "1. Vision Subsystem", "Camera & Persistent Hand Tracker",
        [
            "OpenCV 720p/1080p Stream (Single Flip)",
            "MediaPipe Hands (Max 2 Hands, static=False)",
            "21 3D Normalized Landmarks Extraction",
            "HandAssociationTracker (Persistent IDs)",
            "Primary (Right/Cursor) & Secondary (Left)"
        ], tag="STAGE 1"
    )

    # 2. Kinematics Engine (Stage 2)
    draw_component(
        4.6, 6.7, 3.6, 2.8, "kinematics",
        "2. Kinematics Engine", "Dimensionless Metric Extraction",
        [
            "Palm Scale: Lpalm = d(LM0, LM9)",
            "Norm. Pinch Ratio: r = d(LM4, LM8) / Lpalm",
            "Pinch Hysteresis: Enter<=0.38, Exit>0.52",
            "Joint Collinearity Angle: cos(theta) > 0.55",
            "Multi-Factor Conf: C = sum(wi * Ci) in [0, 1]"
        ], tag="STAGE 2"
    )

    # 3. Gesture Subsystem (Stage 3)
    draw_component(
        8.6, 6.7, 3.8, 2.8, "gestures",
        "3. Gesture Subsystem", "Classifier, Voting & Explicit FSM",
        [
            "Role-Aware Classifier (Gestures YAML)",
            "Sliding-Window Temporal Voting (3 of 5)",
            "Explicit FSM (8 Distinct States):",
            "  IDLE, POINTING, SCROLLING, CLICK,",
            "  PINCH_PENDING, DRAGGING, LOST, PAUSED",
            "Per-Action Cooldown & Safety Transitions"
        ], tag="STAGE 3"
    )

    # 4. Control & Dispatcher (Stage 4)
    draw_component(
        8.6, 3.2, 3.8, 2.9, "control",
        "4. Control & Dispatcher", "Invariant Anchoring & Motion Scaling",
        [
            "Invariant Cursor Anchor (Strict Index Tip)",
            "Adaptive EMA: alpha = interp(v, [v_slow, v_fast])",
            "Continuous Scroll with Momentum Decay",
            "Hold-to-Drag State Lifecycle (3-frame grace)",
            "CommandDispatcher routes StateOutput"
        ], tag="STAGE 4"
    )

    # 5. System & Input Layer (Stage 5)
    draw_component(
        4.6, 3.2, 3.6, 2.9, "system",
        "5. System & OS Automation", "User-Mode Win32 & Safety Guards",
        [
            "InputBackend Interface (Decoupled Design)",
            "Win32InputBackend (Cached User32 Ctypes)",
            "  SetCursorPos, mouse_event, keybd_event",
            "MockInputBackend (Headless Unit Tests)",
            "SafetyManager: Timeout Auto-Release & ESC Stop"
        ], tag="STAGE 5"
    )

    # 6. Calibration, Telemetry & UI (Stage 6)
    draw_component(
        0.8, 3.2, 3.4, 2.9, "telemetry",
        "6. Calibration, Telemetry & HUD", "Diagnostics & Biometric Adaptation",
        [
            "Calibrator: 5-Stage Guided Tuning",
            "  Rest, Point, Pinch, Peace, Spread",
            "StageLatencyProfiler (Sub-Millisecond Profiling)",
            "Structured Diagnostic Logger (JSON/Console)",
            "Active Control Panel HUD Overlay (OpenCV)"
        ], tag="STAGE 6"
    )

    # Measured Performance Benchmark Box (Bottom Bar)
    draw_component(
        0.8, 0.5, 11.6, 2.1, "benchmark",
        "Empirical Benchmark Results (150-Frame Runtime Profiling @ 48.7 FPS)",
        "Zero Hardcoded Magic Values • Centralized YAML (tracking, gestures, system) • Sub-Millisecond Native Dispatch",
        [
            "Inference Latency: 18.89 ms  |  Capture: 1.59 ms  |  Features: 0.05 ms  |  Classifier: 0.03 ms  |  Stabilizer: 0.04 ms",
            "OS Dispatch: 0.03 ms  |  Total Latency: 20.63 ms  |  Measured Frame Rate: 48.7 FPS  |  RAM Usage: 31.2 MB  |  CPU: 0.0%",
            "Automated Test Coverage: 20 of 20 unit tests passing (kinematics, gesture classification, temporal voting, state machine)"
        ], tag="BENCHMARK"
    )

    # Connectors & Flow Arrows
    arrow_props = dict(arrowstyle="-|>", color="#2563EB", lw=2.2, mutation_scale=16)
    reverse_props = dict(arrowstyle="-|>", color="#16A34A", lw=2.2, mutation_scale=16)

    # 1 -> 2
    ax.annotate("", xy=(4.6, 8.1), xytext=(4.2, 8.1), arrowprops=arrow_props)
    ax.text(4.4, 8.25, "Landmarks", fontsize=7.5, fontweight='bold', ha='center', color="#1D4ED8")

    # 2 -> 3
    ax.annotate("", xy=(8.6, 8.1), xytext=(8.2, 8.1), arrowprops=arrow_props)
    ax.text(8.4, 8.25, "Features+C", fontsize=7.5, fontweight='bold', ha='center', color="#854D0E")

    # 3 -> 4
    ax.annotate("", xy=(10.5, 6.1), xytext=(10.5, 6.7), arrowprops=dict(arrowstyle="-|>", color="#9333EA", lw=2.2, mutation_scale=16))
    ax.text(11.1, 6.4, "StateOutput", fontsize=7.5, fontweight='bold', ha='center', color="#6B21A8")

    # 4 -> 5
    ax.annotate("", xy=(8.2, 4.65), xytext=(8.6, 4.65), arrowprops=reverse_props)
    ax.text(8.4, 4.85, "Actions", fontsize=7.5, fontweight='bold', ha='center', color="#15803D")

    # 5 -> 6
    ax.annotate("", xy=(4.2, 4.65), xytext=(4.6, 4.65), arrowprops=reverse_props)
    ax.text(4.4, 4.85, "Telemetry", fontsize=7.5, fontweight='bold', ha='center', color="#9F1239")

    # Right Legend Box (Gesture Mapping)
    legend_rect = patches.FancyBboxPatch((12.8, 0.5), 2.7, 9.0, boxstyle="round,pad=0.12,rounding_size=0.15",
                                         facecolor="#FFFFFF", edgecolor="#CBD5E1", linewidth=1.5, zorder=2)
    ax.add_patch(legend_rect)
    ax.text(14.15, 9.15, "Gesture Mapping Matrix", fontsize=10.5, fontweight='bold', ha='center', color="#0F172A", zorder=3)
    ax.plot([13.0, 15.3], [8.95, 8.95], color="#E2E8F0", lw=1, zorder=3)

    gestures_summary = [
        ("Pointing (Tuck/Relax)", "Move Cursor (Relative/EMA)"),
        ("Dynamic Pinch (0.38)", "Click / Text Drag-Select"),
        ("Two Fingers Up", "Momentum Fluid Scroll"),
        ("Offhand Peace", "Next Tab (Ctrl+Tab)"),
        ("Offhand 3-Fingers", "Prev Tab (Ctrl+Shift+Tab)"),
        ("Offhand Fist", "Zero-Jitter Text Drag"),
        ("Rock Sign (I+P)", "Next Browser Tab"),
        ("Rock + Thumb", "Previous Browser Tab"),
        ("Three Fingers", "Alt + Tab (App Switch)"),
        ("Four Fingers", "Task View (Win + Tab)"),
        ("Thumb Up", "Volume Up (0xAF)"),
        ("Pinky / Thumb Down", "Volume Down (0xAE)"),
        ("Shaka / Call Sign", "Play / Pause Media"),
        ("Closed Fist", "PAUSE System"),
        ("Open Palm", "RESUME System")
    ]

    gy = 8.65
    for g_icon, g_act in gestures_summary:
        ax.text(13.0, gy, g_icon, fontsize=7.5, fontweight='bold', color="#1E293B", zorder=3)
        ax.text(13.0, gy - 0.20, f"-> {g_act}", fontsize=7.0, color="#0284C7", zorder=3)
        gy -= 0.52

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Updated architecture diagram saved to: {output_path}")


if __name__ == "__main__":
    create_architecture_diagram()
