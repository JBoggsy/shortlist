"""Multi-step pipeline — orchestrate sub-pipelines sequentially."""

import logging

from ..pipeline_base import Pipeline
from ..schemas import MultiStepParams

logger = logging.getLogger(__name__)


class MultiStepPipeline(Pipeline):
    params_schema = MultiStepParams

    def execute(self):
        p = self.params

        if not p.steps:
            yield self.text("I couldn't break that down into steps. Could you be more specific?")
            return

        # Import registry here to avoid circular imports
        from . import PIPELINE_REGISTRY

        total = len(p.steps)
        for i, step in enumerate(p.steps, 1):
            step_type = step.get("type", "general")
            step_params = step.get("params", {})

            pipeline_fn = PIPELINE_REGISTRY.get(step_type)
            if not pipeline_fn:
                yield self.text(f"\nStep {i}/{total}: Unknown step type '{step_type}', skipping.\n")
                continue

            yield self.text(f"\n**Step {i}/{total}:** ")

            try:
                yield from pipeline_fn(self.model, step_params, self.ctx)
            except Exception as e:
                logger.exception("Multi-step: step %d/%d failed", i, total)
                yield self.text(f"\nStep {i} encountered an error: {e}\n")

            if i < total:
                yield self.text("\n\n---\n")

        yield self.text(f"\n\nAll {total} steps complete.")


def run(model, params, ctx):
    yield from MultiStepPipeline(model, params, ctx).execute()
