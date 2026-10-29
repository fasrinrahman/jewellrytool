"""Parametric solitaire ring builder (FR-01). Band axis is Z, the head points +Y."""
import math
import cadquery as cq
from .params import RingParams

PAVILION_RATIO = 0.43      # round stone pavilion depth as a share of diameter (placeholder)
COLLAR_FLOOR_MM = 1.0      # metal left under the stone seat
COLLAR_WALL_MM = 1.0       # metal around the stone at the girdle (must stay above the min wall rule)
HEAD_SINK_MM = 0.5         # head sinks into the band so the parts fuse
# The CAD kernel can fail to fuse parts at rare coincidences (found by scanning: stone 4.5 mm with
# prongs of 1.18 to 1.23 mm split into two pieces). A slightly different overlap avoids the clash.
HEAD_SINK_RETRIES_MM = (0.5, 0.55, 0.45, 0.6, 0.4)
PRONG_GRIP_MM = 0.15       # each prong reaches this far over the stone's edge to hold it


def seat_depth_mm(stone_shape: str, stone_size_mm: float) -> float:
    """Seat depth is derived from the stone, never entered by the user."""
    return PAVILION_RATIO * stone_size_mm


class RingBuildError(Exception):
    """The parts of the ring could not be fused into one valid solid."""


def build_ring(p: RingParams) -> cq.Workplane:
    """Build the ring and verify it is one valid solid, retrying with a slightly different overlap."""
    for sink in HEAD_SINK_RETRIES_MM:
        shape = _assemble(p, sink)
        if len(shape.solids().vals()) == 1 and shape.val().isValid():
            return shape
    raise RingBuildError("The parts of the ring did not fuse into one solid.")


def _assemble(p: RingParams, head_sink_mm: float) -> cq.Workplane:
    r_in = p.ring_size_mm / 2
    r_out = r_in + p.band_thickness_mm
    band = (cq.Workplane("XY").circle(r_out).circle(r_in)
            .extrude(p.band_width_mm / 2, both=True))

    stone_r = p.stone_size_mm / 2
    pav_h = seat_depth_mm(p.stone_shape, p.stone_size_mm)
    collar_h = pav_h + COLLAR_FLOOR_MM
    prong_r = p.prong_diameter_mm / 2
    # A prong's outer edge is 2 * prong_r - PRONG_GRIP from the stone, so the collar wall is at least
    # that wide. The prong then always sits PRONG_GRIP inside the collar edge and is never exactly
    # tangent to it (a tangent cylinder leaves a sliver the exported mesh cannot close).
    collar_wall = max(COLLAR_WALL_MM, 2 * prong_r)
    head = cq.Workplane("XY").circle(stone_r + collar_wall).extrude(collar_h)
    seat = cq.Workplane("XY").add(cq.Solid.makeCone(
        0.3, stone_r, pav_h, pnt=cq.Vector(0, 0, collar_h - pav_h)))
    head = head.cut(seat)
    for i in range(p.prong_count):
        a = 2 * math.pi * i / p.prong_count
        centre = stone_r + prong_r - PRONG_GRIP_MM
        x, y = centre * math.cos(a), centre * math.sin(a)
        head = head.union(cq.Workplane("XY").center(x, y).circle(prong_r).extrude(collar_h + 0.8))
    head = (head.rotate((0, 0, 0), (1, 0, 0), -90)
            .translate((0, r_out - head_sink_mm, 0)))
    return band.union(head)
