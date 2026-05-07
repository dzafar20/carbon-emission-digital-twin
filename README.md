# Carbon Emission Digital Twin — AAS with BaSyx

A complete Python project that:
1. Calculates **Scope 1 & Scope 2** carbon emissions from production line data
2. Builds a **digital twin** using the Asset Administration Shell (AAS) standard
3. Pushes the AAS to a **BaSyx server** accessible via a web UI

---

## Project Structure

```
carbon_twin/
├── main.py                     ← Run this to execute everything
├── data/
│   └── sample_data.csv         ← Replace with your real CSV
├── calculator/
│   └── emissions.py            ← Scope 1 & 2 formulas
├── utils/
│   └── emission_factors.py     ← GHG Protocol emission factors
├── aas/
│   ├── build_aas.py            ← Builds the AAS structure (JSON)
│   └── basyx_connector.py      ← Pushes AAS to BaSyx via REST API
└── output/                     ← Generated automatically
    ├── emission_results.csv    ← Detailed per-row emission results
    └── carbon_twin_aas.json    ← AAS in JSON format (V3 standard)
```

---

## Setup

### 1. Install Python dependencies
```bash
pip install pandas openpyxl requests basyx-python-sdk
```

### 2. Start BaSyx with Docker
```bash
docker run -p 8081:8081 -p 8082:8082 -p 3000:3000 \
    eclipsebasyx/aas-environment:latest
```

Open **http://localhost:3000** to see the BaSyx Web UI.

---

## Running the Project

### With sample data (offline — no BaSyx needed):
```bash
python main.py --no-push
```

### With sample data + push to BaSyx:
```bash
python main.py
```

### With your own CSV file:
```bash
python main.py --csv path/to/your_data.csv
```

---

## CSV File Format

Your CSV must contain these columns:

| Column | Unit | Description |
|--------|------|-------------|
| `timestamp` | datetime | Measurement timestamp |
| `line_id` | text | Production line name (e.g. Line1) |
| `category` | text | Category/product group |
| `power_rating_kw` | kW | Machine rated power (Pi) |
| `idle_power_kw` | kW | Machine idle power (Pu) |
| `operating_time_hours` | h/day | Active operating hours (tc) |
| `idle_time_hours` | h/day | Idle/non-production hours (tidle) |
| `electricity_kwh` | kWh | Total electricity consumption |
| `fuel_consumption_kwh` | kWh | Fuel used by machines |
| `fuel_type` | text | `natural_gas`, `diesel`, `lpg`, `coal` |
| `compressed_air_kwh` | kWh | Compressed air & utilities energy |
| `hvac_kwh` | kWh | HVAC / heating energy |
| `production_output_units` | units | Units produced |
| `machine_utilization_pct` | % | OEE / utilization |
| `electricity_source` | text | `grid`, `solar`, `wind`, `mixed` |
| `onsite_fuel_boiler_kwh` | kWh | Fuel used by boilers/generators |
| `water_usage_m3` | m³ | Water usage (for future Scope 3) |
| `dedicated_resources` | count | Headcount per step |
| `packaging_type` | text | `cardboard`, `plastic`, `mixed` |

---

## Emission Formulas

### Scope 1 (Direct — fuel combustion)
```
E_scope1 = (fuel_consumption_kwh + onsite_fuel_boiler_kwh) × EF_fuel
```

| Fuel | Emission Factor |
|------|----------------|
| Natural gas | 0.2018 kg CO2e/kWh |
| Diesel | 0.2667 kg CO2e/kWh |
| LPG | 0.2143 kg CO2e/kWh |
| Coal | 0.3410 kg CO2e/kWh |

*Source: IPCC AR6 / GHG Protocol*

### Scope 2 (Indirect — purchased electricity)
```
E_scope2 = (electricity_kwh + compressed_air_kwh + hvac_kwh) × EF_grid
```

| Source | Emission Factor |
|--------|----------------|
| Grid (EU avg) | 0.2330 kg CO2e/kWh |
| Solar | 0.0410 kg CO2e/kWh |
| Wind | 0.0110 kg CO2e/kWh |
| Mixed | 0.1800 kg CO2e/kWh |

*Source: IEA 2023 Electricity Emission Factors*

### Machine Energy Profile (Digital Twin Validation)
```
Expected_kWh = (Pi × tc) + (Pu × tidle)
Deviation_% = (Measured - Expected) / Expected × 100
```

---

## AAS Structure (Digital Twin)

The AAS built by this project contains 5 submodels:

```
ManufacturingCarbonTwin (AAS Shell)
├── Nameplate              — company name, location, reporting standard
├── CarbonEmissions        — Scope 1 total, Scope 2 total, combined, intensity
├── EnergyProfile          — fuel kWh, electricity kWh, data period
├── ProductionData         — units produced, utilization %, intensity
└── LineEmissions          — breakdown by line and by category
```

---

## Uploading AAS Manually to BaSyx

If BaSyx is running but the automatic push failed, you can upload the
JSON manually through the BaSyx Web UI:

1. Open **http://localhost:3000**
2. Click **"Import AAS"** or **"Upload"**
3. Select `output/carbon_twin_aas.json`
4. Your digital twin appears in the shell list

---

## Replacing Sample Data with Your Real Data

1. Export your production data to CSV following the column format above
2. Run: `python main.py --csv your_file.csv`
3. The calculator will compute emissions and rebuild the AAS automatically

For multiple files (one per line as specified in your footnotes):
```python
# In main.py, replace the single process_csv call with:
import pandas as pd
from calculator.emissions import process_csv, summarize

dfs = []
for filepath in ["data/cat1_line1.csv", "data/cat1_line2.csv", ...]:
    dfs.append(process_csv(filepath))
df = pd.concat(dfs, ignore_index=True)
summary = summarize(df)
```
