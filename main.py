"""
main.py — Carbon Emission Digital Twin
=======================================
Full pipeline:
  1. Read production data from CSV
  2. Calculate Scope 1 & Scope 2 emissions
  3. Build the AAS (Asset Administration Shell)
  4. Save AAS to JSON (always)
  5. Push to BaSyx server (if running)

Usage:
    python main.py                        # uses default sample data
    python main.py --csv path/to/data.csv # use your own file
    python main.py --no-push              # skip BaSyx upload (offline mode)
"""

import os
import sys
import json
import argparse

# ── Make sure imports work from project root ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calculator.emissions import process_csv, summarize
from aas.build_aas import build_full_aas_environment, save_aas_json
from aas.basyx_connector import BaSyxConnector


# ─────────────────────────────────────────────
# Configuration — edit these for your setup
# ─────────────────────────────────────────────
COMPANY_NAME   = "Example Manufacturing GmbH"
LOCATION       = "Berlin, Germany"
BASYX_URL      = "http://localhost:8081"
DEFAULT_CSV    = os.path.join(os.path.dirname(__file__), "data", "sample_data.csv")
OUTPUT_DIR     = os.path.join(os.path.dirname(__file__), "output")


def print_section(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


def run(csv_path: str, push_to_basyx: bool = True):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── Step 1: Calculate emissions ───────────────────────────
    print_section("STEP 1 — Reading data & calculating emissions")
    print(f"[Calc] Reading: {csv_path}")

    df = process_csv(csv_path)
    summary = summarize(df)

    print(f"[Calc] Rows processed         : {len(df)}")
    print(f"[Calc] Total Scope 1 (tCO2e)  : {summary['total_scope1_tco2e']}")
    print(f"[Calc] Total Scope 2 (tCO2e)  : {summary['total_scope2_tco2e']}")
    print(f"[Calc] Total Combined (tCO2e) : {summary['total_combined_tco2e']}")
    print(f"[Calc] Total production units : {summary['total_production_units']}")
    print(f"[Calc] Avg emission intensity : {summary['avg_emission_intensity']} tCO2e/unit")
    print(f"[Calc] By line  : {summary['by_line']}")
    print(f"[Calc] By category : {summary['by_category']}")

    # Save detailed results to CSV
    results_path = os.path.join(OUTPUT_DIR, "emission_results.csv")
    df.to_csv(results_path, index=False)
    print(f"[Calc] Detailed results saved : {results_path}")

    # ── Step 2: Build AAS ─────────────────────────────────────
    print_section("STEP 2 — Building Asset Administration Shell")

    aas_env = build_full_aas_environment(
        summary=summary,
        company_name=COMPANY_NAME,
        location=LOCATION,
    )

    n_shells   = len(aas_env["assetAdministrationShells"])
    n_submodels = len(aas_env["submodels"])
    print(f"[AAS]  Shells built     : {n_shells}")
    print(f"[AAS]  Submodels built  : {n_submodels}")
    for sm in aas_env["submodels"]:
        n_elements = len(sm["submodelElements"])
        print(f"[AAS]    └─ {sm['idShort']:<30} ({n_elements} elements)")

    # ── Step 3: Save AAS to JSON ──────────────────────────────
    print_section("STEP 3 — Saving AAS to JSON")
    aas_json_path = os.path.join(OUTPUT_DIR, "carbon_twin_aas.json")
    save_aas_json(aas_env, aas_json_path)

    # ── Step 4: Push to BaSyx ─────────────────────────────────
    if push_to_basyx:
        print_section("STEP 4 — Pushing to BaSyx server")
        connector = BaSyxConnector(base_url=BASYX_URL)

        if connector.check_connection():
            connector.push_environment(aas_env)
        else:
            print("[BaSyx] Skipping upload — server not reachable.")
            print("[BaSyx] The AAS JSON has been saved and can be")
            print("[BaSyx] uploaded manually via the BaSyx Web UI.")
    else:
        print_section("STEP 4 — BaSyx push skipped (--no-push flag)")

    # ── Summary ───────────────────────────────────────────────
    print_section("DONE")
    print(f"  Emission results CSV : {results_path}")
    print(f"  AAS JSON file        : {aas_json_path}")
    print(f"  BaSyx Web UI         : http://localhost:3000")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carbon Emission Digital Twin — AAS Builder")
    parser.add_argument("--csv",      default=DEFAULT_CSV, help="Path to input CSV file")
    parser.add_argument("--no-push",  action="store_true",  help="Skip BaSyx upload")
    args = parser.parse_args()

    run(csv_path=args.csv, push_to_basyx=not args.no_push)
