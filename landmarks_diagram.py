"""
Script to generate 21 MediaPipe Hand Landmark Reference diagram.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches


def create_landmarks_diagram(output_path="landmarks_reference.png"):
    fig, ax = plt.subplots(figsize=(12, 9), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    ax.axis('off')

    fig.patch.set_facecolor("#F8FAFC")
    ax.set_facecolor("#F8FAFC")

    # Title
    ax.text(6.0, 9.6, "MediaPipe 21 Hand Landmark Topology & Feature Reference",
            fontsize=17, fontweight='bold', ha='center', color="#0F172A")
    ax.text(6.0, 9.2, "Normalized Dimensionless Kinematics, Palm Scale Baseline & Joint Angle Vectors",
            fontsize=10, fontstyle='italic', ha='center', color="#475569")

    # Landmark coordinates approximate hand skeleton layout
    pts = {
        0: (4.8, 1.8),   # Wrist
        # Thumb
        1: (3.6, 2.6),   # Thumb CMC
        2: (2.8, 3.7),   # Thumb MCP
        3: (2.3, 4.8),   # Thumb IP
        4: (1.8, 5.8),   # Thumb Tip
        # Index
        5: (3.8, 4.8),   # Index MCP
        6: (3.6, 6.2),   # Index PIP
        7: (3.5, 7.3),   # Index DIP
        8: (3.4, 8.4),   # Index Tip
        # Middle
        9: (4.8, 4.9),   # Middle MCP
        10: (4.8, 6.4),  # Middle PIP
        11: (4.8, 7.6),  # Middle DIP
        12: (4.8, 8.7),  # Middle Tip
        # Ring
        13: (5.8, 4.7),  # Ring MCP
        14: (5.9, 6.1),  # Ring PIP
        15: (6.0, 7.2),  # Ring DIP
        16: (6.1, 8.2),  # Ring Tip
        # Pinky
        17: (6.7, 4.3),  # Pinky MCP
        18: (7.0, 5.4),  # Pinky PIP
        19: (7.2, 6.4),  # Pinky DIP
        20: (7.4, 7.3),  # Pinky Tip
    }

    # Connections
    connections = [
        # Palm & thumb
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12),
        (9, 13), (13, 14), (14, 15), (15, 16),
        (13, 17), (17, 18), (18, 19), (19, 20),
        (0, 17)
    ]

    # Draw connection bones
    for p1, p2 in connections:
        x1, y1 = pts[p1]
        x2, y2 = pts[p2]
        ax.plot([x1, x2], [y1, y2], color="#94A3B8", lw=3.2, zorder=2)

    # Color coding groups
    finger_colors = {
        "wrist": "#475569",
        "thumb": "#EF4444",
        "index": "#2563EB",
        "middle": "#10B981",
        "ring": "#F59E0B",
        "pinky": "#8B5CF6"
    }

    def get_color(idx):
        if idx == 0:
            return finger_colors["wrist"]
        if 1 <= idx <= 4:
            return finger_colors["thumb"]
        if 5 <= idx <= 8:
            return finger_colors["index"]
        if 9 <= idx <= 12:
            return finger_colors["middle"]
        if 13 <= idx <= 16:
            return finger_colors["ring"]
        return finger_colors["pinky"]

    # Plot landmark nodes
    for idx, (x, y) in pts.items():
        c = get_color(idx)
        ax.scatter(x, y, s=260, color=c, edgecolors="white", linewidth=2.2, zorder=4)
        ax.text(x, y, str(idx), fontsize=8, fontweight='bold', color="white",
                ha='center', va='center', zorder=5)

    # Feature 1: Palm Scale Baseline d(0, 9)
    x0, y0 = pts[0]
    x9, y9 = pts[9]
    ax.plot([x0, x9], [y0, y9], color="#0284C7", lw=2.8, linestyle="--", zorder=3)
    ax.text(5.05, 3.3, "Palm Scale Baseline: Lpalm = d(LM0, LM9)", fontsize=8,
            fontweight='bold', color="#0369A1", rotation=78, zorder=6)

    # Feature 2: Normalized Pinch Ratio d(4, 8) / Lpalm
    x4, y4 = pts[4]
    x8, y8 = pts[8]
    ax.plot([x4, x8], [y4, y8], color="#EC4899", lw=2.5, linestyle=":", zorder=3)
    ax.text((x4+x8)/2 - 0.4, (y4+y8)/2 + 0.35, "Norm. Pinch Ratio:\nr = d(4, 8) / Lpalm\nEnter<=0.38, Exit>0.52",
            fontsize=7.8, fontweight='bold', color="#BE185D", rotation=40, zorder=6)

    # Feature 3: Joint Collinearity Vector Annotation on Index
    x5, y5 = pts[5]
    x6, y6 = pts[6]
    x8, y8 = pts[8]
    ax.annotate("", xy=(x6, y6), xytext=(x5, y5),
                arrowprops=dict(arrowstyle="->", color="#1D4ED8", lw=1.5))
    ax.annotate("", xy=(x8, y8), xytext=(x6, y6),
                arrowprops=dict(arrowstyle="->", color="#1D4ED8", lw=1.5))
    ax.text(2.65, 7.0, "Joint Collinearity:\ncos(theta) = v1 · v2 > 0.55", fontsize=7.2,
            fontstyle='italic', color="#1E40AF", zorder=6)

    # Invariant Cursor Anchor Callout
    ax.scatter(pts[8][0], pts[8][1], s=420, facecolors='none', edgecolors='#EF4444', lw=2.5, linestyle='--', zorder=5)
    ax.text(pts[8][0] - 0.2, pts[8][1] + 0.45, "Invariant Anchor (LM8)", fontsize=8,
            fontweight='bold', color="#B91C1C", ha='right', zorder=6)

    # Right Legend & Landmark Roles Table
    leg_box = patches.FancyBboxPatch((8.3, 0.6), 3.4, 8.3, boxstyle="round,pad=0.12,rounding_size=0.12",
                                     facecolor="white", edgecolor="#CBD5E1", lw=1.2, zorder=2)
    ax.add_patch(leg_box)
    ax.text(10.0, 8.6, "Landmark Functional Roles", fontsize=10, fontweight='bold', ha='center', color="#0F172A")
    ax.plot([8.5, 11.5], [8.4, 8.4], color="#E2E8F0", lw=1)

    legend_items = [
        ("0", "WRIST", "Palm origin & extension baseline", finger_colors["wrist"]),
        ("1-3", "THUMB CMC/MCP/IP", "Thumb direction & opposition vector", finger_colors["thumb"]),
        ("4", "THUMB TIP", "Pinch ratio contact point", finger_colors["thumb"]),
        ("5-7", "INDEX MCP/PIP/DIP", "Collinearity alignment calculation", finger_colors["index"]),
        ("8", "INDEX TIP", "Invariant cursor anchor & pointer", finger_colors["index"]),
        ("9", "MIDDLE MCP", "Palm scale normalization reference", finger_colors["middle"]),
        ("10-12", "MIDDLE PIP/DIP/TIP", "Scroll tracking & peace sign recognition", finger_colors["middle"]),
        ("13-16", "RING MCP/PIP/TIP", "Alt+Tab (3-finger) detection", finger_colors["ring"]),
        ("17", "PINKY MCP", "Palm width boundary reference", finger_colors["pinky"]),
        ("18-20", "PINKY PIP/DIP/TIP", "Task View & Volume Down detection", finger_colors["pinky"])
    ]

    ly = 8.05
    for num, name, role, clr in legend_items:
        ax.scatter(8.6, ly, s=55, color=clr, edgecolors="none")
        ax.text(8.8, ly - 0.05, f"{num}: {name}", fontsize=7.2, fontweight='bold', color="#0F172A")
        ax.text(8.8, ly - 0.30, role, fontsize=6.5, color="#475569")
        ly -= 0.68

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"Landmarks reference diagram saved to: {output_path}")


if __name__ == "__main__":
    create_landmarks_diagram()
