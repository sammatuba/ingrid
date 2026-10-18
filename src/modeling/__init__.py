"""M0 structured-data baseline evaluation harness (synthetic, stdlib only).

Public interface::

    from src.modeling import (
        build_input, build_config, build_partition,  # strict parsing
        run_evaluation,                              # evaluate one input
        PersistenceProvider, SeasonalNaiveProvider,
        default_providers, builtin_providers_by_name,
        EvaluationInput, EvaluationConfig, Partition, Observation,
        EvaluationReport, EvaluationOutcome,
        ModelingError,
    )

Scope: one entity and one unit per call; history and truth are separated; the
provider port is a pure in-process prediction function.  Only labeled synthetic
input is supported.  This harness does not run TimesFM/TabFM, contact a cloud
service, write files or authorize external execution.
"""
from .errors import ALL_CODES, MESSAGES, ModelingError, ModelingValidationError
from .providers import (
    BaselineProvider,
    ContextObservation,
    ContextView,
    PersistenceProvider,
    Prediction,
    ProviderError,
    ProviderLookupError,
    SeasonalNaiveProvider,
    builtin_providers_by_name,
    default_providers,
)
from .records import (
    BuildResult,
    EvaluationConfig,
    EvaluationInput,
    Observation,
    Partition,
    build_config,
    build_input,
    build_partition,
    compute_input_digest,
    is_utf8_text,
    revalidate_input,
    safe_finite_float,
)
from .evaluation import (
    ContextCounts,
    EvaluationOutcome,
    EvaluationReport,
    ExclusionCount,
    Forecast,
    LeadMetric,
    ModelInfo,
    ModelSummary,
    OriginReport,
    filter_context,
    report_to_dict,
    run_evaluation,
)

__all__ = [
    "ALL_CODES",
    "BaselineProvider",
    "BuildResult",
    "ContextCounts",
    "ContextObservation",
    "ContextView",
    "EvaluationConfig",
    "EvaluationInput",
    "EvaluationOutcome",
    "EvaluationReport",
    "ExclusionCount",
    "Forecast",
    "LeadMetric",
    "MESSAGES",
    "ModelInfo",
    "ModelSummary",
    "ModelingError",
    "ModelingValidationError",
    "Observation",
    "OriginReport",
    "Partition",
    "PersistenceProvider",
    "Prediction",
    "ProviderError",
    "ProviderLookupError",
    "SeasonalNaiveProvider",
    "build_config",
    "build_input",
    "build_partition",
    "builtin_providers_by_name",
    "compute_input_digest",
    "default_providers",
    "filter_context",
    "is_utf8_text",
    "report_to_dict",
    "revalidate_input",
    "run_evaluation",
    "safe_finite_float",
]
