from __future__ import annotations

from typing import Dict

from gsuid_core.utils.plugins_config.models import GSC, GsStrConfig

CONFIG_DEFAULT: Dict[str, GSC] = {
    "matting_server_url": GsStrConfig(
        "抠图服务地址",
        "Anime Background Remover / Gradio 服务地址，留空使用默认 HuggingFace Space。",
        "",
    ),
}

