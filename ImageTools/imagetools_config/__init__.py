from __future__ import annotations

from gsuid_core.data_store import get_res_path
from gsuid_core.utils.plugins_config.gs_config import StringConfig

from .config_default import CONFIG_DEFAULT

CONFIG_PATH = get_res_path() / "ImageTools" / "console_config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

IMAGETOOLS_CONFIG = StringConfig("ImageTools", CONFIG_PATH, CONFIG_DEFAULT)
IMAGETOOLS_CONFIG.plugin_name = "ImageTools"
