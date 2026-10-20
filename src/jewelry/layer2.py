"""Layer 2: checks on the built mesh (FR-04, NFR-04)."""
import numpy as np
import trimesh
from .params import RingParams
from .report import CheckResult, FAIL, PASS, UNVERIFIED, WARN

SAMPLES, SEED, PERCENTILE = 4000, 1, 1
# The STL approximates curves to within 0.01 mm, so a wall built exactly at the minimum
# can measure slightly under it. Allow twice that before warning or failing.
MESH_TOLERANCE_MM = 0.02


def wall_thickness_stats(mesh, n=SAMPLES, seed=SEED):
    """Shoot rays inward from surface samples; the hit distance is the local wall thickness.
    Returns (value near the thinnest 1% of the surface, thinnest single spot), or None."""
    pts, faces = trimesh.sample.sample_surface(mesh, n, seed=seed)
    normals = mesh.face_normals[faces]
    origins = pts - normals * 1e-3
    locs, ray_idx, _ = mesh.ray.intersects_location(origins, -normals, multiple_hits=False)
    if len(ray_idx) == 0:
        return None
    d = np.linalg.norm(locs - origins[ray_idx], axis=1)
    return float(np.percentile(d, PERCENTILE)), float(d.min())


def check_mesh(mesh, cad_volume_mm3: float, p: RingParams, rules: dict) -> list:
    metal = p.metal.replace("_", " ")
    need = rules["metals"][p.metal]["min_wall_mm"]
    tol = rules["tolerances"]["stl_step_volume_pct"]
    out = []

    if not mesh.is_watertight:
        out.append(CheckResult("L2-WATERTIGHT", 2, FAIL,
                   "The 3D model has holes or open edges, so a printer or caster could not turn it into a solid ring."))
        out.append(CheckResult("L2-WALL-THICKNESS", 2, UNVERIFIED,
                   "Wall thickness was not checked because the model has holes."))
        out.append(CheckResult("L2-VOLUME-MATCH", 2, UNVERIFIED,
                   "The weight and file consistency check was skipped because the model has holes."))
        return out
    out.append(CheckResult("L2-WATERTIGHT", 2, PASS, "The 3D model is a closed solid with no holes."))

    stats = wall_thickness_stats(mesh)
    if stats is None:
        out.append(CheckResult("L2-WALL-THICKNESS", 2, UNVERIFIED,
                   "Wall thickness could not be measured for this model."))
    else:
        low, thinnest = stats
        if low < need - MESH_TOLERANCE_MM:
            out.append(CheckResult("L2-WALL-THICKNESS", 2, FAIL,
                       f"Parts of the ring are only about {low:.2f} mm thick, but {metal} needs at least {need:g} mm. Thicken the prongs, the band, or the metal around the stone."))
        elif thinnest < need - MESH_TOLERANCE_MM:
            out.append(CheckResult("L2-WALL-THICKNESS", 2, WARN,
                       f"A few small spots are as thin as {thinnest:.2f} mm, below the {need:g} mm minimum for {metal}. Ask your jeweler to check them."))
        else:
            out.append(CheckResult("L2-WALL-THICKNESS", 2, PASS,
                       f"The thinnest metal is {thinnest:.2f} mm, which meets the {need:g} mm minimum for {metal}."))

    diff = abs(mesh.volume - cad_volume_mm3) / cad_volume_mm3 * 100
    if diff < tol:
        out.append(CheckResult("L2-VOLUME-MATCH", 2, PASS,
                   f"The exported files agree on the ring's volume (difference {diff:.2f}%), so the weight estimate is consistent."))
    else:
        out.append(CheckResult("L2-VOLUME-MATCH", 2, FAIL,
                   f"The exported files disagree on the ring's volume by {diff:.2f}%, which is more than the {tol:g}% allowed. The weight estimate would not be reliable."))
    return out
