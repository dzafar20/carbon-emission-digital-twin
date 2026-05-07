"""
AAS Builder — Asset Administration Shell for Carbon Emissions Digital Twin
Builds the full AAS structure in JSON (AAS Part 2 / V3 schema)
compatible with BaSyx AAS Server.

Structure:
  AAS: ManufacturingCompany_CarbonTwin
  ├── Submodel: Nameplate          (company identity)
  ├── Submodel: CarbonEmissions    (Scope 1 + 2 totals & KPIs)
  ├── Submodel: EnergyProfile      (electricity, fuel, HVAC breakdown)
  ├── Submodel: ProductionData     (output, utilization, intensity)
  └── Submodel: LineEmissions      (per production line breakdown)
"""

import json
import base64
from datetime import datetime
from typing import Any


# ─────────────────────────────────────────────────────────────
# Helpers — build AAS element primitives
# ─────────────────────────────────────────────────────────────

def _b64(s: str) -> str:
    """Base64-encode an AAS identifier (required by BaSyx REST API)."""
    return base64.urlsafe_b64encode(s.encode()).decode()


def _property(id_short: str, value_type: str, value: Any,
               display_name: str = "", description: str = "", unit: str = "") -> dict:
    """Create an AAS Property element."""
    prop = {
        "modelType": "Property",
        "idShort": id_short,
        "valueType": value_type,
        "value": str(value),
        "category": "VARIABLE",
    }
    if display_name:
        prop["displayName"] = [{"language": "en", "text": display_name}]
    if description:
        prop["description"] = [{"language": "en", "text": description}]
    if unit:
        prop["qualifiers"] = [{"modelType": "Qualifier", "type": "unit", "valueType": "xs:string", "value": unit}]
    return prop


def _collection(id_short: str, elements: list, display_name: str = "") -> dict:
    """Create an AAS SubmodelElementCollection."""
    col = {
        "modelType": "SubmodelElementCollection",
        "idShort": id_short,
        "value": elements,
    }
    if display_name:
        col["displayName"] = [{"language": "en", "text": display_name}]
    return col


def _submodel(submodel_id: str, id_short: str, description: str, elements: list) -> dict:
    """Create a full Submodel object."""
    return {
        "modelType": "Submodel",
        "id": submodel_id,
        "idShort": id_short,
        "description": [{"language": "en", "text": description}],
        "administration": {"version": "1", "revision": "0"},
        "kind": "Instance",
        "submodelElements": elements,
    }


# ─────────────────────────────────────────────────────────────
# Submodel builders
# ─────────────────────────────────────────────────────────────

def build_nameplate_submodel(company_name: str = "Example Manufacturing GmbH",
                              location: str = "Berlin, Germany",
                              sector: str = "Manufacturing / Industrial") -> dict:
    """Nameplate — company identity information."""
    return _submodel(
        submodel_id="urn:company:submodel:nameplate",
        id_short="Nameplate",
        description="Company identification and classification",
        elements=[
            _property("CompanyName",    "xs:string", company_name,
                      "Company Name", "Legal name of the company"),
            _property("Location",       "xs:string", location,
                      "Location", "Primary facility location"),
            _property("Sector",         "xs:string", sector,
                      "Industry Sector", "Industry classification"),
            _property("ReportingYear",  "xs:string", str(datetime.now().year),
                      "Reporting Year", "Year for which emissions are calculated"),
            _property("Standard",       "xs:string", "GHG Protocol Corporate Standard",
                      "Reporting Standard", "Emission accounting standard used"),
            _property("CreatedAt",      "xs:string", datetime.now().isoformat(),
                      "Created At", "Timestamp when this AAS was generated"),
        ]
    )


def build_carbon_emissions_submodel(summary: dict) -> dict:
    """
    CarbonEmissions — Scope 1 & 2 totals, KPIs.
    This is the primary submodel for the digital twin.
    """
    return _submodel(
        submodel_id="urn:company:submodel:carbon-emissions",
        id_short="CarbonEmissions",
        description="Scope 1 and Scope 2 greenhouse gas emissions — GHG Protocol",
        elements=[
            # ── Scope 1 ──────────────────────────────────────
            _collection("Scope1_DirectEmissions", display_name="Scope 1 — Direct Emissions", elements=[
                _property("Scope1_Total_tCO2e",  "xs:float",
                          summary["total_scope1_tco2e"],
                          "Total Scope 1 Emissions",
                          "Direct emissions from fuel combustion in machines, boilers, generators",
                          "tCO2e"),
                _property("Scope1_TotalFuel_kWh", "xs:float",
                          summary["total_fuel_kwh"],
                          "Total Fuel Consumed",
                          "Sum of fuel consumed by all machines and onsite boilers",
                          "kWh"),
                _property("Scope1_EmissionFactor_Source", "xs:string",
                          "GHG Protocol / IPCC AR6",
                          "Emission Factor Source",
                          "Standard used for fuel emission factors"),
            ]),

            # ── Scope 2 ──────────────────────────────────────
            _collection("Scope2_IndirectEmissions", display_name="Scope 2 — Indirect Emissions", elements=[
                _property("Scope2_Total_tCO2e",        "xs:float",
                          summary["total_scope2_tco2e"],
                          "Total Scope 2 Emissions",
                          "Indirect emissions from purchased electricity, compressed air, HVAC",
                          "tCO2e"),
                _property("Scope2_TotalElectricity_kWh", "xs:float",
                          summary["total_electricity_kwh"],
                          "Total Electricity Consumed",
                          "Sum of electricity, compressed air, and HVAC energy",
                          "kWh"),
                _property("Scope2_EmissionFactor_Source", "xs:string",
                          "IEA 2023 Grid Emission Factors",
                          "Emission Factor Source",
                          "Standard used for electricity emission factors"),
            ]),

            # ── Combined Total ────────────────────────────────
            _collection("CombinedEmissions", display_name="Combined Totals", elements=[
                _property("Total_tCO2e",        "xs:float",
                          summary["total_combined_tco2e"],
                          "Total GHG Emissions",
                          "Scope 1 + Scope 2 combined",
                          "tCO2e"),
                _property("EmissionIntensity",  "xs:float",
                          summary["avg_emission_intensity"],
                          "Avg Emission Intensity",
                          "Average tCO2e per unit produced across all lines",
                          "tCO2e/unit"),
            ]),
        ]
    )


def build_energy_submodel(summary: dict) -> dict:
    """EnergyProfile — breakdown of all energy sources."""
    return _submodel(
        submodel_id="urn:company:submodel:energy-profile",
        id_short="EnergyProfile",
        description="Energy consumption breakdown across all sources",
        elements=[
            _property("TotalFuelEnergy_kWh",        "xs:float",
                      summary["total_fuel_kwh"],
                      "Total Fuel Energy",
                      "Total energy from fuel combustion (machines + boilers)",
                      "kWh"),
            _property("TotalElectricityEnergy_kWh", "xs:float",
                      summary["total_electricity_kwh"],
                      "Total Electricity Energy",
                      "Total electricity incl. compressed air and HVAC",
                      "kWh"),
            _property("DataPeriod",                 "xs:string",
                      "5 working days (1 week)",
                      "Data Collection Period",
                      "Time span of the dataset used"),
            _property("EnergyDeviation_Avg_Pct",    "xs:float",
                      summary["avg_energy_deviation_pct"],
                      "Avg Energy Deviation",
                      "Avg % deviation between expected (rated) and measured energy",
                      "%"),
        ]
    )


def build_production_submodel(summary: dict) -> dict:
    """ProductionData — output volumes, utilization, intensity."""
    return _submodel(
        submodel_id="urn:company:submodel:production-data",
        id_short="ProductionData",
        description="Production output, machine utilization and emission intensity",
        elements=[
            _property("TotalProductionUnits",       "xs:int",
                      summary["total_production_units"],
                      "Total Units Produced",
                      "Total production output across all lines and days",
                      "units"),
            _property("AvgMachineUtilization_Pct",  "xs:float",
                      summary["avg_machine_utilization_pct"],
                      "Avg Machine Utilization",
                      "Average OEE / utilization across all machines",
                      "%"),
            _property("AvgEmissionIntensity",       "xs:float",
                      summary["avg_emission_intensity"],
                      "Avg Emission Intensity",
                      "Average tCO2e emitted per unit produced",
                      "tCO2e/unit"),
        ]
    )


def build_line_emissions_submodel(summary: dict) -> dict:
    """LineEmissions — per-line and per-category emission breakdown."""
    elements = []

    # Per production line
    line_elements = []
    for line_id, tco2e in summary["by_line"].items():
        line_elements.append(
            _property(
                id_short=f"Line_{line_id.replace(' ', '_')}_tCO2e",
                value_type="xs:float",
                value=tco2e,
                display_name=f"{line_id} Emissions",
                description=f"Total tCO2e for {line_id}",
                unit="tCO2e"
            )
        )
    elements.append(_collection("ByProductionLine", line_elements, "Emissions by Production Line"))

    # Per category
    cat_elements = []
    for cat, tco2e in summary["by_category"].items():
        cat_elements.append(
            _property(
                id_short=f"Cat_{cat.replace(' ', '_')}_tCO2e",
                value_type="xs:float",
                value=tco2e,
                display_name=f"{cat} Emissions",
                description=f"Total tCO2e for {cat}",
                unit="tCO2e"
            )
        )
    elements.append(_collection("ByCategory", cat_elements, "Emissions by Category"))

    return _submodel(
        submodel_id="urn:company:submodel:line-emissions",
        id_short="LineEmissions",
        description="Emission breakdown by production line and category",
        elements=elements,
    )


# ─────────────────────────────────────────────────────────────
# Main AAS builder
# ─────────────────────────────────────────────────────────────

def build_aas_shell(submodel_ids: list) -> dict:
    """Build the top-level AAS shell referencing all submodels."""
    return {
        "modelType": "AssetAdministrationShell",
        "id": "urn:company:aas:carbon-twin-001",
        "idShort": "ManufacturingCarbonTwin",
        "description": [{"language": "en",
                          "text": "Digital twin for carbon emission tracking — Scope 1 & 2"}],
        "administration": {"version": "1", "revision": "0"},
        "assetInformation": {
            "assetKind": "Instance",
            "globalAssetId": "urn:company:asset:manufacturing-plant-001",
        },
        "submodels": [
            {"type": "ModelReference",
             "keys": [{"type": "Submodel", "value": sm_id}]}
            for sm_id in submodel_ids
        ],
    }


def build_full_aas_environment(summary: dict,
                                company_name: str = "Example Manufacturing GmbH",
                                location: str = "Berlin, Germany") -> dict:
    """
    Build and return the complete AAS Environment dict,
    ready to be serialized to JSON and uploaded to BaSyx.
    """
    nameplate   = build_nameplate_submodel(company_name, location)
    carbon      = build_carbon_emissions_submodel(summary)
    energy      = build_energy_submodel(summary)
    production  = build_production_submodel(summary)
    line_em     = build_line_emissions_submodel(summary)

    submodels = [nameplate, carbon, energy, production, line_em]
    shell     = build_aas_shell([sm["id"] for sm in submodels])

    return {
        "assetAdministrationShells": [shell],
        "submodels": submodels,
        "conceptDescriptions": [],
    }


def save_aas_json(env: dict, filepath: str):
    """Save the AAS environment to a .json file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2, ensure_ascii=False)
    print(f"[AAS] Saved to {filepath}")
