"""API tests. Names carry the SRS requirement ID they cover (NFR-07)."""
import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from jewelry.api import app

client = TestClient(app)
GOOD = dict(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
            band_thickness_mm=1.8, stone_shape="round", stone_size_mm=6.0,
            prong_count=4, prong_diameter_mm=1.0)


@pytest.fixture(scope="module")
def good_build():
    r = client.post("/designs/build", json=GOOD)
    assert r.status_code == 200
    return r.json()


# ---------- FR-11: preview mesh from the build call ----------

def test_fr11_build_returns_a_valid_triangle_mesh(good_build):
    mesh = good_build["mesh"]
    n_vertices = len(mesh["vertices"]) // 3
    assert n_vertices > 100 and len(mesh["vertices"]) % 3 == 0
    assert len(mesh["indices"]) % 3 == 0 and len(mesh["indices"]) > 0
    assert min(mesh["indices"]) >= 0 and max(mesh["indices"]) < n_vertices


def test_fr11_mesh_is_in_millimetres_so_the_preview_can_be_true_scale(good_build):
    lo, hi = good_build["bbox_mm"]["min"], good_build["bbox_mm"]["max"]
    outer_diameter = GOOD["ring_size_mm"] + 2 * GOOD["band_thickness_mm"]
    assert hi[0] - lo[0] == pytest.approx(outer_diameter, abs=0.05)   # across the band
    assert hi[2] - lo[2] >= GOOD["band_width_mm"]                      # along the ring axis


def test_fr11_preview_triangles_face_outward_and_form_a_closed_solid(good_build):
    """Inward-facing triangles would make the ring render inside-out in the browser."""
    import numpy as np
    import trimesh
    from jewelry.engine import build_ring
    from jewelry.params import RingParams
    v = np.array(good_build["mesh"]["vertices"]).reshape(-1, 3)
    f = np.array(good_build["mesh"]["indices"]).reshape(-1, 3)
    signed = np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6
    cad = build_ring(RingParams(**GOOD)).val().Volume()
    assert signed > 0 and signed == pytest.approx(cad, rel=0.01)
    merged = trimesh.Trimesh(v, f, process=True)
    assert merged.is_watertight and merged.is_winding_consistent


def test_fr11_the_head_points_up_the_y_axis_for_the_life_size_view(good_build):
    lo, hi = good_build["bbox_mm"]["min"], good_build["bbox_mm"]["max"]
    assert hi[1] > abs(lo[1])   # the stone head sticks out above the band, on +Y


def test_fr11_the_report_and_the_mesh_come_from_the_same_call(good_build):
    assert good_build["exportable"] is True
    assert good_build["mesh"] is not None
    assert any(r["check_id"] == "L2-WALL-THICKNESS" and r["status"] == "pass"
               for r in good_build["report"])


def test_fr08_build_returns_weight_and_cost_with_price_source(good_build):
    n = good_build["numbers"]
    assert n["weight_g"] > 0 and n["cost_low"] < n["cost_high"]
    assert n["price_source"] and n["price_as_of"] and n["prices_verified"] is False


def test_fr07_build_returns_ring_sizes_in_every_system(good_build):
    assert good_build["sizes"]["us"] == 7 and good_build["sizes"]["eu"] == 54


# ---------- FR-04 to FR-06: bad designs ----------

def test_fr06_a_bad_design_returns_no_mesh_and_a_buildable_suggestion():
    r = client.post("/designs/build", json={**GOOD, "prong_diameter_mm": 0.4}).json()
    assert r["exportable"] is False and r["mesh"] is None
    assert r["suggestion"]["changes"][0]["field"] == "prong_diameter_mm"
    fixed = client.post("/designs/build", json=r["suggestion"]["params"]).json()
    assert fixed["exportable"] is True and fixed["mesh"] is not None


def test_fr05_every_non_passing_result_has_a_plain_message():
    r = client.post("/designs/build", json={**GOOD, "band_thickness_mm": 0.5}).json()
    problems = [x for x in r["report"] if x["status"] == "fail"]
    assert problems and all(len(x["message"]) > 20 and "_mm" not in x["message"] for x in problems)


def test_fr12_invalid_input_is_rejected_with_422():
    assert client.post("/designs/build", json={**GOOD, "prong_count": "many"}).status_code == 422
    assert client.post("/designs/build", json={**GOOD, "engraving": "x"}).status_code == 422
    assert client.post("/designs/build", json={}).status_code == 422


# ---------- FR-09, FR-10, NFR-01: export ----------

def test_fr09_export_returns_a_zip_with_stl_step_and_spec_sheet():
    r = client.post("/designs/export", json=GOOD)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert sorted(names) == ["ring.step", "ring.stl", "ring_spec.pdf"]


def test_nfr01_export_of_a_failed_design_is_refused_with_the_report():
    r = client.post("/designs/export", json={**GOOD, "prong_diameter_mm": 0.4})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["report"]["exportable"] is False
    assert any(x["status"] == "fail" for x in detail["report"]["results"])


# ---------- FR-03, FR-07: rules and sizes ----------

def test_fr03_rules_endpoint_returns_the_config():
    r = client.get("/rules").json()
    assert "silver_925" in r["metals"] and "round" in r["stone_shapes"]
    assert r["verified_by_jeweler"] is False


def test_fr07_sizes_endpoint_converts_between_systems():
    assert client.get("/sizes", params={"system": "us", "value": "7"}).json()["uk"] == "N\u00bd"
    assert client.get("/sizes", params={"system": "uk", "value": "N\u00bd"}).json()["us"] == 7
    assert client.get("/sizes", params={"system": "eu", "value": "54"}).json()["mm"] == pytest.approx(17.19, abs=0.01)


@pytest.mark.parametrize("params", [{"system": "us", "value": "40"}, {"system": "jp", "value": "5"},
                                    {"system": "uk", "value": "7"}])
def test_fr07_bad_sizes_return_422_with_a_message(params):
    r = client.get("/sizes", params=params)
    assert r.status_code == 422 and len(r.json()["detail"]) > 10


def test_fr07_non_numeric_size_returns_422():
    assert client.get("/sizes", params={"system": "us", "value": "abc"}).status_code == 422


# ---------- Plumbing ----------

def test_the_front_end_origin_is_allowed_by_cors():
    r = client.options("/designs/build", headers={"Origin": "http://localhost:5173",
                                                   "Access-Control-Request-Method": "POST"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_health_endpoint():
    assert client.get("/health").json() == {"status": "ok"}
