# ImageTools

<p align="center">
  <a href="https://github.com/MimoKit/ImageTools"><img src="ICON.png" width="256" height="256" alt="ImageTools"></a>
</p>
<h1 align="center">ImageTools 1.0.0</h1>
<h4 align="center">🚧 支持 GsCore 的图片操作插件 🚧</h4>
<div align="center">
  <a href="https://docs.sayu-bot.com/" target="_blank">安装文档</a> &nbsp; · &nbsp;
  <a href="https://github.com/Genshin-bots/gsuid_core" target="_blank">gsuid_core</a> &nbsp; · &nbsp;
  <a href="https://github.com/CandriaJS/karin-plugin-imagetools" target="_blank">原项目</a>
</div>

## 丨安装提醒

> **注意：该插件为 [早柚核心(gsuid_core)](https://github.com/Genshin-bots/gsuid_core) 的扩展，具体安装方式可参考上方安装文档**
>
> **运行环境要求 Python `3.10+`**
>
> 如果已经是最新版本的 `gsuid_core`，可以直接将本仓库克隆到 Core 插件目录后重启 Core：
>
> ```bash
> cd gsuid_core/gsuid_core/plugins
> git clone https://github.com/MimoKit/ImageTools.git ImageTools
> ```
>
> 插件依赖 `Pillow`、`httpx`、`gradio-client`，通常会根据 `pyproject.toml` 自动安装。
>
> 抠图功能依赖 Anime Background Remover / Gradio 服务；如果默认服务不可用，可以在插件配置中填写自定义 `matting_server_url`。
>
> 🚧 插件仍在持续完善中 🚧

## 丨功能

- 图片信息
- 水平翻转 / 垂直翻转
- 旋转 / 缩放 / 裁剪
- 灰度化 / 反色 / 颜色滤镜
- 幻影坦克
- 水平拼接 / 垂直拼接
- 图片抠图
- GIF 分解 / 合成 / 反转 / 加速

## 丨命令

```text
图片操作帮助
图片信息
水平翻转
垂直翻转
旋转 90
缩放 50%
缩放 300x200
裁剪 300x300
灰度化
反色
颜色滤镜 #ff0000
幻影坦克
水平拼接
垂直拼接
图片抠图
gif分解
gif合成 0.08
gif反转
加速0.5
加速1.5
加速10
```

> 命令可以直接发送，也可以加 `图片操作` / `imagetools` 前缀，例如 `图片操作旋转 90`、`imagetools缩放 50%`。
>
> 使用时请带图发送命令，或回复图片后发送命令。`幻影坦克`、图片拼接、`gif合成` 等多图功能需要至少两张图片。

## 丨使用限制

> [!CAUTION]
> 本插件主要处理用户上传或回复的图片，单张图片读取大小限制为 **30MB**。
>
> GIF 分解会返回 zip 文件，并默认预览前若干帧；大型 GIF 处理可能需要较长时间。
>
> 抠图功能依赖外部服务，速度与稳定性取决于服务状态。

## 丨其他

- 本项目从 [CandriaJS/karin-plugin-imagetools](https://github.com/CandriaJS/karin-plugin-imagetools) 移植到 GsCore / Python 生态
- 本项目仅供学习使用，请勿用于商业用途
- [GPL-3.0 License](LICENSE)

## 丨致谢

- [CandriaJS](https://github.com/CandriaJS)
- [karin-plugin-imagetools](https://github.com/CandriaJS/karin-plugin-imagetools)
- [gsuid_core](https://github.com/Genshin-bots/gsuid_core)
