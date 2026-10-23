import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, buildDesign, exportDesign, fetchRules, fetchSizes } from "./api";
import { CalibrationCard } from "./components/CalibrationCard";
import { NumbersPanel } from "./components/NumbersPanel";
import { ParamForm } from "./components/ParamForm";
import { ReportPanel } from "./components/ReportPanel";
import { RingPreview, type ViewMode } from "./components/RingPreview";
import { ScaleBar } from "./components/ScaleBar";
import { saveBlob } from "./download";
import { useDebouncedValue } from "./hooks";
import { makeLatestGuard } from "./latest";
import { DEFAULT_FORM, DEFAULT_SIZE_INPUT } from "./params";
import { loadPxPerMm, savePxPerMm } from "./trueScale";
import type { BuildResponse, FormParams, MeshData, RingParams, Rules, SizeInput } from "./types";

const message = (e: unknown): string => (e instanceof Error ? e.message : "Something went wrong.");

export default function App({ debounceMs = 350 }: { debounceMs?: number }) {
  const [rules, setRules] = useState<Rules | null>(null);
  const [form, setForm] = useState<FormParams>(DEFAULT_FORM);
  const [sizeInput, setSizeInput] = useState<SizeInput>(DEFAULT_SIZE_INPUT);
  const [ringMm, setRingMm] = useState<number | null>(null);
  const [sizeError, setSizeError] = useState<string | null>(null);
  const [build, setBuild] = useState<BuildResponse | null>(null);
  const [lastMesh, setLastMesh] = useState<MeshData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("inspect");
  const [pxPerMm, setPxPerMm] = useState(() => loadPxPerMm(window.localStorage));

  const sizeGuard = useRef(makeLatestGuard()).current;
  const buildGuard = useRef(makeLatestGuard()).current;

  useEffect(() => {
    fetchRules().then(setRules).catch((e) => setError(message(e)));
  }, []);

  // Ring size is converted by the server, so there is one source of truth for the maths.
  const debouncedSize = useDebouncedValue(sizeInput, debounceMs);
  useEffect(() => {
    const token = sizeGuard.next();
    fetchSizes(debouncedSize.system, debouncedSize.value)
      .then((s) => {
        if (!sizeGuard.isLatest(token)) return;
        setRingMm(s.mm);
        setSizeError(null);
      })
      .catch((e) => sizeGuard.isLatest(token) && setSizeError(message(e)));
  }, [debouncedSize, sizeGuard]);

  const params: RingParams | null = useMemo(
    () => (ringMm === null ? null : { ...form, ring_size_mm: ringMm }),
    [form, ringMm],
  );
  const debouncedParams = useDebouncedValue(params, debounceMs);

  useEffect(() => {
    if (!debouncedParams) return;
    const token = buildGuard.next();
    setBusy(true);
    buildDesign(debouncedParams)
      .then((r) => {
        if (!buildGuard.isLatest(token)) return;
        setBuild(r);
        if (r.mesh) setLastMesh(r.mesh);
        setError(null);
      })
      .catch((e) => buildGuard.isLatest(token) && setError(message(e)))
      .finally(() => buildGuard.isLatest(token) && setBusy(false));
  }, [debouncedParams, buildGuard]);

  const stale = build !== null && build.mesh === null;
  const mesh = build?.mesh ?? lastMesh;

  const applySuggestion = () => {
    if (!build?.suggestion) return;
    const { ring_size_mm: _ignored, ...rest } = build.suggestion.params;
    setForm((f) => ({ ...f, ...rest }));
  };

  const doExport = async () => {
    if (!params) return;
    setExportMsg(null);
    try {
      saveBlob(await exportDesign(params), "ring_design.zip");
      setExportMsg("Downloaded ring_design.zip (STL, STEP and spec sheet).");
    } catch (e) {
      setExportMsg(e instanceof ApiError ? e.message : message(e));
    }
  };

  const changePxPerMm = (v: number) => {
    setPxPerMm(v);
    savePxPerMm(window.localStorage, v);
  };

  return (
    <div className="app">
      <header>
        <h1>AI Jewelry Design Tool</h1>
        <p className="muted">Preview, check, and export a ring design.</p>
      </header>

      {rules && !rules.verified_by_jeweler && (
        <div className="banner" role="note">
          The design rules and prices are placeholders and have not been reviewed by a jeweler.
        </div>
      )}
      {error && (
        <div className="banner error" role="alert">
          {error}
        </div>
      )}

      <main className="layout">
        <section className="panel">
          <ParamForm
            rules={rules}
            form={form}
            onChange={(patch) => setForm((f) => ({ ...f, ...patch }))}
            sizeInput={sizeInput}
            onSizeChange={setSizeInput}
            sizeError={sizeError}
            sizes={build?.sizes ?? null}
          />
        </section>

        <section className="panel stage">
          <div className="toolbar">
            <div role="group" aria-label="View">
              <button type="button" aria-pressed={view === "inspect"} onClick={() => setView("inspect")}>
                Inspect
              </button>
              <button type="button" aria-pressed={view === "life-size"} onClick={() => setView("life-size")}>
                Life size
              </button>
            </div>
            <span className="muted" role="status">{busy ? "Updating..." : ""}</span>
          </div>
          <div className="canvas-wrap">
            <RingPreview mesh={mesh} metal={form.metal} mode={view} pxPerMm={pxPerMm} />
            {view === "life-size" && <ScaleBar mm={20} pxPerMm={pxPerMm} />}
            {stale && (
              <p className="stale" role="status">
                This design cannot be built yet, so the last buildable version is shown.
              </p>
            )}
          </div>
        </section>

        <section className="panel side">
          <NumbersPanel sizes={build?.sizes ?? null} numbers={build?.numbers ?? null} />
          {build && <ReportPanel report={build.report} exportable={build.exportable} />}
          {build?.suggestion && (
            <button type="button" className="secondary" onClick={applySuggestion}>
              Use the nearest buildable version
            </button>
          )}
          <button type="button" className="primary" disabled={!build?.exportable || busy} onClick={doExport}>
            Export STL, STEP and spec sheet
          </button>
          {exportMsg && <p role="status">{exportMsg}</p>}
          {view === "life-size" && <CalibrationCard pxPerMm={pxPerMm} onChange={changePxPerMm} />}
        </section>
      </main>
    </div>
  );
}
