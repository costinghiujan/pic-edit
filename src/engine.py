import os
import logging
from typing import List, Optional
import numpy as np
import cv2

from src.raw_loader import RawLoader
from src.filters.base import ImageFilter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


class ImageEngine:
    """Core image processing pipeline and state manager."""

    def __init__(self):
        self._raw_path: Optional[str] = None
        self._preview_base: Optional[np.ndarray] = None
        self._current_preview: Optional[np.ndarray] = None
        self._filters: List[ImageFilter] = []
        self._is_modified: bool = False

    @property
    def has_image(self) -> bool:
        return self._preview_base is not None

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    def load(self, filepath: str, max_preview_dim: int = 1280) -> bool:
        """Loads a RAW image preview buffer and resets the filter pipeline state."""
        preview_data = RawLoader.load_image(
            filepath,
            half_size=True,
            max_preview_dim=max_preview_dim
        )
        if preview_data is None:
            logging.error("Failed to load preview for file: %s", filepath)
            return False

        self._raw_path = filepath
        self._preview_base = preview_data
        self._current_preview = preview_data.copy()
        self._filters.clear()
        self._is_modified = False
        return True

    def update_pipeline(self, filter_list: List[ImageFilter], is_modified: bool = True) -> np.ndarray:
        """Applies a list of filters sequentially over the preview buffer."""
        if not self.has_image:
            raise RuntimeError("No image loaded in ImageEngine.")

        self._filters = filter_list
        self._is_modified = is_modified

        processed = self._preview_base.copy()
        for f in self._filters:
            if f is not None:
                processed = f.apply(processed)

        self._current_preview = processed
        return self._current_preview

    def export_jpeg(self, output_path: str, quality: int = 95) -> bool:
        """Renders the filter pipeline on the full-resolution RAW sensor image and saves as JPEG."""
        if not self.has_image or not self._raw_path:
            logging.error("Cannot export: No active RAW file loaded.")
            return False

        logging.info("Decoding full-resolution RAW for export: %s", self._raw_path)
        full_res_image = RawLoader.load_image(self._raw_path, half_size=False, max_preview_dim=None)
        if full_res_image is None:
            logging.error("Full-resolution decode failed.")
            return False

        logging.info("Applying filter pipeline to full-resolution buffer...")
        for f in self._filters:
            if f is not None:
                full_res_image = f.apply(full_res_image)

        # Convert RGB to BGR for OpenCV export
        bgr_output = cv2.cvtColor(full_res_image, cv2.COLOR_RGB2BGR)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        success = cv2.imwrite(output_path, bgr_output, [cv2.IMWRITE_JPEG_QUALITY, quality])

        if success:
            logging.info("Image exported successfully to: %s", output_path)
        else:
            logging.error("OpenCV failed to write JPEG to: %s", output_path)

        return success