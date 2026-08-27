from pathlib import Path
from PIL import Image, ImageDraw


def create_icon(output_path="icon.ico"):
    output = Path(output_path)

    size = 256

    img = Image.new(
        "RGBA",
        (size, size),
        (255, 255, 255, 0),
    )

    draw = ImageDraw.Draw(img)

    # Main folder
    draw.rounded_rectangle(
        (25, 75, 231, 215),
        radius=24,
        fill=(37, 99, 235, 255),
    )

    # Folder tab
    draw.rounded_rectangle(
        (40, 45, 135, 100),
        radius=15,
        fill=(29, 78, 216, 255),
    )

    # Search glass
    draw.ellipse(
        (75, 100, 165, 190),
        outline=(255, 255, 255, 255),
        width=14,
    )

    draw.line(
        (150, 175, 205, 225),
        fill=(255, 255, 255, 255),
        width=16,
    )

    # Duplicate indicator
    draw.rectangle(
        (175, 100, 215, 140),
        fill=(250, 204, 21, 255),
    )

    img.save(
        output,
        format="ICO",
        sizes=[
            (256, 256),
            (128, 128),
            (64, 64),
            (48, 48),
            (32, 32),
            (16, 16),
        ],
    )

    return str(output)


if __name__ == "__main__":
    create_icon()
    print("icon.ico created successfully")