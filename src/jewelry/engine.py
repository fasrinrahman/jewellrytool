"""Parametric solitaire ring builder (FR-01). Band axis is Z, the head points +Y."""
import math
import cadquery as cq
from .params import RingParams

PAVILION_RATIO = 0.43      # round stone pavilion depth as a share of diameter (placeholder)
COLLAR_FLOOR_MM = 1.0      # metal left under the stone seat
COLLAR_WALL_MM = 1.0       # metal around the stone at the girdle (must stay above the min wall rule)
HEAD_SINK_MM = 0.5         # head sinks into the band so the parts fuse


def seat_depth_mm(stone_shape: str, stone_size_mm: float) -> float:
    """Seat depth is derived from the stone, never entered by the user."""
    return PAVILION_RATIO * stone_size_mm


def build_ring(p: RingParams) -> cq.Workplane:
    r_in = p.ring_size_mm / 2
    r_out = r_in + p.band_thickness_mm
    band = (cq.Workplane("XY").circle(r_out).circle(r_in)
            .extrude(p.band_width_mm / 2, both=True))

    stone_r = p.stone_size_mm / 2
    pav_h = seat_depth_mm(p.stone_shape, p.stone_size_mm)
    collar_h = pav_h + COLLAR_FLOOR_MM
    head = cq.Workplane("XY").circle(stone_r + COLLAR_WALL_MM).extrude(collar_h)
    seat = cq.Workplane("XY").add(cq.Solid.makeCone(
        0.3, stone_r, pav_h, pnt=cq.Vector(0, 0, collar_h - pav_h)))
    head = head.cut(seat)
    for i in range(p.prong_count):
        a = 2 * math.pi * i / p.prong_count
        x, y = (stone_r + 0.35) * math.cos(a), (stone_r + 0.35) * math.sin(a)
        head = head.union(cq.Workplane("XY").center(x, y)
                          .circle(p.prong_diameter_mm / 2).extrude(collar_h + 0.8))
    head = (head.rotate((0, 0, 0), (1, 0, 0), -90)
            .translate((0, r_out - HEAD_SINK_MM, 0)))
    return band.union(head)
