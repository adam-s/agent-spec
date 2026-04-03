#!/usr/bin/env python3
"""Test script for GIF builder toolkit."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from core.gif_builder import GIFBuilder
from core.validators import validate_gif


def test_basic_gif():
    """Create a simple animated GIF and validate it."""
    builder = GIFBuilder(width=128, height=128, fps=10)

    # Create 8 frames with a moving circle
    for i in range(8):
        frame = Image.new("RGB", (128, 128), (30, 30, 60))
        draw = ImageDraw.Draw(frame)
        x = 20 + i * 12
        draw.ellipse([x, 40, x + 48, 88], fill=(255, 100, 50))
        builder.add_frame(frame)

    output = Path("test_output.gif")
    info = builder.save(str(output), num_colors=48)

    # Verify file was created
    assert output.exists(), "GIF file was not created"
    assert info["frame_count"] == 8, f"Expected 8 frames, got {info['frame_count']}"
    assert info["size_kb"] > 0, "GIF file is empty"

    # Validate with the toolkit's own validator
    passes, details = validate_gif(str(output), is_emoji=True, verbose=False)
    assert passes, f"GIF failed validation: {details}"

    # Clean up
    output.unlink()
    print("All checks passed.")


if __name__ == "__main__":
    try:
        test_basic_gif()
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
