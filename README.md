# AI Jewelry Design Tool (MVP)

- Milestone 1: core engine. Parametric solitaire ring, rules config file, STL and STEP export.
- Milestone 2: validator. Parameter rules (layer 1), mesh checks (layer 2), a plain-language
  report, and the nearest buildable version of a design that breaks a rule.

    python -m pip install -r requirements.txt
    python -m pytest -v

Rule values in `rules/rules.yaml` are placeholders until a jeweler reviews them, and every
report says so. Test names carry the SRS requirement ID they cover.

Quick try:

    from jewelry.params import RingParams
    from jewelry.validate import validate, nearest_buildable
    print(validate(RingParams(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
        band_thickness_mm=0.5, stone_shape="round", stone_size_mm=6.0,
        prong_count=4, prong_diameter_mm=1.0)).to_text())
