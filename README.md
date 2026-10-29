# AI Jewelry Design Tool (MVP)

- Milestone 1: core engine. Parametric solitaire ring, rules config file, STL and STEP export.
- Milestone 2: validator. Parameter rules (layer 1), mesh checks (layer 2), a plain-language
  report, and the nearest buildable version of a design that breaks a rule.
- Milestone 3: numbers and spec sheet. Ring size conversion (US, UK, EU, mm), metal weight,
  a cost range with its price source and date, a one-page PDF spec sheet, and an export step
  that refuses any design that fails a check.

- Milestone 4: backend API and live 3D preview (React and three.js) with a true-scale view.

## How validation protects the user

Three layers, so no single mistake can put a bad design in front of a jeweler:

1. **Input limits** (`params.py`): generous hard limits stop absurd or hostile input (infinity, NaN,
   1,000,000,000 mm, a 5,000 character metal name) before it reaches the CAD engine. The API answers
   422 and never echoes the bad value back.
2. **Design rules** (`rules/rules.yaml`, checked by `layer1.py`): every measurement has a minimum
   and a maximum, and the prongs are checked against the stone. A failed rule explains itself and
   offers the nearest buildable value.
3. **Model checks** (`layer2.py`): the built mesh must be a closed solid, one connected piece, thick
   enough everywhere, and consistent between the STL and STEP files.

The engine also verifies its own result and retries if the CAD kernel fails to fuse the parts.
All limits in `rules.yaml` are placeholders until a jeweler reviews them.

## Run the tests

    python -m pip install -r requirements.txt
    python -m pytest -v
    cd frontend && npm install && npm test

## Run the app (two terminals)

    # terminal 1: backend API on http://localhost:8000
    python -m uvicorn jewelry.api:app --app-dir src --port 8000

    # terminal 2: front end on http://localhost:5173
    cd frontend && npm install && npm run dev

The front end talks to the API at `http://localhost:8000`. To use another address, set
`VITE_API_URL` before starting the front end. The API allows the front end's origin through
CORS; set `JEWELRY_CORS_ORIGINS` (comma separated) to allow others.

True-scale view: choose Life size, hold a bank card against the screen, and drag the slider
until the outline matches it. The ring is then drawn at its real size and the setting is saved.

Rule values in `rules/rules.yaml` and prices in `rules/prices.yaml` are placeholders until a
jeweler reviews the rules and a real price source is chosen. Every report and spec sheet says so.
Test names carry the SRS requirement ID they cover.

Quick try:

    from jewelry.params import RingParams
    from jewelry.design_export import export_design
    from jewelry.sizes import convert

    print(convert("us", 7, "uk"))     # N1/2 (UK is approximate; mm is exact)
    result = export_design(RingParams(metal="silver_925", ring_size_mm=17.3, band_width_mm=3.0,
        band_thickness_mm=1.8, stone_shape="round", stone_size_mm=6.0,
        prong_count=4, prong_diameter_mm=1.0), "out")
    print(result.numbers.weight_g, result.numbers.cost_text())   # files are in the out folder
