"""Pipeline base class — shared infrastructure for fixed pipelines."""

import logging

from langchain_core.language_models import BaseChatModel

from .context import RequestContext
from .streaming import execute_tool_with_events, yield_text

logger = logging.getLogger(__name__)


class ToolResult:
    """Container for tool execution results, used with exec_tool()."""

    def __init__(self):
        self.data: dict = {}

    @property
    def is_error(self) -> bool:
        return "error" in self.data

    @property
    def error(self) -> str:
        return self.data.get("error", "")


class Pipeline:
    """Base class for fixed pipelines.

    Subclasses set ``params_schema`` to a Pydantic model and implement
    ``execute()`` as a generator yielding SSE event dicts.
    """

    params_schema = None  # Subclass sets this to a Pydantic model

    def __init__(self, model: BaseChatModel, params: dict, ctx: RequestContext):
        self.model = model
        self.ctx = ctx
        pipeline_name = type(self).__name__
        if self.params_schema:
            self.params = self.params_schema.model_validate(params)
            logger.info("[%s] initialized — params=%s", pipeline_name, self.params)
        else:
            self.params = params
            logger.info("[%s] initialized — raw params=%s", pipeline_name, params)

    def exec_tool(self, name: str, arguments: dict, tr: ToolResult | None = None):
        """Execute a tool, yielding SSE events. Stores result in *tr* if provided."""
        pipeline_name = type(self).__name__
        logger.info("[%s] exec_tool '%s' — args=%s", pipeline_name, name, arguments)
        result, events = execute_tool_with_events(self.ctx, name, arguments)
        if tr is not None:
            tr.data = result
        if "error" in result:
            logger.warning("[%s] exec_tool '%s' — error: %s", pipeline_name, name, result["error"])
        else:
            # Log a summary of the result (truncated to avoid huge logs)
            summary = str(result)[:200]
            logger.info("[%s] exec_tool '%s' — ok: %s", pipeline_name, name, summary)
        yield from events

    def text(self, content: str) -> dict:
        """Create a text_delta SSE event."""
        return yield_text(content)

    def execute(self):
        """Override in subclass. Yield SSE event dicts."""
        raise NotImplementedError
