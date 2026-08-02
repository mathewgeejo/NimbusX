"""Published built-asset template catalog.

The catalog is deliberately small and versioned in source.  Templates make
the fields needed for a rule visible to users; they are not a substitute for a
customer's safety case, engineering standard, or regulatory assessment.
"""

from __future__ import annotations

from .schemas import (
    AssetFieldSpec,
    AssetTemplate,
    HazardType,
    OperationalRuleDefinition,
    Severity,
)


def _field(
    key: str,
    label: str,
    description: str,
    *,
    value_type: str = "string",
    allowed_values: tuple[str, ...] = (),
) -> AssetFieldSpec:
    return AssetFieldSpec(
        key=key,
        label=label,
        description=description,
        value_type=value_type,  # type: ignore[arg-type]
        allowed_values=list(allowed_values),
    )


def _rule(
    rule_id: str,
    name: str,
    hazard: HazardType,
    minimum_severity: Severity,
    action: str,
    rationale: str,
    *,
    exposure: tuple[str, ...] = (),
    vulnerability: tuple[str, ...] = (),
) -> OperationalRuleDefinition:
    return OperationalRuleDefinition(
        id=rule_id,
        name=name,
        hazard=hazard,
        minimum_severity=minimum_severity,
        action=action,
        rationale=rationale,
        required_exposure_fields=list(exposure),
        required_vulnerability_fields=list(vulnerability),
    )


ASSET_TEMPLATES: tuple[AssetTemplate, ...] = (
    AssetTemplate(
        id="campus",
        display_name="Campus",
        description="Schools, universities, and multi-building campuses.",
        required_exposure_fields=[
            _field(
                "occupancy_band",
                "Occupancy band",
                "Typical occupancy during the assessed window.",
                value_type="enum",
                allowed_values=("low", "medium", "high"),
            ),
        ],
        required_vulnerability_fields=[
            _field(
                "cooling_resilience",
                "Cooling resilience",
                "Ability to maintain safe conditions during heat.",
                value_type="enum",
                allowed_values=("limited", "standard", "redundant"),
            ),
            _field(
                "drainage_condition",
                "Drainage condition",
                "Current known condition of drainage and surface-water controls.",
                value_type="enum",
                allowed_values=("unknown", "poor", "adequate", "verified"),
            ),
        ],
        supported_hazards=[HazardType.EXTREME_HEAT, HazardType.HEAVY_PRECIPITATION],
        operational_rules=[
            _rule(
                "campus-heat-continuity-v1",
                "Campus heat-continuity review",
                HazardType.EXTREME_HEAT,
                Severity.MODERATE,
                "Review heat-safety staffing, cooling capacity, and continuity plans before the relevant operating window.",
                "A source-backed heat finding met the published screening severity and the template context is complete.",
                exposure=("occupancy_band",),
                vulnerability=("cooling_resilience",),
            ),
            _rule(
                "campus-rain-access-v1",
                "Campus rainfall-access review",
                HazardType.HEAVY_PRECIPITATION,
                Severity.HIGH,
                "Review drainage, pedestrian access, and weatherproofing before the relevant operating window.",
                "A source-backed precipitation finding met the published screening severity and the template context is complete.",
                exposure=("occupancy_band",),
                vulnerability=("drainage_condition",),
            ),
        ],
    ),
    AssetTemplate(
        id="data_center",
        display_name="Data center",
        description="Data centers, server rooms, and critical digital infrastructure.",
        required_exposure_fields=[
            _field(
                "service_criticality",
                "Service criticality",
                "Criticality of the services supported by this asset.",
                value_type="enum",
                allowed_values=("standard", "important", "critical"),
            ),
        ],
        required_vulnerability_fields=[
            _field(
                "cooling_redundancy",
                "Cooling redundancy",
                "Cooling redundancy available at the asset.",
                value_type="enum",
                allowed_values=("none", "n", "n_plus_1", "2n"),
            ),
            _field(
                "backup_power_hours",
                "Backup power hours",
                "Documented backup-power autonomy in hours.",
                value_type="number",
            ),
        ],
        supported_hazards=[HazardType.EXTREME_HEAT, HazardType.WIND],
        operational_rules=[
            _rule(
                "data-center-heat-cooling-v1",
                "Data-center cooling-continuity review",
                HazardType.EXTREME_HEAT,
                Severity.MODERATE,
                "Review cooling headroom, maintenance status, and escalation coverage before the relevant operating window.",
                "A source-backed heat finding met the published screening severity and the template context is complete.",
                exposure=("service_criticality",),
                vulnerability=("cooling_redundancy", "backup_power_hours"),
            ),
            _rule(
                "data-center-wind-continuity-v1",
                "Data-center wind-continuity review",
                HazardType.WIND,
                Severity.HIGH,
                "Review rooftop equipment, fuel logistics, and site-access contingencies before the relevant operating window.",
                "A source-backed daily-mean wind finding met the published screening severity and the template context is complete.",
                exposure=("service_criticality",),
                vulnerability=("backup_power_hours",),
            ),
        ],
    ),
    AssetTemplate(
        id="warehouse",
        display_name="Warehouse",
        description="Warehouses, distribution centers, and logistics facilities.",
        required_exposure_fields=[
            _field(
                "goods_sensitivity",
                "Goods sensitivity",
                "Sensitivity of stored goods to heat, cold, or water exposure.",
                value_type="enum",
                allowed_values=("low", "medium", "high"),
            ),
        ],
        required_vulnerability_fields=[
            _field(
                "roof_condition",
                "Roof condition",
                "Current known condition of roofing and weatherproofing.",
                value_type="enum",
                allowed_values=("unknown", "poor", "adequate", "verified"),
            ),
            _field(
                "drainage_condition",
                "Drainage condition",
                "Current known condition of drainage and surface-water controls.",
                value_type="enum",
                allowed_values=("unknown", "poor", "adequate", "verified"),
            ),
        ],
        supported_hazards=[HazardType.HEAVY_PRECIPITATION, HazardType.WIND],
        operational_rules=[
            _rule(
                "warehouse-rain-protection-v1",
                "Warehouse rainfall-protection review",
                HazardType.HEAVY_PRECIPITATION,
                Severity.MODERATE,
                "Review drainage, dock weatherproofing, and stock-protection procedures before the relevant operating window.",
                "A source-backed precipitation finding met the published screening severity and the template context is complete.",
                exposure=("goods_sensitivity",),
                vulnerability=("roof_condition", "drainage_condition"),
            ),
            _rule(
                "warehouse-wind-operations-v1",
                "Warehouse wind-operations review",
                HazardType.WIND,
                Severity.HIGH,
                "Review loose equipment, dock operations, and continuity measures before the relevant operating window.",
                "A source-backed daily-mean wind finding met the published screening severity and the template context is complete.",
                exposure=("goods_sensitivity",),
                vulnerability=("roof_condition",),
            ),
        ],
    ),
    AssetTemplate(
        id="healthcare_facility",
        display_name="Healthcare facility",
        description="Hospitals, clinics, and care facilities with continuity obligations.",
        required_exposure_fields=[
            _field(
                "care_criticality",
                "Care criticality",
                "Criticality of care supported by this facility.",
                value_type="enum",
                allowed_values=("routine", "urgent", "critical"),
            ),
        ],
        required_vulnerability_fields=[
            _field(
                "cooling_resilience",
                "Cooling resilience",
                "Ability to maintain safe conditions during heat.",
                value_type="enum",
                allowed_values=("limited", "standard", "redundant"),
            ),
            _field(
                "access_resilience",
                "Access resilience",
                "Known resilience of access routes and patient transport.",
                value_type="enum",
                allowed_values=("unknown", "limited", "standard", "redundant"),
            ),
        ],
        supported_hazards=[HazardType.EXTREME_HEAT, HazardType.HEAVY_PRECIPITATION],
        operational_rules=[
            _rule(
                "healthcare-heat-care-v1",
                "Healthcare heat-care continuity review",
                HazardType.EXTREME_HEAT,
                Severity.MODERATE,
                "Review patient heat-safety, cooling, staffing, and continuity coverage before the relevant operating window.",
                "A source-backed heat finding met the published screening severity and the template context is complete.",
                exposure=("care_criticality",),
                vulnerability=("cooling_resilience",),
            ),
            _rule(
                "healthcare-rain-access-v1",
                "Healthcare rainfall-access review",
                HazardType.HEAVY_PRECIPITATION,
                Severity.MODERATE,
                "Review emergency access, patient transport, and weatherproofing before the relevant operating window.",
                "A source-backed precipitation finding met the published screening severity and the template context is complete.",
                exposure=("care_criticality",),
                vulnerability=("access_resilience",),
            ),
        ],
    ),
    AssetTemplate(
        id="industrial_facility",
        display_name="Industrial facility",
        description="Manufacturing, processing, and industrial sites.",
        required_exposure_fields=[
            _field(
                "process_criticality",
                "Process criticality",
                "Criticality of continuous processes at this facility.",
                value_type="enum",
                allowed_values=("low", "medium", "high"),
            ),
        ],
        required_vulnerability_fields=[
            _field(
                "water_dependency",
                "Water dependency",
                "Reliance on reliable water supply for operation.",
                value_type="enum",
                allowed_values=("low", "medium", "high"),
            ),
            _field(
                "wind_operating_plan",
                "Wind operating plan",
                "Whether documented wind operating limits and controls exist.",
                value_type="enum",
                allowed_values=("unknown", "absent", "documented", "tested"),
            ),
        ],
        supported_hazards=[HazardType.WIND, HazardType.DROUGHT, HazardType.EXTREME_HEAT],
        operational_rules=[
            _rule(
                "industrial-wind-operations-v1",
                "Industrial wind-operations review",
                HazardType.WIND,
                Severity.MODERATE,
                "Review outdoor work, loose equipment, and documented wind operating limits before the relevant operating window.",
                "A source-backed daily-mean wind finding met the published screening severity and the template context is complete.",
                exposure=("process_criticality",),
                vulnerability=("wind_operating_plan",),
            ),
            _rule(
                "industrial-drought-water-v1",
                "Industrial water-continuity review",
                HazardType.DROUGHT,
                Severity.MODERATE,
                "Review water supply, storage, and process-continuity measures before the relevant operating window.",
                "A source-backed drought finding met the published screening severity and the template context is complete.",
                exposure=("process_criticality",),
                vulnerability=("water_dependency",),
            ),
        ],
    ),
    AssetTemplate(
        id="solar_site",
        display_name="Solar site",
        description="Utility and commercial solar generation sites.",
        required_exposure_fields=[
            _field(
                "generation_criticality",
                "Generation criticality",
                "Criticality of generation from this site.",
                value_type="enum",
                allowed_values=("low", "medium", "high"),
            ),
        ],
        required_vulnerability_fields=[
            _field(
                "wind_design_review_status",
                "Wind-design review status",
                "Status of the documented wind-design and inspection review.",
                value_type="enum",
                allowed_values=("unknown", "overdue", "current", "verified"),
            ),
            _field(
                "water_cleaning_dependency",
                "Water cleaning dependency",
                "Reliance on water for panel cleaning and operations.",
                value_type="enum",
                allowed_values=("low", "medium", "high"),
            ),
        ],
        supported_hazards=[HazardType.WIND, HazardType.DROUGHT, HazardType.EXTREME_HEAT],
        operational_rules=[
            _rule(
                "solar-wind-inspection-v1",
                "Solar-site wind inspection review",
                HazardType.WIND,
                Severity.MODERATE,
                "Review tracking equipment, loose components, and inspection plans before the relevant operating window.",
                "A source-backed daily-mean wind finding met the published screening severity and the template context is complete.",
                exposure=("generation_criticality",),
                vulnerability=("wind_design_review_status",),
            ),
            _rule(
                "solar-drought-water-v1",
                "Solar-site water-continuity review",
                HazardType.DROUGHT,
                Severity.MODERATE,
                "Review water availability and cleaning-continuity plans before the relevant operating window.",
                "A source-backed drought finding met the published screening severity and the template context is complete.",
                exposure=("generation_criticality",),
                vulnerability=("water_cleaning_dependency",),
            ),
        ],
    ),
)


def list_templates() -> list[AssetTemplate]:
    """Return independent catalog values so callers cannot mutate the module catalog."""

    return [template.model_copy(deep=True) for template in ASSET_TEMPLATES]


def get_template(template_id: str) -> AssetTemplate | None:
    for template in ASSET_TEMPLATES:
        if template.id == template_id:
            return template.model_copy(deep=True)
    return None
