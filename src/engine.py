import os
import logging
from typing import List, Optional
import numpy as np
import cv2

from filters import ImageFilter
from src.raw_loader import RawLoader

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


class ImageEngine:
    """Manages raw image loading, preview pipeline, and full-resolution export."""

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

    def update_pipeline(self, filters: List[ImageFilter], is_modified: bool = True) -> Optional[np.ndarray]:
        """Applies a new list of filters to the preview base image."""
        if self._preview_base is None:
            return None

        self._filters = filters.copy()
        self._is_modified = is_modified

        buffer = self._preview_base
        try:
            for active_filter in self._filters:
                buffer = active_filter.apply(buffer)
            self._current_preview = buffer
            return self._current_preview
        except Exception as err:
            logging.error("Error during preview pipeline processing: %s", err)
            return self._preview_base

    def export_jpeg(self, destination_path: str, quality: int = 95) -> bool:
        """
        Loads the raw file at full resolution, applies all current filters, and saves as JPEG.
        """
        if not self._raw_path or not os.path.isfile(self._raw_path):
            logging.error("No valid raw file source found for export.")
            return False

        try:
            logging.info("Decoding full resolution RAW for export: %s", self._raw_path)
            full_res_image = RawLoader.load_image(self._raw_path, half_size=False)
            if full_res_image is None:
                return False

            logging.info("Applying %d filters to full-resolution image...", len(self._filters))
            export_buffer = full_res_image
            for active_filter in self._filters:
                export_buffer = active_filter.apply(export_buffer)

            # OpenCV expects BGR color format for writing to disk
            bgr_image = cv2.cvtColor(export_buffer, cv2.COLOR_RGB2BGR)
            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), max(1, min(quality, 100))]
            success = cv2.imwrite(destination_path, bgr_image, encode_params)

            if success:
                logging.info("Image successfully exported to: %s", destination_path)
                self._is_modified = False
                return True
            else:
                logging.error("OpenCV failed to write JPEG to: %s", destination_path)
                return False

        except Exception as err:
            logging.error("Unexpected error during JPEG export: %s", err)
            return False