"""STL and STEP export (FR-09)."""
from pathlib import Path
import cadquery as cq
import trimesh


def export_files(shape: cq.Workplane, stem) -> trimesh.Trimesh:
    stem = Path(stem)
    cq.exporters.export(shape, str(stem.with_suffix(".step")))
    cq.exporters.export(shape, str(stem.with_suffix(".stl")),
                        tolerance=0.01, angularTolerance=0.1)
    return trimesh.load(str(stem.with_suffix(".stl")), process=True)
