# ComfyUI Two Reference Transfer

双参考图人物迁移：先单独分析图一的发型、发色、眼睛等人物特征，再分析图二的场景。图一提供人物身份；图二提供动作、表情、服装、环境、构图与光线。分析节点输出完整的可见要素描述与融合提示词，再由 FLUX.2 Klein 同时参考两张图生成结果。

## 两种分析方案

- **本地 Qwen3-VL**：在本机分析图二，首次使用会加载约 4.26 GB 的视觉模型。节点执行后释放视觉模型，随后运行出图模型。
- **DSH（云端看图）**：通过当前用户的 dsh-baton 本地套接字连接已登录的 DeepSeek Harness 桌面端，交给其当前默认模型看图。无需另填 API Key。两张图会交给 Harness 所连接的服务，以分别提取人物身份与场景要素。需要 Harness 与 `dsh-baton-host` 正在运行。每次新的自动分析会在 Harness 中创建分析对话。

两种方案使用相同的图像生成模型，均同时参考图一与图二；文字描述不是唯一条件。

## 使用

1. 在 Anime Local 的工作流列表打开“**双参考图-本地分析**”或“**双参考图-DSH分析**”。
2. 左上上传图一人物，左下上传图二动作、衣着和场景。
3. 选择是否保留图一画风；可填写补充要求。
4. 点击运行。分析节点会显示“图二分析”和“最终提示词”，可选择并复制；结果保存在 `ComfyUI-Shared/output/TwoReference/`。

若分析有误，把展示的 JSON 复制到“自定义分析 JSON”后修改。该字段非空时直接使用修改后的描述，跳过分析服务。默认图像比例跟随图二，约 0.59 百万像素、4 步、CFG 1；内部采用原生 ComfyUI 节点。

对衣服纹样、复杂手部、遮挡和多人场景，模型仍可能遗漏或误判。这里生成的是可见要素描述，不能反推出图片原本的完整提示词，也不保证逐像素复刻。两张图中人物清晰、图二主要只有一个人物时更容易控制。

## 安装与模型

将本目录放进 `ComfyUI/custom_nodes/`，使用 ComfyUI 的 Python 安装 `requirements.txt`，然后重启 ComfyUI。当前这台 Mac 已安装所需依赖。

本地分析权重为单个文件：

`models/text_encoders/qwen3-vl-2b-instruct.safetensors`

从 [Qwen/Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) 下载 `model.safetensors` 并改为上述名称。SHA-256：

`7de1838c87a5349b016c26a1c3f7d2bc400a3d485f95ef39a7059ffd734977a0`

`resources/qwen3-vl-2b/` 内包含同版本的处理器、词表和配置文件。运行时只读本地模型，不自动联网下载。

出图模型使用已经配置的 FLUX.2 Klein 4B、Qwen3 4B 文本编码器、Flux2 VAE。DSH 方案仅适配当前 macOS 的 Unix 套接字接口。

## 验证

`python -m unittest discover -s tests -v`

运行时取消操作会中止本地分析，或取消本插件创建的 DSH 分析任务；不会取消其他 Harness 会话。

## 来源

- [ComfyUI](https://github.com/Comfy-Org/ComfyUI) 与其原生 FLUX.2 工作流。
- [Qwen3-VL](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)，配置、词表和权重遵循 Apache 2.0。
- [dsh-baton](https://github.com/JialaoLiu/dsh-baton)，使用其文档公开的本地套接字协议；本插件不复制其实现，不修改 Harness 配置，不读取 API Key。
