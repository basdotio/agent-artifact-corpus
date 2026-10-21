"""Schema package — Pydantic boundary models of the design-pattern selection pipeline
(docs/implementation-guide.md §4–§11).

Exports the schema symbols imported through this package for FastMCP tool I/O boundaries and
validation; the Modules list below maps the package layout (import a submodule directly for
symbols not re-exported here).

Modules:
- enums: Language, SupportLevel, Paradigm, Provenance, PatternScope, PatternCategory,
         QUALITY_AXES, FALLBACK_PRIMARY
- quality: QualityMetrics
- variants: VariantSummary, LanguageBinding
- patterns: PatternRecord, PatternParticipantRole
- analysis: RawBriefAndParts and the repaired DesignBrief/DecisionPart forms, RequirementWeights
- selection: Adjustment, AnnotatedCandidate, SupportingChoice, PartSelection, AnalysisResult
- generation: GenerationSeed, CatalogSlice, ApplicationSeed, Raw* GENERATE payload
- design: DesignOverview, DesignResult and their parts
- evaluation: EvaluationFinding, DesignEvaluation, MetricResult, EvaluationSummary, PipelineResult
"""

from src.schemas.analysis import (
    BriefAndParts,
    BriefComponent,
    BriefFlow,
    DecisionPart,
    DesignBrief,
    RawBriefAndParts,
    RawBriefComponent,
    RawBriefFlow,
    RawDecisionPart,
    RawDesignBrief,
    RequirementWeights,
    RequirementWeightsBatch,
)
from src.schemas.design import (
    ApplicationInteraction,
    DesignOverview,
    DesignResult,
    Interaction,
    Participant,
    PatternApplication,
    Risk,
    SupportingPattern,
    TestStrategy,
)
from src.schemas.enums import (
    FALLBACK_PRIMARY,
    QUALITY_AXES,
    Language,
    Paradigm,
    PatternCategory,
    PatternScope,
    Provenance,
    SupportLevel,
)
from src.schemas.evaluation import (
    DesignEvaluation,
    EvaluationFinding,
    EvaluationSummary,
    MetricResult,
    PipelineResult,
)
from src.schemas.generation import (
    ApplicationSeed,
    CatalogSlice,
    GenerationSeed,
    InteractionSeed,
    ParticipantSpec,
    RawApplication,
    RawApplicationInteraction,
    RawGeneration,
    RawParticipant,
)
from src.schemas.patterns import PatternParticipantRole, PatternRecord
from src.schemas.quality import QualityMetrics
from src.schemas.selection import (
    Adjustment,
    AnalysisResult,
    AnnotatedCandidate,
    PartSelection,
    SupportingChoice,
)
from src.schemas.variants import LanguageBinding, VariantSummary

__all__ = [
    # enums
    "FALLBACK_PRIMARY",
    "QUALITY_AXES",
    "Language",
    "Paradigm",
    "PatternCategory",
    "PatternScope",
    "Provenance",
    "SupportLevel",
    # quality
    "QualityMetrics",
    # variants
    "LanguageBinding",
    "VariantSummary",
    # patterns
    "PatternParticipantRole",
    "PatternRecord",
    # analysis
    "BriefAndParts",
    "BriefComponent",
    "BriefFlow",
    "DecisionPart",
    "DesignBrief",
    "RawBriefAndParts",
    "RawBriefComponent",
    "RawBriefFlow",
    "RawDecisionPart",
    "RawDesignBrief",
    "RequirementWeights",
    "RequirementWeightsBatch",
    # selection
    "Adjustment",
    "AnalysisResult",
    "AnnotatedCandidate",
    "PartSelection",
    "SupportingChoice",
    # generation
    "ApplicationSeed",
    "CatalogSlice",
    "GenerationSeed",
    "InteractionSeed",
    "ParticipantSpec",
    "RawApplication",
    "RawApplicationInteraction",
    "RawGeneration",
    "RawParticipant",
    # design
    "ApplicationInteraction",
    "DesignOverview",
    "DesignResult",
    "Interaction",
    "Participant",
    "PatternApplication",
    "Risk",
    "SupportingPattern",
    "TestStrategy",
    # evaluation
    "DesignEvaluation",
    "EvaluationFinding",
    "EvaluationSummary",
    "MetricResult",
    "PipelineResult",
]
