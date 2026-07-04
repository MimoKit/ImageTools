"""ImageTools command handlers."""
from __future__ import annotations

import asyncio
import base64
import binascii
import io
import math
import re
import zipfile
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from PIL import Image, ImageChops, ImageOps, ImageSequence

from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment
from gsuid_core.sv import SV

from ..imagetools_config import IMAGETOOLS_CONFIG

LOG_PREFIX = "[ImageTools]"
MAX_IMAGE_BYTES = 30 * 1024 * 1024
MAX_GIF_SPLIT_PREVIEW = 24
HELP_TEXT = """图片操作 / ImageTools

基础：
图片信息、水平翻转、垂直翻转、灰度化、反色、幻影坦克、抠图

参数：
旋转 90
缩放 50% / 缩放 300x200 / 缩放 300x
裁剪 0,0,300,300 / 裁剪 300x300 / 裁剪 1:1
颜色滤镜 255,0,0 / 颜色滤镜 #ff0000

拼接：
水平拼接、垂直拼接

GIF：
gif分解、gif合成 0.08、gif反转、加速0.5 / 加速10 / 加速1.5

用法：发送命令时带图，或回复一张/多张图片后发送命令。"""

sv_help = SV("图片操作帮助")
sv_info = SV("图片信息")
sv_tool = SV("图片操作")
sv_gif = SV("GIF图片操作")


def _command_pattern(words: str, arg: str = "") -> str:
    prefix = r"^#?(?:(?:图片操作|imagetools))?"
    return prefix + rf"(?:{words})(?:图片)?{arg}\s*$"


def _read_bytes(source: str) -> bytes | None:
    text = str(source or "").strip()
    if not text:
        return None
    try:
        if text.startswith("data:image/") and "," in text:
            data = base64.b64decode(text.split(",", 1)[1], validate=False)
        elif text.startswith("base64://"):
            data = base64.b64decode(text[9:], validate=False)
        else:
            if text.startswith("link://"):
                text = text[7:]
            if text.startswith(("http://", "https://")):
                req = Request(text, headers={"User-Agent": "Mozilla/5.0 ImageTools/1.0"})
                with urlopen(req, timeout=20) as resp:
                    data = resp.read(MAX_IMAGE_BYTES + 1)
            else:
                path = Path(text)
                if not path.is_file():
                    return None
                data = path.read_bytes()
    except (OSError, ValueError, binascii.Error) as exc:
        logger.warning(f"{LOG_PREFIX} 读取图片失败: {exc}")
        return None
    if not data or len(data) > MAX_IMAGE_BYTES:
        return None
    return data


def _iter_message_images(ev: Event) -> Iterable[str]:
    for content in ev.content or []:
        if content.type in {"image", "img"} and isinstance(content.data, str):
            ref = content.data.strip()
            if ref:
                yield ref
    for item in ev.image_list or []:
        if isinstance(item, str) and item.strip():
            yield item.strip()
    if isinstance(ev.image, str) and ev.image.strip():
        yield ev.image.strip()


def _iter_reply_images(ev: Event) -> Iterable[str]:
    reply = getattr(ev, "reply", None)
    if reply is None:
        return
    for attr in ("content", "message"):
        value = getattr(reply, attr, None)
        if not value:
            continue
        for item in value if isinstance(value, (list, tuple)) else [value]:
            item_type = getattr(item, "type", None)
            data = getattr(item, "data", None)
            if item_type in {"image", "img"} and isinstance(data, str) and data.strip():
                yield data.strip()
    for attr in ("image_list", "image"):
        value = getattr(reply, attr, None)
        if not value:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, str) and item.strip():
                    yield item.strip()
        elif isinstance(value, str) and value.strip():
            yield value.strip()


def _image_refs(ev: Event) -> tuple[str, ...]:
    refs = [*list(_iter_reply_images(ev)), *list(_iter_message_images(ev))]
    return tuple(dict.fromkeys(refs))


async def _get_images(ev: Event, limit: int | None = None) -> list[bytes]:
    refs = _image_refs(ev)
    if limit is not None:
        refs = refs[:limit]
    result: list[bytes] = []
    for ref in refs:
        data = await asyncio.to_thread(_read_bytes, ref)
        if data:
            result.append(data)
    return result


def _open_image(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data))


def _save_image(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    save_kwargs = {"format": fmt}
    if fmt.upper() == "GIF":
        save_kwargs["save_all"] = True
    img.save(buf, **save_kwargs)
    return buf.getvalue()


def _save_gif(frames: list[Image.Image], duration_ms: int) -> bytes:
    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )
    return buf.getvalue()


def _fit_rgba(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img.convert("RGBA"), size, method=Image.Resampling.LANCZOS)


def _parse_color(text: str) -> tuple[int, int, int] | None:
    value = text.strip()
    rgb_match = re.fullmatch(r"(\d{1,3}),\s*(\d{1,3}),\s*(\d{1,3})", value)
    if rgb_match:
        rgb = tuple(int(x) for x in rgb_match.groups())
        if all(0 <= x <= 255 for x in rgb):
            return rgb
        return None
    hex_match = re.fullmatch(r"#?([0-9a-fA-F]{6})", value)
    if hex_match:
        raw = hex_match.group(1)
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    return None


def _parse_resize(text: str, size: tuple[int, int]) -> tuple[int, int] | None:
    value = text.strip().lower()
    if not value:
        return None
    percent = re.fullmatch(r"(\d+(?:\.\d+)?)%", value)
    if percent:
        scale = float(percent.group(1)) / 100
        return max(1, round(size[0] * scale)), max(1, round(size[1] * scale))
    fixed = re.fullmatch(r"(\d+)(?:x(\d*)?)?", value)
    if fixed:
        width = int(fixed.group(1))
        height_raw = fixed.group(2)
        if height_raw:
            height = int(height_raw)
        else:
            height = round(size[1] * (width / size[0]))
        return max(1, width), max(1, height)
    return None


def _parse_crop(text: str, size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    value = text.strip().lower()
    if re.fullmatch(r"\d+,\d+,\d+,\d+", value):
        left, top, right, bottom = [int(x) for x in value.split(",")]
        return left, top, right, bottom
    if re.fullmatch(r"\d+x\d+", value):
        width, height = [int(x) for x in value.split("x")]
        return 0, 0, width, height
    ratio = re.fullmatch(r"(\d+):(\d+)", value)
    if ratio:
        rw, rh = int(ratio.group(1)), int(ratio.group(2))
        if rw <= 0 or rh <= 0:
            return None
        target = rw / rh
        width, height = size
        if width / height > target:
            new_width = math.floor(height * target)
            left = (width - new_width) // 2
            return left, 0, left + new_width, height
        new_height = math.floor(width / target)
        top = (height - new_height) // 2
        return 0, top, width, top + new_height
    return None


def _image_info_text(data: bytes) -> str:
    with _open_image(data) as img:
        width, height = img.size
        frames = getattr(img, "n_frames", 1)
        animated = bool(getattr(img, "is_animated", False))
        lines = [
            "图片信息:",
            f"分辨率: {width}x{height}",
            f"格式: {img.format or '未知'}",
            f"是否为动图: {'是' if animated else '否'}",
        ]
        if animated:
            durations = [
                int(frame.info.get("duration", img.info.get("duration", 0)) or 0)
                for frame in ImageSequence.Iterator(img)
            ]
            avg = sum(durations) / len(durations) if durations else 0
            lines.append(f"帧数: {frames}")
            lines.append(f"平均帧间隔: {avg:.0f}ms")
        return "\n".join(lines)


def _phantom_tank(light_data: bytes, dark_data: bytes) -> bytes:
    with _open_image(light_data) as light_raw, _open_image(dark_data) as dark_raw:
        size = light_raw.size
        light = ImageOps.grayscale(_fit_rgba(light_raw, size))
        dark = ImageOps.grayscale(_fit_rgba(dark_raw, size))
        pixels_light = light.load()
        pixels_dark = dark.load()
        out = Image.new("RGBA", size)
        pixels_out = out.load()
        for y in range(size[1]):
            for x in range(size[0]):
                luma_light = pixels_light[x, y]
                luma_dark = pixels_dark[x, y]
                alpha = max(1, min(255, 255 - luma_light + luma_dark))
                gray = max(0, min(255, round(luma_dark * 255 / alpha)))
                pixels_out[x, y] = (gray, gray, gray, alpha)
        return _save_image(out)


def _merge_images(images: list[bytes], vertical: bool = False) -> bytes:
    opened = [Image.open(io.BytesIO(data)).convert("RGBA") for data in images]
    try:
        if vertical:
            width = max(img.width for img in opened)
            height = sum(img.height for img in opened)
            out = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            y = 0
            for img in opened:
                out.alpha_composite(img, ((width - img.width) // 2, y))
                y += img.height
        else:
            width = sum(img.width for img in opened)
            height = max(img.height for img in opened)
            out = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            x = 0
            for img in opened:
                out.alpha_composite(img, (x, (height - img.height) // 2))
                x += img.width
        return _save_image(out)
    finally:
        for img in opened:
            img.close()


def _split_gif(data: bytes) -> tuple[list[bytes], bytes]:
    with _open_image(data) as img:
        frames = [frame.convert("RGBA").copy() for frame in ImageSequence.Iterator(img)]
    frame_bytes = [_save_image(frame) for frame in frames]
    for frame in frames:
        frame.close()
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for index, raw in enumerate(frame_bytes):
            zf.writestr(f"image_{index:03d}.png", raw)
    return frame_bytes, zip_buf.getvalue()


def _gif_merge(images: list[bytes], duration_text: str) -> bytes:
    duration = int(float(duration_text.strip() or "0.08") * 1000)
    duration = max(20, duration)
    opened = [Image.open(io.BytesIO(data)).convert("RGBA") for data in images]
    try:
        size = opened[0].size
        frames = [_fit_rgba(img, size) for img in opened]
        return _save_gif(frames, duration)
    finally:
        for img in opened:
            img.close()


def _gif_reverse(data: bytes) -> bytes:
    with _open_image(data) as img:
        frames = [frame.convert("RGBA").copy() for frame in ImageSequence.Iterator(img)]
        duration = int(img.info.get("duration", 80) or 80)
    frames.reverse()
    return _save_gif(frames, duration)


def _parse_duration(param: str, base_ms: int) -> int | None:
    value = param.strip().lower()
    speed = re.fullmatch(r"\d+(?:\.\d+)?", value)
    if not speed:
        return None
    multiplier = float(value)
    if multiplier <= 0:
        return None
    return max(20, round(base_ms / multiplier))


def _gif_change_duration(data: bytes, param: str) -> bytes | str:
    with _open_image(data) as img:
        if not bool(getattr(img, "is_animated", False)):
            return "该图片不是动图, 无法进行加速操作"
        base_ms = int(img.info.get("duration", 80) or 80)
        duration = _parse_duration(param, base_ms)
        if duration is None:
            return "请使用正确的倍率格式，例如：加速0.5、加速10、加速1.5"
        frames = [frame.convert("RGBA").copy() for frame in ImageSequence.Iterator(img)]
    return _save_gif(frames, duration)


async def _process_single(bot: Bot, ev: Event, name: str, func) -> None:
    images = await _get_images(ev, 1)
    if not images:
        return await bot.send("请发送图片，或回复图片后再发送命令。")
    try:
        result = await asyncio.to_thread(func, images[0])
    except Exception as exc:
        logger.warning(f"{LOG_PREFIX} {name}失败: {exc}")
        return await bot.send(f"{name}失败: {exc}")
    await bot.send(MessageSegment.image(result))


@sv_help.on_regex(
    _command_pattern(r"(?:(?:图片操作|imagetools))?(?:命令|帮助|菜单|help|说明|功能|指令|使用说明)"),
    block=True,
    prefix=False,
)
async def image_tools_help(bot: Bot, ev: Event) -> None:
    await bot.send(HELP_TEXT)


@sv_info.on_regex(_command_pattern(r"(?:查看)?(?:图片信息|imageinfo)"), block=True, prefix=False)
async def image_info(bot: Bot, ev: Event) -> None:
    images = await _get_images(ev, 1)
    if not images:
        return await bot.send("请发送图片，或回复图片后再发送命令。")
    await bot.send([MessageSegment.image(images[0]), "\n", _image_info_text(images[0])])


@sv_tool.on_regex(_command_pattern(r"水平翻转"), block=True, prefix=False)
async def flip_horizontal(bot: Bot, ev: Event) -> None:
    await _process_single(bot, ev, "水平翻转图片", lambda data: _save_image(ImageOps.mirror(_open_image(data).convert("RGBA"))))


@sv_tool.on_regex(_command_pattern(r"垂直翻转"), block=True, prefix=False)
async def flip_vertical(bot: Bot, ev: Event) -> None:
    await _process_single(bot, ev, "垂直翻转图片", lambda data: _save_image(ImageOps.flip(_open_image(data).convert("RGBA"))))


@sv_tool.on_regex(_command_pattern(r"旋转", r"(?:\s*(\d+))?"), block=True, prefix=False)
async def rotate(bot: Bot, ev: Event) -> None:
    angle = ev.regex_group[0] if ev.regex_group else ""
    if not angle:
        return await bot.send("请输入旋转角度，例如：旋转 90")
    await _process_single(
        bot,
        ev,
        "旋转图片",
        lambda data: _save_image(_open_image(data).convert("RGBA").rotate(-int(angle), expand=True)),
    )


@sv_tool.on_regex(_command_pattern(r"缩放", r"(?:\s*([0-9.]+%?|\d+x\d*))?"), block=True, prefix=False)
async def resize(bot: Bot, ev: Event) -> None:
    param = ev.regex_group[0] if ev.regex_group else ""
    if not param:
        return await bot.send("请输入正确的尺寸格式，例如：缩放 100x100、缩放 100x、缩放 50%")

    def handle(data: bytes) -> bytes:
        with _open_image(data) as img:
            size = _parse_resize(param, img.size)
            if size is None:
                raise ValueError("尺寸格式错误")
            return _save_image(img.convert("RGBA").resize(size, Image.Resampling.LANCZOS))

    await _process_single(bot, ev, "缩放图片", handle)


@sv_tool.on_regex(_command_pattern(r"裁剪", r"(?:\s*([\d:x,]+))?"), block=True, prefix=False)
async def crop(bot: Bot, ev: Event) -> None:
    param = ev.regex_group[0] if ev.regex_group else ""
    if not param:
        return await bot.send("请输入正确的裁剪格式，例如：裁剪 0,0,100,100、裁剪 100x100、裁剪 1:1")

    def handle(data: bytes) -> bytes:
        with _open_image(data) as img:
            box = _parse_crop(param, img.size)
            if box is None:
                raise ValueError("裁剪格式错误")
            return _save_image(img.convert("RGBA").crop(box))

    await _process_single(bot, ev, "裁剪图片", handle)


@sv_tool.on_regex(_command_pattern(r"灰度化"), block=True, prefix=False)
async def grayscale(bot: Bot, ev: Event) -> None:
    await _process_single(bot, ev, "灰度化图片", lambda data: _save_image(ImageOps.grayscale(_open_image(data)).convert("RGBA")))


@sv_tool.on_regex(_command_pattern(r"反色"), block=True, prefix=False)
async def invert(bot: Bot, ev: Event) -> None:
    def handle(data: bytes) -> bytes:
        with _open_image(data).convert("RGBA") as img:
            rgb = ImageOps.invert(img.convert("RGB"))
            rgb.putalpha(img.getchannel("A"))
            return _save_image(rgb)

    await _process_single(bot, ev, "反色图片", handle)


@sv_tool.on_regex(_command_pattern(r"颜色滤镜", r"(?:\s*(\S+))?"), block=True, prefix=False)
async def color_mask(bot: Bot, ev: Event) -> None:
    color_text = ev.regex_group[0] if ev.regex_group else ""
    color = _parse_color(color_text or "")
    if color is None:
        return await bot.send("请输入正确的颜色格式，例如：颜色滤镜 255,0,0 或 颜色滤镜 #ff0000")

    def handle(data: bytes) -> bytes:
        with _open_image(data).convert("RGBA") as img:
            overlay = Image.new("RGBA", img.size, (*color, 120))
            return _save_image(ImageChops.multiply(img, overlay))

    await _process_single(bot, ev, "颜色滤镜图片", handle)


@sv_tool.on_regex(_command_pattern(r"幻影坦克"), block=True, prefix=False)
async def mirage(bot: Bot, ev: Event) -> None:
    images = await _get_images(ev, 2)
    if len(images) != 2:
        return await bot.send("请发送或回复两张图片来制作幻影坦克。")
    result = await asyncio.to_thread(_phantom_tank, images[0], images[1])
    await bot.send(MessageSegment.image(result))


@sv_tool.on_regex(_command_pattern(r"水平拼接"), block=True, prefix=False)
async def merge_horizontal(bot: Bot, ev: Event) -> None:
    images = await _get_images(ev)
    if len(images) < 2:
        return await bot.send("请发送至少两张图片进行水平拼接。")
    result = await asyncio.to_thread(_merge_images, images, False)
    await bot.send(MessageSegment.image(result))


@sv_tool.on_regex(_command_pattern(r"垂直拼接"), block=True, prefix=False)
async def merge_vertical(bot: Bot, ev: Event) -> None:
    images = await _get_images(ev)
    if len(images) < 2:
        return await bot.send("请发送至少两张图片进行垂直拼接。")
    result = await asyncio.to_thread(_merge_images, images, True)
    await bot.send(MessageSegment.image(result))


@sv_tool.on_regex(_command_pattern(r"(?:图片)?抠图"), block=True, prefix=False)
async def image_matting(bot: Bot, ev: Event) -> None:
    images = await _get_images(ev, 1)
    if not images:
        return await bot.send("请发送图片，或回复图片后再发送命令。")
    try:
        from gradio_client import Client

        await bot.send("开始处理图片中，请稍后...")
        base_url = str(IMAGETOOLS_CONFIG.get_config("matting_server_url").data or "").strip()
        if not base_url:
            base_url = "https://skytnt-anime-remove-background.hf.space"
        client = await asyncio.to_thread(Client, base_url.rstrip("/"))
        result = await asyncio.to_thread(client.predict, images[0], api_name="/rmbg_fn")
        await bot.send([MessageSegment.image(images[0]), "\n处理后的图片："])
        if isinstance(result, (list, tuple)):
            for item in result:
                url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
                if url:
                    await bot.send(MessageSegment.image(str(url)))
        else:
            await bot.send(str(result))
    except Exception as exc:
        logger.warning(f"{LOG_PREFIX} 图片抠图失败: {exc}")
        await bot.send(f"图片抠图失败: {exc}")


@sv_gif.on_regex(_command_pattern(r"(?:gif)?分解"), block=True, prefix=False)
async def gif_split(bot: Bot, ev: Event) -> None:
    images = await _get_images(ev, 1)
    if not images:
        return await bot.send("请发送 GIF 图片，或回复 GIF 后再发送命令。")
    try:
        frames, zip_bytes = await asyncio.to_thread(_split_gif, images[0])
    except Exception as exc:
        logger.warning(f"{LOG_PREFIX} GIF分解失败: {exc}")
        return await bot.send(f"GIF分解失败: {exc}")
    await bot.send(MessageSegment.file(zip_bytes, "gif分解.zip"))
    preview = frames[:MAX_GIF_SPLIT_PREVIEW]
    nodes = ["GIF分解预览：\n", *[MessageSegment.image(frame) for frame in preview]]
    if len(frames) > MAX_GIF_SPLIT_PREVIEW:
        nodes.append(f"\n已分解 {len(frames)} 帧，预览前 {MAX_GIF_SPLIT_PREVIEW} 帧，完整结果见 zip 文件。")
    await bot.send(MessageSegment.node(nodes))


@sv_gif.on_regex(_command_pattern(r"(?:gif)?(?:合并|拼接|合成)", r"(?:\s*(\S+))?"), block=True, prefix=False)
async def gif_merge(bot: Bot, ev: Event) -> None:
    duration = ev.regex_group[0] if ev.regex_group else ""
    images = await _get_images(ev)
    if len(images) < 2:
        return await bot.send("请发送至少两张图片进行 GIF 合成。")
    result = await asyncio.to_thread(_gif_merge, images, duration or "0.08")
    await bot.send(MessageSegment.image(result))


@sv_gif.on_regex(_command_pattern(r"(?:gif)?反转"), block=True, prefix=False)
async def gif_reverse(bot: Bot, ev: Event) -> None:
    images = await _get_images(ev, 1)
    if not images:
        return await bot.send("请发送 GIF 图片，或回复 GIF 后再发送命令。")
    result = await asyncio.to_thread(_gif_reverse, images[0])
    await bot.send(MessageSegment.image(result))


@sv_gif.on_regex(_command_pattern(r"加速", r"(?:\s*(\d+(?:\.\d+)?))?"), block=True, prefix=False)
async def gif_change_duration(bot: Bot, ev: Event) -> None:
    param = ev.regex_group[0] if ev.regex_group else ""
    if not param:
        return await bot.send("请使用正确的倍率格式，例如：加速0.5、加速10、加速1.5")
    images = await _get_images(ev, 1)
    if not images:
        return await bot.send("请发送 GIF 图片，或回复 GIF 后再发送命令。")
    result = await asyncio.to_thread(_gif_change_duration, images[0], param)
    if isinstance(result, str):
        return await bot.send(result)
    await bot.send(MessageSegment.image(result))
