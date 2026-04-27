"""
SVG Brücken-Analyse Tool
=========================
Prüft ob ein Querschnitts-SVG physikalisch sinnvoll ist:
  1. Materialverbrauch (%)
  2. Zusammenhängend (alle Pixel in einer Komponente?)
  3. Randverbindung (Material an Ober- UND Unterkante?)
  4. Visualisierung der Zusammenhangskomponenten
"""

import numpy as np
from PIL import Image
import cairosvg
import io
from scipy.ndimage import label
import sys
import os

# Auflösung für die Rasterisierung
RASTER_W = 200
RASTER_H = 100
THRESHOLD = 128  # Grauwertschwelle: < 128 = Material (dunkel)


def svg_to_binary(svg_path: str) -> np.ndarray:
    """Liest SVG und wandelt in binäres Array um. True = Material."""
    png_data = cairosvg.svg2png(
        url=svg_path,
        output_width=RASTER_W,
        output_height=RASTER_H
    )
    img = Image.open(io.BytesIO(png_data)).convert("L")  # Graustufen
    arr = np.array(img)
    binary = arr < THRESHOLD  # True wo Material (dunkel)
    return binary


def check_material(binary: np.ndarray) -> dict:
    """Berechnet Materialanteil."""
    total = binary.size
    filled = binary.sum()
    ratio = filled / total
    return {
        "filled_pixels": int(filled),
        "total_pixels": total,
        "ratio": ratio,
        "percent": ratio * 100,
    }


def check_connectivity(binary: np.ndarray) -> dict:
    """
    Prüft ob alle Materialpixel zusammenhängend sind.
    Gibt Anzahl der Komponenten und deren Größen zurück.
    """
    # 8-Nachbarschaft (diagonal zählt auch)
    struct = np.ones((3, 3), dtype=int)
    labeled, n_components = label(binary, structure=struct)

    component_sizes = []
    for i in range(1, n_components + 1):
        component_sizes.append(int((labeled == i).sum()))

    component_sizes.sort(reverse=True)

    return {
        "n_components": n_components,
        "component_sizes": component_sizes,
        "is_connected": n_components == 1,
        "labeled_array": labeled,
        "largest_ratio": component_sizes[0] / binary.sum() if binary.sum() > 0 else 0,
    }


def check_boundary(binary: np.ndarray) -> dict:
    """
    Prüft ob Material an den Rändern vorhanden ist.
    Für eine Brücke wichtig: muss oben und unten Material haben
    (damit die Kraft übertragen werden kann).
    Außerdem: links und rechts (Auflager).
    """
    top_row = binary[0, :]
    bottom_row = binary[-1, :]
    left_col = binary[:, 0]
    right_col = binary[:, -1]

    top_fill = top_row.sum() / RASTER_W
    bottom_fill = bottom_row.sum() / RASTER_W
    left_fill = left_col.sum() / RASTER_H
    right_fill = right_col.sum() / RASTER_H

    return {
        "top_fill": top_fill,
        "bottom_fill": bottom_fill,
        "left_fill": left_fill,
        "right_fill": right_fill,
        "has_top": top_fill > 0.1,
        "has_bottom": bottom_fill > 0.1,
        "has_left": left_fill > 0.1,
        "has_right": right_fill > 0.1,
    }


def score(mat_result, conn_result, bound_result) -> tuple[float, list[str]]:
    """
    Berechnet einen einfachen Qualitätsscore (0-100).
    Gibt auch eine Liste von Warnungen zurück.
    """
    warnings = []
    score = 100.0

    # Materialverbrauch: Weniger ist besser, aber unter 10% ist verdächtig
    ratio = mat_result["ratio"]
    if ratio < 0.10:
        warnings.append("⚠️  Sehr wenig Material (<10%) — wahrscheinlich zu schwach")
        score -= 30
    elif ratio < 0.20:
        warnings.append("⚠️  Wenig Material (<20%) — könnte kritisch sein")
        score -= 10
    elif ratio > 0.80:
        warnings.append("ℹ️  Viel Material (>80%) — Optimierungspotenzial vorhanden")
        score -= 5

    # Zusammenhang
    if not conn_result["is_connected"]:
        n = conn_result["n_components"]
        warnings.append(f"❌ Nicht zusammenhängend! {n} Komponenten gefunden — Brücke würde auseinanderfallen")
        score -= 40
    elif conn_result["largest_ratio"] < 0.95:
        warnings.append(f"⚠️  Kleine Splitter vorhanden (größte Komp. = {conn_result['largest_ratio']*100:.1f}%)")
        score -= 10

    # Randbedingungen
    if not bound_result["has_top"]:
        warnings.append("❌ Kein Material an Oberkante — oberer Flansch fehlt!")
        score -= 20
    if not bound_result["has_bottom"]:
        warnings.append("❌ Kein Material an Unterkante — unterer Flansch fehlt!")
        score -= 20
    if not bound_result["has_left"]:
        warnings.append("⚠️  Kein Material am linken Rand")
        score -= 5
    if not bound_result["has_right"]:
        warnings.append("⚠️  Kein Material am rechten Rand")
        score -= 5

    if not warnings:
        warnings.append("✅ Alles in Ordnung!")

    return max(0.0, score), warnings


def analyze(svg_path: str, verbose=True) -> dict:
    """Vollständige Analyse eines SVGs."""
    name = os.path.basename(svg_path).replace(".svg", "")

    binary = svg_to_binary(svg_path)
    mat = check_material(binary)
    conn = check_connectivity(binary)
    bound = check_boundary(binary)
    quality, warnings_list = score(mat, conn, bound)

    result = {
        "name": name,
        "material_percent": mat["percent"],
        "n_components": conn["n_components"],
        "is_connected": conn["is_connected"],
        "has_top": bound["has_top"],
        "has_bottom": bound["has_bottom"],
        "quality_score": quality,
        "warnings": warnings_list,
        "binary": binary,
        "labeled": conn["labeled_array"],
        "boundary": bound,
    }

    if verbose:
        print(f"\n{'='*50}")
        print(f"  Profil: {name}")
        print(f"{'='*50}")
        print(f"  Material:      {mat['percent']:.1f}%")
        print(f"  Komponenten:   {conn['n_components']}  {'✅' if conn['is_connected'] else '❌'}")
        if not conn["is_connected"]:
            sizes = conn["component_sizes"][:5]
            print(f"  Größen:        {sizes}")
        print(f"  Rand oben:     {bound['top_fill']*100:.0f}%  {'✅' if bound['has_top'] else '❌'}")
        print(f"  Rand unten:    {bound['bottom_fill']*100:.0f}%  {'✅' if bound['has_bottom'] else '❌'}")
        print(f"  Rand links:    {bound['left_fill']*100:.0f}%  {'✅' if bound['has_left'] else '❌'}")
        print(f"  Rand rechts:   {bound['right_fill']*100:.0f}%  {'✅' if bound['has_right'] else '❌'}")
        print(f"  Qualitätsscore: {quality:.0f}/100")
        for w in warnings_list:
            print(f"    {w}")

    return result


def analyze_all(svg_dir: str):
    """Analysiert alle SVGs in einem Ordner und gibt Ranking aus."""
    import glob
    files = sorted(glob.glob(os.path.join(svg_dir, "*.svg")))

    if not files:
        print(f"Keine SVGs gefunden in: {svg_dir}")
        return

    results = []
    for f in files:
        r = analyze(f, verbose=True)
        results.append(r)

    # Ranking nach: Qualität zuerst, dann möglichst wenig Material
    valid = [r for r in results if r["is_connected"] and r["has_top"] and r["has_bottom"]]
    valid.sort(key=lambda r: (-r["quality_score"], r["material_percent"]))

    print(f"\n{'='*50}")
    print("  RANKING (gültige Profile, weniger Material = besser)")
    print(f"{'='*50}")
    for i, r in enumerate(valid):
        print(f"  {i+1}. {r['name']:<20} "
              f"Material: {r['material_percent']:5.1f}%  "
              f"Score: {r['quality_score']:3.0f}/100")

    invalid = [r for r in results if r not in valid]
    if invalid:
        print(f"\n  Ungültige Profile (durchgefallen):")
        for r in invalid:
            print(f"    ✗ {r['name']} — {', '.join(r['warnings'])}")

    return results


def visualize_analysis(svg_path: str, save_path: str = None):
    """Erstellt ein matplotlib-Bild mit der Analyse."""
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

    result = analyze(svg_path, verbose=False)
    binary = result["binary"]
    labeled = result["labeled"]

    fig, axes = plt.subplots(1, 3, figsize=(12, 3))
    name = result["name"]
    fig.suptitle(f"Analyse: {name}  |  Material: {result['material_percent']:.1f}%  |  Score: {result['quality_score']:.0f}/100")

    # Original Bitmap
    axes[0].imshow(binary, cmap="gray_r", aspect="auto")
    axes[0].set_title("Querschnitt (schwarz = Material)")
    axes[0].set_xlabel("Breite →")
    axes[0].set_ylabel("Höhe →")

    # Zusammenhangskomponenten
    n = result["n_components"]
    cmap = plt.cm.get_cmap("tab10", max(n, 1))
    display = np.where(binary, labeled, -1).astype(float)
    display[display == -1] = np.nan
    axes[1].imshow(display, cmap=cmap, aspect="auto", vmin=0.5, vmax=n+0.5)
    axes[1].set_title(f"Komponenten: {n}  {'✅ zusammenhängend' if n==1 else '❌ getrennt!'}")
    axes[1].set_xlabel("Breite →")

    # Randbelegung als Balkendiagramm
    b = result["boundary"]
    labels_b = ["Oben", "Unten", "Links", "Rechts"]
    values = [b["top_fill"]*100, b["bottom_fill"]*100, b["left_fill"]*100, b["right_fill"]*100]
    colors = ["green" if v > 10 else "red" for v in values]
    axes[2].bar(labels_b, values, color=colors, alpha=0.8)
    axes[2].axhline(10, color="gray", linestyle="--", linewidth=0.8, label="Mindest-Schwelle (10%)")
    axes[2].set_ylim(0, 105)
    axes[2].set_title("Randbelegung (%)")
    axes[2].set_ylabel("% des Randes belegt")
    axes[2].legend(fontsize=8)

    # Warnungen als Text
    warn_text = "\n".join(result["warnings"])
    fig.text(0.5, -0.05, warn_text, ha="center", fontsize=9, color="darkred")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, bbox_inches="tight", dpi=120)
        print(f"  → Gespeichert: {save_path}")
    else:
        plt.show()
    plt.close()


# ============================================================
if __name__ == "__main__":
    svg_dir = sys.argv[1] if len(sys.argv) > 1 else "bridge_svgs"

    print("SVG Brücken-Analyse")
    print(f"Analysiere alle SVGs in: {svg_dir}")

    results = analyze_all(svg_dir)

    # Visualisierungen für alle Profile
    print("\nErstelle Visualisierungen...")
    import glob
    for f in sorted(glob.glob(os.path.join(svg_dir, "*.svg"))):
        name = os.path.basename(f).replace(".svg", "")
        save = os.path.join(svg_dir, f"analysis_{name}.png")
        visualize_analysis(f, save_path=save)
