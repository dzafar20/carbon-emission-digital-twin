"""
Carbon Emission Calculator — Scope 1 & Scope 2
Manufacturing / Industrial Company Digital Twin

Variables used (from Data_Variables.xlsx):
  Scope 1 (direct combustion):
    - fuel_consumption_kwh     : Fuel consumed by machines/boilers (kWh)
    - onsite_fuel_boiler_kwh   : Fuel consumed by boilers/generators (kWh)
    - fuel_type                : Type of fuel → selects correct emission factor

  Scope 2 (purchased electricity):
    - electricity_kwh          : Total electricity consumption per line (kWh)
    - compressed_air_kwh       : Compressed air / utilities energy (kWh)
    - hvac_kwh                 : HVAC / heating energy (kWh)
    - electricity_source       : Grid, solar, etc. → selects correct factor

  Supporting variables used for analysis & digital twin accuracy:
    - power_rating_kw          : Machine power rating
    - idle_power_kw            : Machine idle power
    - operating_time_hours     : Hours machines ran
    - idle_time_hours          : Non-productive hours
    - production_output_units  : Units produced (for intensity metrics)
    - machine_utilization_pct  : OEE / utilization
    - line_id, category        : Production line identifier
"""

import pandas as pd
from utils.emission_factors import (
    SCOPE1_FUEL_FACTORS,
    SCOPE2_GRID_FACTORS,
    KG_TO_TONNES,
)


def calculate_scope1(row: pd.Series) -> dict:
    """
    Scope 1 — Direct emissions from fuel combustion.

    Formula:
        E_scope1 = (fuel_consumption_kwh + onsite_fuel_boiler_kwh)
                   × emission_factor(fuel_type)

    Returns dict with intermediate values and final tCO2e.
    """
    fuel_type = str(row.get("fuel_type", "default")).strip().lower()
    ef = SCOPE1_FUEL_FACTORS.get(fuel_type, SCOPE1_FUEL_FACTORS["default"])

    fuel_machine  = float(row.get("fuel_consumption_kwh", 0))
    fuel_boiler   = float(row.get("onsite_fuel_boiler_kwh", 0))
    total_fuel_kwh = fuel_machine + fuel_boiler

    # kg CO2e
    scope1_kg = total_fuel_kwh * ef

    return {
        "fuel_type":              fuel_type,
        "fuel_machine_kwh":       fuel_machine,
        "fuel_boiler_kwh":        fuel_boiler,
        "total_fuel_kwh":         total_fuel_kwh,
        "scope1_emission_factor": ef,
        "scope1_kg_co2e":         round(scope1_kg, 4),
        "scope1_tco2e":           round(scope1_kg * KG_TO_TONNES, 6),
    }


def calculate_scope2(row: pd.Series) -> dict:
    """
    Scope 2 — Indirect emissions from purchased electricity.

    Formula:
        E_scope2 = (electricity_kwh + compressed_air_kwh + hvac_kwh)
                   × emission_factor(electricity_source)

    Returns dict with intermediate values and final tCO2e.
    """
    source = str(row.get("electricity_source", "grid")).strip().lower()
    ef = SCOPE2_GRID_FACTORS.get(source, SCOPE2_GRID_FACTORS["default"])

    elec_kwh  = float(row.get("electricity_kwh", 0))
    air_kwh   = float(row.get("compressed_air_kwh", 0))
    hvac_kwh  = float(row.get("hvac_kwh", 0))
    total_elec_kwh = elec_kwh + air_kwh + hvac_kwh

    # kg CO2e
    scope2_kg = total_elec_kwh * ef

    return {
        "electricity_source":     source,
        "electricity_kwh":        elec_kwh,
        "compressed_air_kwh":     air_kwh,
        "hvac_kwh":               hvac_kwh,
        "total_electricity_kwh":  total_elec_kwh,
        "scope2_emission_factor": ef,
        "scope2_kg_co2e":         round(scope2_kg, 4),
        "scope2_tco2e":           round(scope2_kg * KG_TO_TONNES, 6),
    }


def calculate_energy_profile(row: pd.Series) -> dict:
    """
    Machine energy profile — validates measured consumption against
    rated power × time (useful for digital twin accuracy check).

    Formula:
        Expected energy = (Pi × tc) + (Pu × tidle)
        Where:
            Pi  = power_rating_kw   (active power)
            tc  = operating_time_hours
            Pu  = idle_power_kw
            tidle = idle_time_hours
    """
    pi     = float(row.get("power_rating_kw", 0))
    pu     = float(row.get("idle_power_kw", 0))
    tc     = float(row.get("operating_time_hours", 0))
    tidle  = float(row.get("idle_time_hours", 0))

    expected_kwh  = (pi * tc) + (pu * tidle)
    measured_kwh  = float(row.get("electricity_kwh", 0))
    utilization   = float(row.get("machine_utilization_pct", 0))

    deviation_pct = 0.0
    if expected_kwh > 0:
        deviation_pct = round(((measured_kwh - expected_kwh) / expected_kwh) * 100, 2)

    return {
        "expected_energy_kwh":    round(expected_kwh, 2),
        "measured_energy_kwh":    measured_kwh,
        "energy_deviation_pct":   deviation_pct,
        "machine_utilization_pct": utilization,
    }


def calculate_emission_intensity(total_tco2e: float, production_units: float) -> float:
    """
    Emission intensity = tCO2e per unit produced.
    Useful KPI for normalizing emissions against output.
    """
    if production_units > 0:
        return round(total_tco2e / production_units, 8)
    return 0.0


def process_csv(filepath: str) -> pd.DataFrame:
    """
    Main function: reads the CSV and calculates all emissions per row.

    Returns a DataFrame with original columns + all calculated emission
    columns appended.
    """
    df = pd.read_csv(filepath, parse_dates=["timestamp"])

    results = []
    for _, row in df.iterrows():
        s1 = calculate_scope1(row)
        s2 = calculate_scope2(row)
        ep = calculate_energy_profile(row)

        total_tco2e = s1["scope1_tco2e"] + s2["scope2_tco2e"]
        intensity   = calculate_emission_intensity(
            total_tco2e,
            float(row.get("production_output_units", 0))
        )

        results.append({
            **row.to_dict(),
            **s1,
            **s2,
            **ep,
            "total_tco2e":               round(total_tco2e, 6),
            "emission_intensity_tco2e_per_unit": intensity,
        })

    return pd.DataFrame(results)


def summarize(df: pd.DataFrame) -> dict:
    """
    Aggregate totals and KPIs across the full dataset.
    Returns a dict ready to be pushed into the AAS submodel.
    """
    return {
        # Totals
        "total_scope1_tco2e":           round(df["scope1_tco2e"].sum(), 4),
        "total_scope2_tco2e":           round(df["scope2_tco2e"].sum(), 4),
        "total_combined_tco2e":         round(df["total_tco2e"].sum(), 4),

        # Energy totals
        "total_fuel_kwh":               round(df["total_fuel_kwh"].sum(), 2),
        "total_electricity_kwh":        round(df["total_electricity_kwh"].sum(), 2),

        # Production
        "total_production_units":       int(df["production_output_units"].sum()),

        # KPIs
        "avg_emission_intensity":       round(df["emission_intensity_tco2e_per_unit"].mean(), 8),
        "avg_machine_utilization_pct":  round(df["machine_utilization_pct"].mean(), 2),
        "avg_energy_deviation_pct":     round(df["energy_deviation_pct"].mean(), 2),

        # Per line breakdown
        "by_line": df.groupby("line_id")["total_tco2e"].sum().round(4).to_dict(),

        # Per category breakdown
        "by_category": df.groupby("category")["total_tco2e"].sum().round(4).to_dict(),
    }
