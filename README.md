# ImageTools

适用于 **GsCore** 的图片处理插件。

> 本项目是从 [CandriaJS/karin-plugin-imagetools](https://github.com/CandriaJS/karin-plugin-imagetools) 移植而来的 **GsCore / Python 版本插件**。  
> 原项目面向 Karin / Node.js 生态，本仓库将其中常用的图片操作能力移植到 GsCore 插件结构中，便于在 GsCore Bot 中直接使用。  
> 感谢原项目作者 CandriaJS 及相关贡献者。

## 项目说明

`ImageTools` 提供常见图片处理、图片拼接、GIF 处理以及抠图能力。插件支持用户发送图片时直接带命令，或回复一张 / 多张图片后发送命令处理。

当前仓库是移植版，不是原 Karin 插件本体：

- 原项目：`CandriaJS/karin-plugin-imagetools`
- 原框架：Karin / Node.js
- 当前项目：`MimoKit/ImageTools`
- 当前框架：GsCore / Python
- 当前依赖：`Pillow`、`httpx`、`gradio-client`

## 功能列表

### 基础图片处理

- 图片信息：查看图片分辨率、格式、是否为动图、帧数等信息
- 水平翻转：左右镜像图片
- 垂直翻转：上下镜像图片
- 旋转：按指定角度旋转图片
- 缩放：按百分比或指定尺寸缩放图片
- 裁剪：按坐标、尺寸或比例裁剪图片
- 灰度化：转换为灰度图片
- 反色：反转图片颜色
- 颜色滤镜：叠加指定颜色滤镜
- 幻影坦克：使用两张图片生成幻影坦克效果
- 图片抠图：调用 Anime Background Remover / Gradio 服务进行背景移除

### 图片拼接

- 水平拼接：将多张图片横向拼接
- 垂直拼接：将多张图片纵向拼接

### GIF 处理

- GIF 分解：将 GIF 拆分为单帧图片，并返回 zip 文件
- GIF 合成：将多张图片合成为 GIF
- GIF 反转：反转 GIF 帧顺序
- GIF 加速：按倍率调整 GIF 播放速度

## 安装方式

进入 GsCore 插件目录后克隆本仓库：

```bash
cd gsuid_core/gsuid_core/plugins
git clone https://github.com/MimoKit/ImageTools.git ImageTools
```

目录应类似：

```text
gsuid_core/plugins/ImageTools
```

或在你的机器人插件目录中保留本项目结构：

```text
ImageTools/
├── __init__.py
├── __nest__.py
├── pyproject.toml
├── README.md
└── ImageTools/
    ├── __init__.py
    ├── __full__.py
    ├── version.py
    ├── imagetools_config/
    └── imagetools_core/
```

依赖声明在 `pyproject.toml` 中：

```toml
dependencies = [
    "Pillow>=10.0.0",
    "httpx>=0.25.0",
    "gradio-client>=1.0.0",
]
```

GsCore 支持插件依赖安装时，通常会根据 `pyproject.toml` 自动处理依赖；如果你的环境未自动安装，请手动安装：

```bash
pip install Pillow httpx gradio-client
```

安装完成后重启 GsCore 即可加载插件。

## 使用方法

发送命令时可以：

1. 直接发送图片并带命令；
2. 回复一张图片后发送命令；
3. 多图功能需要发送或回复多张图片。

插件允许无强制前缀触发，也支持可选写法：

```text
图片操作帮助
imagetools help
#图片信息
```

### 帮助

```text
图片操作帮助
图片操作菜单
imagetools help
```

### 图片信息

```text
图片信息
查看图片信息
imageinfo
```

### 基础处理命令

```text
水平翻转
垂直翻转
旋转 90
缩放 50%
缩放 300x200
缩放 300x
裁剪 0,0,300,300
裁剪 300x300
裁剪 1:1
灰度化
反色
颜色滤镜 255,0,0
颜色滤镜 #ff0000
```

命令也可以加 `图片操作` / `imagetools` 前缀，例如：

```text
图片操作旋转 90
imagetools缩放 50%
#图片信息
```

### 幻影坦克

需要两张图片：

```text
幻影坦克
```

### 图片拼接

需要至少两张图片：

```text
水平拼接
垂直拼接
```

### 图片抠图

```text
图片抠图
抠图
```

默认使用 HuggingFace Space：

```text
https://skytnt-anime-remove-background.hf.space
```

也可以在插件配置中设置自定义 `matting_server_url`。

### GIF 命令

```text
gif分解
gif合成 0.08
gif反转
加速 1.5
加速 2.0
```

说明：

- `gif分解` 会返回 zip 文件，并预览前若干帧；
- `gif合成 0.08` 表示每帧间隔约 `0.08` 秒；
- `加速 1.5` 表示按 1.5 倍速度调整 GIF；
- 加速命令不需要写 `gif` 前缀，直接发送 `加速0.5` / `加速10` / `加速1.5` 即可。

## 配置项

配置文件由插件写入 GsCore 数据目录：

```text
data/ImageTools/console_config.json
```

当前配置项：

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `matting_server_url` | Anime Background Remover / Gradio 抠图服务地址 | 空，使用默认 HuggingFace Space |

如果默认 HuggingFace Space 无法访问，建议自行部署兼容的 Gradio 服务，并将地址填入 `matting_server_url`。

## 注意事项

- 本插件主要处理用户上传或回复的图片；
- 单张图片读取大小限制为 `30MB`；
- GIF 分解预览默认最多展示前 `24` 帧，完整结果以 zip 文件形式发送；
- 抠图功能依赖外部 Gradio 服务，速度和稳定性取决于服务可用性；
- 当前项目是移植版，命令表现和原 Karin 插件可能不完全一致，以本仓库代码为准。

## 常见问题

### 提示没有找到图片

请确认发送命令时同时带图，或回复一张图片后再发送命令。多图功能例如 `幻影坦克`、`水平拼接`、`垂直拼接`、`gif合成` 需要至少两张图片。

### 抠图很慢或失败

默认抠图服务使用 HuggingFace Space，网络、排队和冷启动都会影响速度。建议在插件配置里填写自建 Gradio 抠图服务地址。

### GIF 加速参数怎么写

直接写倍速即可：

```text
加速0.5
加速1.5
加速10
```

不要写成 `gif加速1.5x` 这类格式。

## 移植来源与致谢

本项目移植自：

- [CandriaJS/karin-plugin-imagetools](https://github.com/CandriaJS/karin-plugin-imagetools)

原项目是 Karin 生态下的图片操作插件。本仓库将其核心图片处理思路和常用能力迁移到 GsCore 插件体系中，并使用 Python / Pillow 等依赖重写实现。

感谢原项目作者与贡献者提供的功能设计和实现参考。

## License

本仓库保留原项目的开源许可证文件，详见 [LICENSE](./LICENSE)。
