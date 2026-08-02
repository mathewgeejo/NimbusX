"""Deterministic operational screening rules for stored portfolio assets.

These rules consume already-normalized findings.  They never alter hazard
metrics, create a probability, or turn missing exposure/vulnerability data into
an asset-risk decision.  A result is an operational review prompt, not a
regulatory, safety, or engineering certification.
"""

from __future__ import annotations

from .catalog import get_template
from .schemas import (
    FindingStatus,
    HazardFinding,
    OperationalFindingStatus,
    OperationalRiskFinding,
    PortfolioAsset,
    Severity,
)

_SEVERITY_RANK = {
    Severity.LOW: 1,
    Severity.MODERATE: 2,
    Severity.HIGH: 3,
    Severity.UNKNOWN: 0,
}


def severity_at_least(value: Severity, minimum: Severity) -> bool:
    """Compare the published screening severity labels without inventing a score."""

    return _SEVERITY_RANK[value] >= _SEVERITY_RANK[minimum]


def _missing_fields(values: dict[str, object], required: list[str]) -> list[str]:
    missing: list[str] = []
    for field in required:
        value = values.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def evaluate_operational_rules(
    asset: PortfolioAsset,
    findings: list[HazardFinding],
) -> tuple[list[OperationalRiskFinding], list[str]]:
    """Evaluate complete template context against source-backed hazard findings.

    A template may be deliberately incomplete while an asset is being onboarded.
    In that case the result says exactly which fields are missing and does not
    issue an action-required result.
    """

    template = get_template(asset.template_id)
    if template is None:
        # Creation validates the template.  This guard preserves the no-fabrication
        # boundary if a catalog version is removed after an asset was stored.
        return (
            [],
            [
                f"Asset template '{asset.template_id}' is no longer available; operational rules were not evaluated."
            ],
        )

    by_hazard = {finding.hazard: finding for finding in findings}
    template_exposure = [field.key for field in template.required_exposure_fields if field.required]
    template_vulnerability = [
        field.key for field in template.required_vulnerability_fields if field.required
    ]
    results: list[OperationalRiskFinding] = []

    for rule in template.operational_rules:
        finding = by_hazard.get(rule.hazard)
        if finding is None:
            continue

        required_exposure = list(
            dict.fromkeys([*template_exposure, *rule.required_exposure_fields])
        )
        required_vulnerability = list(
            dict.fromkeys([*template_vulnerability, *rule.required_vulnerability_fields])
        )
        missing_exposure = _missing_fields(asset.exposure, required_exposure)
        missing_vulnerability = _missing_fields(asset.vulnerability, required_vulnerability)

        if finding.status != FindingStatus.AVAILABLE:
            results.append(
                OperationalRiskFinding(
                    asset_id=asset.id,
                    template_id=asset.template_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    hazard=rule.hazard,
                    status=OperationalFindingStatus.SOURCE_UNAVAILABLE,
                    source_finding_status=finding.status,
                    source_severity=finding.severity,
                    evidence_ids=finding.evidence_ids,
                    rationale=(
                        "The associated hazard finding is unavailable, so this operational rule "
                        "was not evaluated."
                    ),
                    missing_exposure_fields=missing_exposure,
                    missing_vulnerability_fields=missing_vulnerability,
                )
            )
            continue

        if missing_exposure or missing_vulnerability:
            results.append(
                OperationalRiskFinding(
                    asset_id=asset.id,
                    template_id=asset.template_id,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    hazard=rule.hazard,
                    status=OperationalFindingStatus.INSUFFICIENT_CONTEXT,
                    source_finding_status=finding.status,
                    source_severity=finding.severity,
                    evidence_ids=finding.evidence_ids,
                    rationale=(
                        "Asset exposure and vulnerability context is incomplete; NimbusX did not "
                        "calculate an operational rule outcome."
                    ),
                    missing_exposure_fields=missing_exposure,
                    missing_vulnerability_fields=missing_vulnerability,
                )
            )
            continue

        matched = severity_at_least(finding.severity, rule.minimum_severity)
        results.append(
            OperationalRiskFinding(
                asset_id=asset.id,
                template_id=asset.template_id,
                rule_id=rule.id,
                rule_name=rule.name,
                hazard=rule.hazard,
                status=(
                    OperationalFindingStatus.ACTION_REQUIRED
                    if matched
                    else OperationalFindingStatus.MONITORED
                ),
                source_finding_status=finding.status,
                source_severity=finding.severity,
                evidence_ids=finding.evidence_ids,
                action=rule.action if matched else None,
                rationale=(
                    rule.rationale
                    if matched
                    else (
                        "The source-backed hazard finding did not meet this rule's published "
                        "screening severity."
                    )
                ),
            )
        )

    limitations = [
        "Operational rule outcomes are template screening prompts based on completed source-backed hazard findings; they are not forecasts, asset-risk verdicts, engineering advice, or certification."
    ]
    return results, limitations
