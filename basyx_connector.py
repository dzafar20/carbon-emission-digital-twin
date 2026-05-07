"""
BaSyx Connector — pushes the AAS & submodels to a running BaSyx server
via its REST API (AAS Part 2 HTTP/REST API, V3).

Prerequisites:
    Docker must be running with BaSyx:
    ─────────────────────────────────────────────────────────────────
    docker run -p 8081:8081 -p 8082:8082 -p 3000:3000 \
        eclipsebasyx/aas-environment:latest
    ─────────────────────────────────────────────────────────────────

    Then open http://localhost:3000 to browse the AAS Web UI.

Usage:
    from aas.basyx_connector import BaSyxConnector
    conn = BaSyxConnector()
    conn.push_environment(aas_env_dict)
"""

import json
import base64
import requests
from typing import Optional


class BaSyxConnector:
    """
    Handles all communication with the BaSyx AAS Environment server.
    """

    def __init__(self, base_url: str = "http://localhost:8081"):
        """
        Args:
            base_url: URL where the BaSyx AAS Environment server is running.
                      Default is localhost:8081.
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}

    # ─────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────

    def _b64(self, id_str: str) -> str:
        """Base64-encode an AAS/Submodel ID for use in REST URLs."""
        return base64.urlsafe_b64encode(id_str.encode()).decode().rstrip("=")

    def _post(self, endpoint: str, payload: dict) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        resp = requests.post(url, headers=self.headers, json=payload, timeout=10)
        return resp

    def _put(self, endpoint: str, payload: dict) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        resp = requests.put(url, headers=self.headers, json=payload, timeout=10)
        return resp

    def _delete(self, endpoint: str) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        return requests.delete(url, headers=self.headers, timeout=10)

    def _get(self, endpoint: str) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        return requests.get(url, headers=self.headers, timeout=10)

    # ─────────────────────────────────────────────────────────
    # Connectivity check
    # ─────────────────────────────────────────────────────────

    def check_connection(self) -> bool:
        """Returns True if the BaSyx server is reachable."""
        try:
            resp = self._get("/shells")
            if resp.status_code in (200, 404):
                print(f"[BaSyx] ✓ Connected to {self.base_url}")
                return True
        except requests.exceptions.ConnectionError:
            pass
        print(f"[BaSyx] ✗ Cannot reach {self.base_url}")
        print("[BaSyx]   Make sure Docker is running:")
        print("[BaSyx]   docker run -p 8081:8081 -p 3000:3000 eclipsebasyx/aas-environment:latest")
        return False

    # ─────────────────────────────────────────────────────────
    # Submodel operations
    # ─────────────────────────────────────────────────────────

    def upload_submodel(self, submodel: dict) -> bool:
        """
        Upload a single submodel. If it already exists (409), update it.
        Returns True on success.
        """
        sm_id = submodel["id"]
        resp = self._post("/submodels", submodel)

        if resp.status_code == 201:
            print(f"[BaSyx] ✓ Submodel created: {sm_id}")
            return True
        elif resp.status_code == 409:
            # Already exists — update instead
            encoded_id = self._b64(sm_id)
            resp2 = self._put(f"/submodels/{encoded_id}", submodel)
            if resp2.status_code in (200, 204):
                print(f"[BaSyx] ↻ Submodel updated: {sm_id}")
                return True
            else:
                print(f"[BaSyx] ✗ Update failed for {sm_id}: {resp2.status_code} — {resp2.text[:200]}")
                return False
        else:
            print(f"[BaSyx] ✗ Upload failed for {sm_id}: {resp.status_code} — {resp.text[:200]}")
            return False

    def update_submodel_property(self, submodel_id: str,
                                  id_short_path: str, new_value) -> bool:
        """
        Update a single property value inside a submodel.
        Useful for live updates after recalculating emissions.

        Args:
            submodel_id:    The submodel's full URI (e.g. "urn:company:submodel:carbon-emissions")
            id_short_path:  Dot-separated path to the property
                            (e.g. "Scope1_DirectEmissions.Scope1_Total_tCO2e")
            new_value:      New value (will be cast to string for AAS)
        """
        encoded_id = self._b64(submodel_id)
        # BaSyx uses dot-separated path with each segment base64-encoded
        path_parts = id_short_path.split(".")
        path_encoded = ".".join(self._b64(p) for p in path_parts)

        endpoint = f"/submodels/{encoded_id}/submodel-elements/{path_encoded}/$value"
        resp = self._put(endpoint, str(new_value))

        if resp.status_code in (200, 204):
            print(f"[BaSyx] ✓ Updated {id_short_path} = {new_value}")
            return True
        else:
            print(f"[BaSyx] ✗ Update failed: {resp.status_code} — {resp.text[:200]}")
            return False

    # ─────────────────────────────────────────────────────────
    # Shell operations
    # ─────────────────────────────────────────────────────────

    def upload_shell(self, shell: dict) -> bool:
        """Upload the AAS shell. Updates if it already exists."""
        shell_id = shell["id"]
        resp = self._post("/shells", shell)

        if resp.status_code == 201:
            print(f"[BaSyx] ✓ AAS Shell created: {shell_id}")
            return True
        elif resp.status_code == 409:
            encoded_id = self._b64(shell_id)
            resp2 = self._put(f"/shells/{encoded_id}", shell)
            if resp2.status_code in (200, 204):
                print(f"[BaSyx] ↻ AAS Shell updated: {shell_id}")
                return True
        print(f"[BaSyx] ✗ Shell upload failed: {resp.status_code} — {resp.text[:200]}")
        return False

    # ─────────────────────────────────────────────────────────
    # Full environment push
    # ─────────────────────────────────────────────────────────

    def push_environment(self, aas_env: dict) -> bool:
        """
        Push the complete AAS environment (shell + all submodels) to BaSyx.

        Args:
            aas_env: Dict returned by build_aas.build_full_aas_environment()

        Returns:
            True if everything uploaded successfully.
        """
        print("\n[BaSyx] Pushing AAS environment to server...")

        # 1. Upload submodels first (shell references them)
        all_ok = True
        for sm in aas_env.get("submodels", []):
            ok = self.upload_submodel(sm)
            all_ok = all_ok and ok

        # 2. Upload the shell
        for shell in aas_env.get("assetAdministrationShells", []):
            ok = self.upload_shell(shell)
            all_ok = all_ok and ok

        if all_ok:
            print("\n[BaSyx] ✓ All done! Open http://localhost:3000 to browse your AAS.")
        else:
            print("\n[BaSyx] ⚠ Some uploads failed. Check the messages above.")

        return all_ok

    # ─────────────────────────────────────────────────────────
    # Convenience: read back a submodel from the server
    # ─────────────────────────────────────────────────────────

    def get_submodel(self, submodel_id: str) -> Optional[dict]:
        """Fetch a submodel from the server by ID."""
        encoded_id = self._b64(submodel_id)
        resp = self._get(f"/submodels/{encoded_id}")
        if resp.status_code == 200:
            return resp.json()
        print(f"[BaSyx] ✗ Could not fetch {submodel_id}: {resp.status_code}")
        return None

    def list_shells(self) -> list:
        """Return list of all AAS shells on the server."""
        resp = self._get("/shells")
        if resp.status_code == 200:
            return resp.json().get("result", [])
        return []
