"""Optimization blueprint — trigger DSPy BootstrapFewShot and check readiness."""

import json
import logging
from datetime import datetime, timezone

import dspy
from flask import Blueprint, jsonify, request

from backend.database import db
from backend.models.dspy_example import DspyExample
from backend.agent.fixed_pipeline.feedback import evaluator_metric, query_gen_metric
from backend.agent.fixed_pipeline.module_store import (
    get_last_modified,
    has_optimized_module,
    save_module,
)

logger = logging.getLogger(__name__)

optimize_bp = Blueprint("optimize", __name__, url_prefix="/api/optimize")

# Module configs: module_name → (DSPy module class, input field names, metric fn)
_MODULE_CONFIGS = {
    "evaluator": {
        "input_fields": ["job_context", "job_results"],
        "metric": evaluator_metric,
    },
    "query_generator": {
        "input_fields": ["search_criteria", "user_profile"],
        "metric": query_gen_metric,
    },
}

_MIN_EXAMPLES = 10


@optimize_bp.route("", methods=["POST"])
def run_optimization():
    """Run BootstrapFewShot optimization on modules with enough scored examples."""
    from backend.agent.fixed_pipeline.dspy_modules import EvaluatorModule, QueryGeneratorModule
    from backend.agent.fixed_pipeline.dspy_lm import LangChainLM, create_dspy_lm
    from backend.llm.langchain_factory import create_langchain_model
    from backend.config_manager import get_llm_config

    # Ensure DSPy is configured with the current LLM
    llm_config = get_llm_config()
    if not llm_config.get("provider") or not llm_config.get("api_key"):
        return jsonify({"error": "LLM not configured"}), 503

    langchain_model = create_langchain_model(
        llm_config["provider"], llm_config["api_key"], llm_config.get("model", "")
    )
    dspy_lm = create_dspy_lm(langchain_model)

    # Optional teacher model
    teacher_lm = None
    body = request.get_json(silent=True) or {}
    teacher_config = body.get("teacher_model")
    if teacher_config and teacher_config.get("provider") and teacher_config.get("api_key"):
        teacher_model = create_langchain_model(
            teacher_config["provider"],
            teacher_config["api_key"],
            teacher_config.get("model", ""),
        )
        teacher_lm = LangChainLM(teacher_model)

    module_classes = {
        "evaluator": EvaluatorModule,
        "query_generator": QueryGeneratorModule,
    }

    modules_optimized = []
    examples_used = {}
    errors = {}

    # Use dspy.context so the LM is set per-thread (avoids cross-thread RuntimeError)
    with dspy.context(lm=dspy_lm):
        for module_name, config in _MODULE_CONFIGS.items():
            # Query scored examples
            scored = DspyExample.query.filter(
                DspyExample.module_name == module_name,
                DspyExample.score.isnot(None),
            ).all()

            if len(scored) < _MIN_EXAMPLES:
                errors[module_name] = f"Insufficient examples: {len(scored)}/{_MIN_EXAMPLES}"
                continue

            # Convert to dspy.Example objects
            trainset = []
            for ex in scored:
                inputs = json.loads(ex.inputs_json)
                dspy_ex = dspy.Example(
                    **{k: inputs.get(k, "") for k in config["input_fields"]},
                    score=ex.score,
                ).with_inputs(*config["input_fields"])
                trainset.append(dspy_ex)

            # Build and run optimizer
            try:
                module = module_classes[module_name]()
                optimizer_kwargs = {
                    "metric": config["metric"],
                    "max_bootstrapped_demos": 4,
                    "max_labeled_demos": 8,
                }
                if teacher_lm:
                    optimizer_kwargs["teacher_settings"] = {"lm": teacher_lm}

                optimizer = dspy.BootstrapFewShot(**optimizer_kwargs)
                compiled = optimizer.compile(module, trainset=trainset)

                save_module(module_name, compiled)
                modules_optimized.append(module_name)
                examples_used[module_name] = len(trainset)
                logger.info("Optimized module '%s' with %d examples", module_name, len(trainset))
            except Exception as e:
                logger.warning("Optimization failed for '%s': %s", module_name, e)
                errors[module_name] = str(e)

    result = {
        "status": "success" if modules_optimized else "no_modules_optimized",
        "modules_optimized": modules_optimized,
        "examples_used": examples_used,
    }
    if errors:
        result["errors"] = errors

    return jsonify(result)


@optimize_bp.route("/status", methods=["GET"])
def optimization_status():
    """Check readiness for optimization — per-module example counts and optimization state."""
    status = []

    for module_name in _MODULE_CONFIGS:
        scored_count = DspyExample.query.filter(
            DspyExample.module_name == module_name,
            DspyExample.score.isnot(None),
        ).count()

        unscored_count = DspyExample.query.filter(
            DspyExample.module_name == module_name,
            DspyExample.score.is_(None),
        ).count()

        last_mod = get_last_modified(module_name)
        last_optimized = (
            datetime.fromtimestamp(last_mod, tz=timezone.utc).isoformat()
            if last_mod else None
        )

        status.append({
            "module_name": module_name,
            "scored_count": scored_count,
            "unscored_count": unscored_count,
            "min_required": _MIN_EXAMPLES,
            "ready": scored_count >= _MIN_EXAMPLES,
            "has_optimized_module": has_optimized_module(module_name),
            "last_optimized": last_optimized,
        })

    return jsonify(status)
