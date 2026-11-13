import json

import numpy as np
from PIL import Image

from comfy_api.latest import io

from .backends import analyze_local
from .dsh_bridge import analyze_dsh
from .prompting import compose_prompt, parse_analysis


class TwoReferenceAnalyze(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="TwoReferenceAnalyze",
            display_name="图二分析 · 双参考图提示词",
            category="Two Reference Transfer",
            is_output_node=True,
            description="分别提取图一身份特征与图二的动作、表情、服装、环境和构图。DSH 后端会将两张图发送给 DeepSeek Harness 所选模型。",
            inputs=[
                io.Image.Input("identity_image", display_name="图一 · 人物身份"),
                io.Image.Input("reference_image", display_name="图二 · 动作服装场景"),
                io.Combo.Input("backend", options=["本地 Qwen3-VL", "DSH（云端看图）"], default="本地 Qwen3-VL", display_name="分析后端"),
                io.Boolean.Input("keep_identity_style", default=True, display_name="保留图一画风"),
                io.String.Input("extra_requirements", default="", multiline=True, display_name="补充要求"),
                io.String.Input("analysis_override", default="", multiline=True, advanced=True, display_name="自定义分析 JSON（留空自动）"),
            ],
            outputs=[
                io.String.Output(display_name="图二完整描述 JSON"),
                io.String.Output(display_name="人物迁移提示词"),
            ],
        )

    @classmethod
    def execute(cls, identity_image, reference_image, backend, keep_identity_style, extra_requirements, analysis_override=""):
        if reference_image.shape[0] != 1 or identity_image.shape[0] != 1:
            raise ValueError("两个输入各需要一张静态参考图；请从动画或批量图像中选取一帧。")
        if analysis_override.strip():
            raw = analysis_override
        else:
            pixels = reference_image[0, :, :, :3].detach().cpu().numpy()
            image = Image.fromarray(np.rint(pixels * 255).clip(0, 255).astype(np.uint8), "RGB")
            image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            identity_pixels = identity_image[0, :, :, :3].detach().cpu().numpy()
            identity = Image.fromarray(np.rint(identity_pixels * 255).clip(0, 255).astype(np.uint8), "RGB")
            identity.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            raw = analyze_dsh(image, identity) if backend.startswith("DSH") else analyze_local(image, identity)
        try:
            analysis = parse_analysis(raw)
        except ValueError as exc:
            raise ValueError(str(exc) + "\n收到的分析：\n" + raw) from exc
        description = json.dumps(analysis, ensure_ascii=False, indent=2)
        prompt = compose_prompt(analysis, keep_identity_style, extra_requirements)
        return io.NodeOutput(description, prompt, ui={"reference_analysis": [description], "transfer_prompt": [prompt]})
