"""
Brücken-Querschnitt SVG Generator
===================================
Erzeugt verschiedene Querschnittsprofile als SVG-Dateien.
Die Brücke ist:
  - Länge & Höhe des Querschnitts: L = 300mm, H = 15mm (fix vom Professor)
  - Belastung: 5kg in der Mitte
  - Maximale Durchbiegung: 3mm

Die SVGs kodieren den Querschnitt als schwarz=Material, weiß=Leer.
"""

import numpy as np
import os

# === Brückenparameter (müssen mit Simulation übereinstimmen) ===
H = 15.0    # Höhe der Brücke [mm]
L = 300.0   # Länge der Brücke [mm]

# === SVG Auflösung ===
SVG_W = 300   # Pixel
SVG_H = 15   # Pixel 
scale_x = SVG_W / L # geändert von B zu L 
scale_y = SVG_H / H

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge_svgs") # change to fit curent directory of this .py file
os.makedirs(OUTPUT_DIR, exist_ok=True)


def svg_header(name):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{SVG_W}" height="{SVG_H}" '
        f'viewBox="0 0 {SVG_W} {SVG_H}">\n'
        f'  <!-- {name} -->\n'
        f'  <!-- H={H}mm L={L}mm -->\n'
        f'  <rect width="{SVG_W}" height="{SVG_H}" fill="white"/>\n'
    )


def svg_footer():
    return '</svg>\n'


def rect(x_mm, y_mm, w_mm, h_mm, color="black"):
    """Zeichnet ein Rechteck in mm-Koordinaten."""
    x = x_mm * scale_x
    y = y_mm * scale_y
    w = w_mm * scale_x
    h = h_mm * scale_y
    return f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{color}"/>\n'


def poly(points_mm, color="black"):
    """Polygon aus mm-Koordinaten."""
    pts = " ".join(f"{x*scale_x:.1f},{y*scale_y:.1f}" for x, y in points_mm)
    return f'  <polygon points="{pts}" fill="{color}"/>\n'


def circle_fill(cx_mm, cy_mm, r_mm, color="white"):
    cx = cx_mm * scale_x
    cy = cy_mm * scale_y
    r = min(r_mm * scale_x, r_mm * scale_y)
    return f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{color}"/>\n'


def material_ratio(filled_area_mm2):
    total = L * H
    return filled_area_mm2 / total


# ============================================================
# 1) Vollrechteck (Referenz, 100% Material)
# ============================================================
def gen_solid():
    name = "vollrechteck"
    area = L * H
    svg = svg_header("Vollrechteck")
    svg += rect(0, 0, L, H)
    svg += svg_footer()
    with open(f"{OUTPUT_DIR}/{name}.svg", "w") as f:
        f.write(svg)
    print(f"[{name}] Materialanteil: {material_ratio(area)*100:.1f}%  Fläche: {area:.1f} mm²")


# ============================================================
# 2) I-Träger
# ============================================================
def gen_i_beam(flange_h=3.0, web_t=4.0):
    name = "i_traeger"
    fh = flange_h
    wt = web_t
    wh = H - 2 * fh
    wx = (L - wt) / 2

    area = 2 * (L * fh) + wt * wh

    svg = svg_header("I-Traeger")
    svg += rect(0, 0, L, fh)               # oberer Flansch
    svg += rect(wx, fh, wt, wh)            # Steg
    svg += rect(0, H - fh, L, fh)         # unterer Flansch
    svg += svg_footer()
    with open(f"{OUTPUT_DIR}/{name}.svg", "w") as f:
        f.write(svg)
    print(f"[{name}] Materialanteil: {material_ratio(area)*100:.1f}%  Fläche: {area:.1f} mm²")


# ============================================================
# 3) Hohlrechteck
# ============================================================
def gen_hollow_rect(t_wall=2.5):
    name = "hohlrechteck"
    t = t_wall
    inner_w = L - 2 * t
    inner_h = H - 2 * t
    area = L * H - inner_w * inner_h

    svg = svg_header("Hohlrechteck")
    svg += rect(0, 0, L, H)
    svg += rect(t, t, inner_w, inner_h, color="white")
    svg += svg_footer()
    with open(f"{OUTPUT_DIR}/{name}.svg", "w") as f:
        f.write(svg)
    print(f"[{name}] Materialanteil: {material_ratio(area)*100:.1f}%  Fläche: {area:.1f} mm²")


# ============================================================
# 4) Gitterstruktur (vertikale Rippen)
# ============================================================
def gen_grid(n_ribs=4, rib_t=2.0, flange_h=2.5):
    name = "gitter"
    fh = flange_h
    wh = H - 2 * fh
    rt = rib_t

    area = 2 * (L * fh)
    # Seitenwände
    area += 2 * (rt * wh)
    # Innere Rippen
    inner_spacing = (L - 2 * rt) / (n_ribs + 1)
    area += n_ribs * (rt * wh)

    svg = svg_header("Gitter mit Rippen")
    svg += rect(0, 0, L, fh)           # oben
    svg += rect(0, H - fh, L, fh)     # unten
    svg += rect(0, fh, rt, wh)        # links
    svg += rect(L - rt, fh, rt, wh)   # rechts
    for i in range(n_ribs):
        x = rt + (i + 1) * inner_spacing - rt / 2
        svg += rect(x, fh, rt, wh)
    svg += svg_footer()
    with open(f"{OUTPUT_DIR}/{name}.svg", "w") as f:
        f.write(svg)
    print(f"[{name}] Materialanteil: {material_ratio(area)*100:.1f}%  Fläche: {area:.1f} mm²")


# ============================================================
# 5) Doppel-T (breiter Steg, dickere Flansche)
# ============================================================
def gen_double_t(flange_h=4.0, web_t=8.0):
    name = "doppel_t"
    fh = flange_h
    wt = web_t
    wh = H - 2 * fh
    wx = (L - wt) / 2
    area = 2 * (L * fh) + wt * wh

    svg = svg_header("Doppel-T-Traeger")
    svg += rect(0, 0, L, fh)
    svg += rect(wx, fh, wt, wh)
    svg += rect(0, H - fh, L, fh)
    svg += svg_footer()
    with open(f"{OUTPUT_DIR}/{name}.svg", "w") as f:
        f.write(svg)
    print(f"[{name}] Materialanteil: {material_ratio(area)*100:.1f}%  Fläche: {area:.1f} mm²")


# ============================================================
# 6) Honigwaben-Gitter (diagonale Streben)
# ============================================================
def gen_honeycomb(n_cells=4, wall_t=2.0, flange_h=2.5):
    name = "honigwabe"
    fh = flange_h
    wh = H - 2 * fh
    n = n_cells
    cell_w = (L) / n

    svg = svg_header("Honigwaben-Gitter")
    svg += rect(0, 0, L, fh)
    svg += rect(0, H - fh, L, fh)

    # Diagonale Streben (X-Muster in jedem Zell-Abschnitt)
    for i in range(n):
        x0 = i * cell_w
        x1 = x0 + cell_w
        y0 = fh
        y1 = H - fh
        wt = wall_t
        # Diagonale von oben-links nach unten-rechts
        svg += poly([(x0, y0), (x0+wt, y0), (x1, y1-wt), (x1, y1), (x1-wt, y1), (x0, y0+wt)])
        # Diagonale von oben-rechts nach unten-links
        svg += poly([(x1, y0), (x1-wt, y0), (x0, y1-wt), (x0, y1), (x0+wt, y1), (x1, y0+wt)])

    svg += svg_footer()
    with open(f"{OUTPUT_DIR}/{name}.svg", "w") as f:
        f.write(svg)

    area_approx = 2 * (L * fh) + n * 2 * (wall_t * np.sqrt((L/n)**2 + wh**2))
    print(f"[{name}] Materialanteil (ca.): {material_ratio(area_approx)*100:.1f}%  Fläche: {area_approx:.1f} mm²")


# ============================================================
# 7) Brücke mit Bögen (Unterspannung)
# ============================================================
def gen_arch(flange_h=2.5, arch_t=2.5, n_hangers=5):
    name = "bogen"
    fh = flange_h

    # SVG hat kein einfaches "Kreisbogen-Füll-Primitiv" => Annäherung durch Polygon
    n_pts = 40
    angle = np.linspace(np.pi, 0, n_pts)
    # Bogen sitzt unter der Brücke, Radius so dass er exakt H hoch ist
    r = (L**2 / 8 + H**2 / 2) / (2 * (H - fh))  # Kreisbogen-Radius
    cx = L / 2
    cy_arc = H - fh - r  # Mittelpunkt des Kreises (kann negativ sein = über dem Querschnitt)

    # Oberer Flansch
    area = L * fh

    svg = svg_header("Bogenprofil")
    svg += rect(0, 0, L, fh)  # oberer Flansch

    # Unterer Bogen als dicke Linie approximiert
    arc_inner = []
    arc_outer = []
    for a in np.linspace(0, np.pi, n_pts):
        x = cx + r * np.cos(np.pi - a)
        y = cy_arc + r * np.sin(np.pi - a)
        arc_inner.append((x, y))
    r_out = r + arch_t
    for a in np.linspace(np.pi, 0, n_pts):
        x = cx + r_out * np.cos(np.pi - a)
        y = cy_arc + r_out * np.sin(np.pi - a)
        arc_outer.append((x, y))

    all_pts = arc_inner + arc_outer
    # Clip to [0, B] x [0, H]
    all_pts_clipped = [(max(0, min(L, x)), max(0, min(H, y))) for x, y in all_pts]
    svg += poly(all_pts_clipped)

    # Hänger (vertical bars)
    hanger_w = 1.5
    for i in range(n_hangers):
        x = L / (n_hangers + 1) * (i + 1)
        # y-Koordinate des Bogens an Position x
        dx = x - cx
        if abs(dx) <= r:
            y_arc = cy_arc + np.sqrt(r**2 - dx**2)
        else:
            y_arc = H
        y_arc = max(fh, min(H, y_arc))
        svg += rect(x - hanger_w/2, fh, hanger_w, y_arc - fh)
        area += hanger_w * (y_arc - fh)

    svg += svg_footer()
    with open(f"{OUTPUT_DIR}/{name}.svg", "w") as f:
        f.write(svg)
    print(f"[{name}] Materialanteil (ca.): {material_ratio(area)*100:.1f}%  Fläche: {area:.1f} mm²")


# ============================================================
# Alle generieren
# ============================================================
if __name__ == "__main__":
    print(f"Brückenparameter: B={L}mm, H={H}mm, L={L}mm")
    print(f"Grenzlast: 3kg = {3*9.81:.1f}N, max. Durchbiegung: 3mm")
    print(f"SVG Auflösung: {SVG_W}x{SVG_H}px\n")
    print("Generiere Profile...")
    print("-" * 50)

    gen_solid()
    gen_i_beam(flange_h=3.0, web_t=4.0)
    gen_hollow_rect(t_wall=2.5)
    gen_grid(n_ribs=4, rib_t=2.0, flange_h=2.5)
    gen_double_t(flange_h=4.0, web_t=8.0)
    gen_honeycomb(n_cells=4, wall_t=2.0, flange_h=2.5)
    gen_arch(flange_h=2.5, arch_t=2.5, n_hangers=5)

    print("-" * 50)
    print(f"\nAlle SVGs gespeichert in: ./{OUTPUT_DIR}/")
    print("\nNächster Schritt: simulation.py ausführen, um Durchbiegung zu berechnen.")
