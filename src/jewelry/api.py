"""HTTP API for the front end (SDD: backend API). Run with:
    python -m uvicorn jewelry.api:app --app-dir src --port 8000
"""
import io
import os
import tempfile
import zipfile
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from .design_export import ExportRefused, export_design
from .params import RingParams
from .rules import load_rules
from .service import build_design
from .sizes import inner_diameter_mm, ring_sizes

ORIGINS = os.environ.get("JEWELRY_CORS_ORIGINS",
                         "http://localhost:5173,http://127.0.0.1:5173").split(",")

app = FastAPI(title="AI Jewelry Design Tool API")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/designs/build")
def build(params: RingParams):
    """Build the ring, validate it, and return the preview mesh, report and numbers (FR-11)."""
    return build_design(params)


@app.post("/designs/export")
def export(params: RingParams):
    """STL, STEP and spec sheet as one zip. Refused with the report if any check fails (FR-09, FR-10)."""
    with tempfile.TemporaryDirectory() as d:
        try:
            result = export_design(params, Path(d) / "out")
        except ExportRefused as refused:
            raise HTTPException(status_code=422, detail={
                "message": "Export refused: a check failed.",
                "report": refused.report.to_dict()}) from None
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for path in (result.stl, result.step, result.spec_sheet):
                z.write(path, path.name)
    return Response(buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="ring_design.zip"'})


@app.get("/rules")
def rules():
    """The current design rules, read-only (FR-03)."""
    return load_rules()


@app.get("/sizes")
def sizes(system: str = Query(..., description="mm, us, uk or eu"),
          value: str = Query(..., description="the size, for example 7 or N1/2")):
    """Convert a ring size to every system (FR-07)."""
    try:
        v = value if system.lower() == "uk" else float(value)
        return ring_sizes(inner_diameter_mm(system, v))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
