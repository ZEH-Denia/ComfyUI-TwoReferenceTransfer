import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

app.registerExtension({
    name: "TwoReferenceTransfer.PromptPreview",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "TwoReferenceAnalyze") return;
        const previous = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function (message) {
            previous?.apply(this, arguments);
            for (const [key, label] of [
                ["reference_analysis", "图二分析（可复制）"],
                ["transfer_prompt", "最终提示词（可复制）"],
            ]) {
                if (!message[key]) continue;
                this.transferPreviews ??= {};
                let widget = this.transferPreviews[key];
                if (!widget) {
                    widget = ComfyWidgets.STRING(this, label, ["STRING", { multiline: true }], app).widget;
                    widget.inputEl.readOnly = true;
                    widget.options.serialize = false;
                    this.transferPreviews[key] = widget;
                }
                widget.value = message[key].join("\n");
            }
            this.setSize([Math.max(this.size[0], 500), Math.max(this.size[1], 720)]);
            this.setDirtyCanvas(true, true);
        };
    },
});
