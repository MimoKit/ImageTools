"""ImageTools for GsCore."""
from __future__ import annotations

from gsuid_core.sv import Plugins

from .version import ImageTools_version

Plugins(
    name="ImageTools",
    allow_empty_prefix=True,
    disable_force_prefix=True,
    alias=["imagetools", "图片操作"],
)

__version__ = ImageTools_version
