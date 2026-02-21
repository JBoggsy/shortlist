"""LLM factory — thin re-export layer.

After the LangChain migration, model creation goes through
``langchain_factory.create_langchain_model`` and model listing
through ``model_listing.list_models``.  This module re-exports
them for convenience so existing import paths keep working.
"""

from backend.llm.langchain_factory import create_langchain_model  # noqa: F401
from backend.llm.model_listing import list_models, MODEL_LISTERS  # noqa: F401
