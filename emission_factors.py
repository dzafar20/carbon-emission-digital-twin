"""
Emission Factors — based on GHG Protocol & IPCC standards
All factors in kg CO2e per kWh (or per unit as noted)

Sources:
  - IPCC AR6 (2021)
  - GHG Protocol Corporate Standard
  - IEA Electricity Emission Factors 2023
"""

# ─────────────────────────────────────────────
# SCOPE 1 — Fuel combustion emission factors
# Unit: kg CO2e per kWh of fuel energy
# ─────────────────────────────────────────────
SCOPE1_FUEL_FACTORS = {
    "natural_gas":  0.2018,   # kg CO2e / kWh  (IPCC)
    "diesel":       0.2667,   # kg CO2e / kWh
    "petrol":       0.2288,   # kg CO2e / kWh
    "lpg":          0.2143,   # kg CO2e / kWh
    "coal":         0.3410,   # kg CO2e / kWh
    "biomass":      0.0390,   # kg CO2e / kWh  (considered low-carbon)
    "default":      0.2500,   # fallback average
}

# ─────────────────────────────────────────────
# SCOPE 2 — Electricity grid emission factors
# Unit: kg CO2e per kWh of electricity consumed
# ─────────────────────────────────────────────
SCOPE2_GRID_FACTORS = {
    "grid":         0.2330,   # kg CO2e / kWh  (European average, IEA 2023)
    "solar":        0.0410,   # kg CO2e / kWh  (lifecycle)
    "wind":         0.0110,   # kg CO2e / kWh  (lifecycle)
    "hydro":        0.0240,   # kg CO2e / kWh  (lifecycle)
    "nuclear":      0.0120,   # kg CO2e / kWh  (lifecycle)
    "mixed":        0.1800,   # kg CO2e / kWh  (mixed renewable + grid)
    "default":      0.2330,
}

# Conversion helpers
KWH_PER_LITER_DIESEL      = 10.0    # 1 liter diesel ≈ 10 kWh
KWH_PER_M3_NATURAL_GAS   = 10.55   # 1 m³ natural gas ≈ 10.55 kWh
KG_TO_TONNES              = 0.001   # kg → metric tonnes CO2e
