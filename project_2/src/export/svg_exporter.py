def export_svg(geometry, filename):
    min_x, min_y, max_x, max_y = geometry.bounding_box()

    width = max_x - min_x
    height = max_y - min_y

    with open(filename, "w") as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" ')
        f.write(f'width="{width}mm" height="{height}mm" ')
        f.write(f'viewBox="{min_x} {min_y} {width} {height}">\n')

        for shape in geometry.shapes:
            f.write(
                f'<rect x="{shape.x}" y="{shape.y}" '
                f'width="{shape.width}" height="{shape.height}" '
                f'style="fill:black;" />\n'
            )

        f.write('</svg>\n')
