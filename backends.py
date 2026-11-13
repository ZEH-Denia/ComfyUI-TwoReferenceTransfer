import gc
from pathlib import Path

import torch
from safetensors.torch import load_file
from transformers import AutoProcessor, Qwen3VLConfig, Qwen3VLForConditionalGeneration, StoppingCriteria

import comfy.model_management as mm
import folder_paths

from .prompting import ANALYSIS_INSTRUCTION

RESOURCES = Path(__file__).parent / "resources" / "qwen3-vl-2b"
MODEL_FILE = "qwen3-vl-2b-instruct.safetensors"


class ComfyCancellation(StoppingCriteria):
    def __call__(self, input_ids, scores, **kwargs):
        mm.throw_exception_if_processing_interrupted()
        return False


def analyze_local(image, identity_image):
    checkpoint = folder_paths.get_full_path_or_raise("text_encoders", MODEL_FILE)
    mm.unload_all_models()
    mm.soft_empty_cache(force=True)
    device = mm.get_torch_device()
    dtype = torch.float32 if device.type == "cpu" else torch.bfloat16
    model = weights = inputs = generated = None
    try:
        config = Qwen3VLConfig.from_pretrained(str(RESOURCES), local_files_only=True)
        weights = load_file(checkpoint, device="cpu")
        model = Qwen3VLForConditionalGeneration.from_pretrained(
            None, config=config, state_dict=weights, dtype=dtype,
            attn_implementation="sdpa", local_files_only=True,
        ).to(device)
        weights = None
        processor = AutoProcessor.from_pretrained(str(RESOURCES), local_files_only=True)
        messages = [{"role": "user", "content": [
            {"type": "text", "text": "Image 1: character identity only."},
            {"type": "image", "image": identity_image},
            {"type": "text", "text": "Image 2: pose, expression, clothes and scene only."},
            {"type": "image", "image": image},
            {"type": "text", "text": ANALYSIS_INSTRUCTION},
        ]}]
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        ).to(device)
        mm.throw_exception_if_processing_interrupted()
        generated = model.generate(
            **inputs, max_new_tokens=768, do_sample=False,
            stopping_criteria=[ComfyCancellation()],
        )
        answer = generated[:, inputs.input_ids.shape[1]:]
        return processor.batch_decode(answer, skip_special_tokens=True)[0]
    finally:
        model = weights = inputs = generated = None
        gc.collect()
        mm.soft_empty_cache(force=True)

