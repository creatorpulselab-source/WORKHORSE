import os
import logging
from pathlib import Path
from typing import Dict, Any, Union

logger = logging.getLogger("workhorse.cipher")

class CipherScrubber:
    """
    CIPHER [82 Pb] (Lead Shield)
    Privacy & Air-Gapped EXIF/Metadata Scrubber for Creator Media.
    Strips camera serial numbers, GPS coords, creation timestamps,
    software tags, and ICC profile device fingerprints.
    """
    def __init__(self):
        self.scrubbed_count = 0

    def scrub_image(self, file_path: Union[str, Path], output_path: Union[str, Path] = None) -> Dict[str, Any]:
        """
        Removes all EXIF, XMP, IPTC, and private metadata chunks from JPEG, PNG, WEBP.
        If output_path is None, overwrites file_path in-place atomically.
        """
        in_p = Path(file_path)
        if not in_p.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        out_p = Path(output_path) if output_path else in_p
        tmp_p = out_p.with_suffix(".scrubbing.tmp")

        try:
            from PIL import Image

            with Image.open(in_p) as img:
                # Create a completely clean pixel image without info dict (strips EXIF, XMP, ICC)
                data = list(img.getdata())
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(data)

                # Save clean image without any metadata headers
                fmt = img.format or ("PNG" if in_p.suffix.lower() == ".png" else "JPEG")
                if fmt.upper() in ("JPG", "JPEG"):
                    clean_img.save(tmp_p, format="JPEG", quality=95, optimize=True)
                elif fmt.upper() == "PNG":
                    clean_img.save(tmp_p, format="PNG", optimize=True)
                elif fmt.upper() == "WEBP":
                    clean_img.save(tmp_p, format="WEBP", quality=95)
                else:
                    clean_img.save(tmp_p, format=fmt)

            # Atomic replace
            os.replace(tmp_p, out_p)
            self.scrubbed_count += 1
            return {
                "success": True,
                "file": str(out_p),
                "filename": out_p.name,
                "privacy_status": "CLEAN (All EXIF/GPS/Device tags permanently stripped)",
                "agent": "CIPHER [82 Pb]"
            }

        except Exception as e:
            if tmp_p.exists():
                try:
                    tmp_p.unlink()
                except Exception:
                    pass
            logger.error(f"[CIPHER] Failed to scrub {in_p.name}: {e}")
            return {"success": False, "error": str(e), "file": str(in_p)}

cipher_scrubber = CipherScrubber()
