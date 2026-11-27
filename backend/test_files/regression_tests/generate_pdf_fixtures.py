"""Generate synthetic scanned PDF test fixtures."""

from pathlib import Path

import pymupdf


def generate_scanned_fixture():

    base = Path(__file__).resolve().parents[1]

    source = base / "sample_multiple_notices.pdf"

    output = base / "sample_multiple_notices_scanned.pdf"

    if output.exists():

        return output

    with pymupdf.open(source) as original:

        with pymupdf.open() as scanned:

            for page in original:

                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(3, 3),
                    alpha=False,
                )

                target = scanned.new_page(
                    width=page.rect.width,
                    height=page.rect.height,
                )

                target.insert_image(
                    target.rect,
                    pixmap=pixmap,
                )

            scanned.save(
                output,
                garbage=4,
                deflate=True,
            )

    return output


if __name__ == "__main__":

    print(
        "Scanned fixture:",
        generate_scanned_fixture(),
    )
