import { CARD_HEIGHT_MM, CARD_WIDTH_MM, DEFAULT_PX_PER_MM, MAX_PX_PER_MM, MIN_PX_PER_MM, mmToPx } from "../trueScale";

interface Props {
  pxPerMm: number;
  onChange: (v: number) => void;
}

export function CalibrationCard({ pxPerMm, onChange }: Props) {
  return (
    <section aria-label="Screen calibration">
      <h2>True-scale calibration</h2>
      <p className="muted small">
        Hold a bank card against the screen and drag the slider until the outline below matches it. The
        ring is then drawn at its real size.
      </p>
      <div
        className="card-outline"
        data-testid="card-outline"
        style={{ width: mmToPx(CARD_WIDTH_MM, pxPerMm), height: mmToPx(CARD_HEIGHT_MM, pxPerMm) }}
      >
        Bank card
      </div>
      <label htmlFor="calibration">Screen scale</label>
      <input
        id="calibration"
        type="range"
        min={MIN_PX_PER_MM}
        max={MAX_PX_PER_MM}
        step={0.01}
        value={pxPerMm}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <button type="button" className="link" onClick={() => onChange(DEFAULT_PX_PER_MM)}>
        Reset
      </button>
    </section>
  );
}
