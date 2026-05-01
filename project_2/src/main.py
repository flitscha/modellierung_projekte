from designs.ibeam import IBeamDesign
from export.svg_exporter import export_svg


def main():
    design = IBeamDesign()

    params = design.sample_parameters()
    print("Sampled parameters:", params)

    geometry = design.build_geometry(params)

    if geometry is None:
        print("Invalid geometry")
        return

    area = geometry.approximate_area()
    print("Approx area:", area)

    export_svg(geometry, "output.svg")
    print("SVG exported to output.svg")


if __name__ == "__main__":
    main()
