import os
import logging
from typing import Optional
import numpy as np
import rawpy
import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")


class RawLoader:
    """Handles loading and decoding of RAW sensor image files."""

    @staticmethod
    def load_image(
        filepath: str, 
        half_size: bool = False, 
        max_preview_dim: Optional[int] = None
    ) -> Optional[np.ndarray]:
        """
        Reads a RAW file from disk and returns an RGB NumPy array.

        :param filepath: Path to the RAW image file.
        :param half_size: If True, performs faster half-resolution debayering.
        :param max_preview_dim: If set, scales down the preview so its longest side is at most this value.
        :return: RGB image as a NumPy ndarray, or None if decoding fails.
        :raises FileNotFoundError: If the provided path does not exist.
        """
        if not os.path.isfile(filepath):
            logging.error("File not found: %s", filepath)
            raise FileNotFoundError(f"The specified RAW file does not exist: {filepath}")

        try:
            logging.info("Reading RAW file: %s (half_size=%s)", filepath, half_size)
            with rawpy.imread(filepath) as raw_file:
                rgb_image: np.ndarray = raw_file.postprocess(
                    half_size=half_size,
                    use_camera_wb=True
                )

                # Downscale preview buffer for ultra-fast slider response
                if max_preview_dim is not None and rgb_image is not None:
                    h, w = rgb_image.shape[:2]
                    longest_side = max(h, w)

                    if longest_side > max_preview_dim:
                        scale = max_preview_dim / float(longest_side)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        # INTER_AREA is optimal for high-quality downsampling
                        rgb_image = cv2.resize(rgb_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
                        logging.info("Downscaled preview buffer to: %sx%s", new_w, new_h)

                return rgb_image

        except rawpy.LibRawError as err:
            logging.error("LibRaw failed to decode file: %s. Error: %s", filepath, err)
            return None
        except Exception as err:
            logging.error("Unexpected error while loading RAW image: %s", err)
            return None