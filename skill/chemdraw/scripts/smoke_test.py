from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image
from cdxml_toolkit.mcp_server import server


def as_dict(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


def require_ok(result, operation: str):
    data = as_dict(result)
    if not isinstance(data, dict) or not data.get("ok"):
        raise RuntimeError(f"{operation} failed: {data}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end ChemDraw smoke test")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cdxml_path = output_dir / "aspirin.cdxml"
    png_path = output_dir / "aspirin.png"

    molecule = require_ok(server.resolve_name("aspirin", use_network=True), "resolve_name")
    drawing = require_ok(
        server.draw_molecule(molecule, output_path=str(cdxml_path)),
        "draw_molecule",
    )
    rendered = require_ok(
        server.render_to_png(str(cdxml_path), output_path=str(png_path)),
        "render_to_png",
    )

    if not cdxml_path.is_file() or cdxml_path.stat().st_size == 0:
        raise RuntimeError("CDXML output is missing or empty")
    if not png_path.is_file() or png_path.stat().st_size == 0:
        raise RuntimeError("PNG output is missing or empty")

    with Image.open(png_path) as image:
        width, height = image.size
        image.verify()
    if width < 32 or height < 32:
        raise RuntimeError(f"PNG dimensions are implausible: {width}x{height}")

    print(json.dumps({
        "ok": True,
        "resolved_name": molecule.get("name"),
        "formula": molecule.get("formula"),
        "source": molecule.get("source"),
        "cdxml": str(cdxml_path),
        "cdxml_size": cdxml_path.stat().st_size,
        "png": str(png_path),
        "png_size": png_path.stat().st_size,
        "png_dimensions": [width, height],
        "draw_result": drawing,
        "render_result": rendered,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
