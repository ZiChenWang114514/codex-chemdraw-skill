"""Networked tools kept separate so upload policy remains explicit."""

from __future__ import annotations

from typing import Any, Optional

from decimer_api import DecimerUploadRefused, recognize_image


def extract_structures_via_decimer_api(
    image_path: str,
    hand_drawn: bool = False,
    output_path: Optional[str] = None,
    timeout_seconds: int = 600,
    confirm_upload: bool = False,
    approved_sha256: Optional[str] = None,
    approved_origin: Optional[str] = None,
) -> dict[str, Any]:
    """Upload an image to DECIMER only when confirm_upload is explicitly true."""
    try:
        return recognize_image(
            image_path,
            hand_drawn=hand_drawn,
            output_path=output_path,
            timeout_seconds=timeout_seconds,
            confirm_upload=confirm_upload,
            approved_sha256=approved_sha256,
            approved_origin=approved_origin,
        )
    except DecimerUploadRefused as exc:
        return exc.as_result()


REMOTE_TOOLS = {"extract_structures_via_decimer_api": extract_structures_via_decimer_api}
