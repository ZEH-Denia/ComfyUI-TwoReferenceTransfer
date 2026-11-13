from comfy_api.latest import ComfyExtension
from .nodes import TwoReferenceAnalyze

WEB_DIRECTORY = "./web"


class TwoReferenceExtension(ComfyExtension):
    async def get_node_list(self):
        return [TwoReferenceAnalyze]


async def comfy_entrypoint():
    return TwoReferenceExtension()
