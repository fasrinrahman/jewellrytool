import { metalLabel } from "../params";
import type { FormParams, Rules, SizeInput, SizeSystem, Sizes } from "../types";
import { NumberField } from "./NumberField";

interface Props {
  rules: Rules | null;
  form: FormParams;
  onChange: (patch: Partial<FormParams>) => void;
  sizeInput: SizeInput;
  onSizeChange: (s: SizeInput) => void;
  sizeError: string | null;
  sizes: Sizes | null;
}

const SYSTEMS: { id: SizeSystem; label: string }[] = [
  { id: "us", label: "US" },
  { id: "uk", label: "UK (approximate)" },
  { id: "eu", label: "EU" },
  { id: "mm", label: "Inner diameter (mm)" },
];

export function ParamForm({ rules, form, onChange, sizeInput, onSizeChange, sizeError, sizes }: Props) {
  if (!rules) return <p className="muted">Loading design rules...</p>;
  const metals = Object.keys(rules.metals);
  const shape = rules.stone_shapes[form.stone_shape];

  return (
    <form className="form" onSubmit={(e) => e.preventDefault()} aria-label="Ring design">
      <h2>Design</h2>

      <div className="field">
        <label htmlFor="metal">Metal</label>
        <select id="metal" value={form.metal} onChange={(e) => onChange({ metal: e.target.value })}>
          {metals.map((m) => (
            <option key={m} value={m}>
              {metalLabel(m)}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor="finish">Finish</label>
        <select
          id="finish"
          value={form.finish}
          onChange={(e) => onChange({ finish: e.target.value as FormParams["finish"] })}
        >
          <option value="polished">Polished</option>
          <option value="satin">Satin</option>
        </select>
      </div>

      <fieldset>
        <legend>Ring size</legend>
        <div className="input-row">
          <select
            aria-label="Size system"
            value={sizeInput.system}
            onChange={(e) => onSizeChange({ ...sizeInput, system: e.target.value as SizeSystem })}
          >
            {SYSTEMS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
          <input
            aria-label="Size value"
            type="text"
            value={sizeInput.value}
            onChange={(e) => onSizeChange({ ...sizeInput, value: e.target.value })}
          />
        </div>
        {sizeError ? (
          <p className="error" role="alert">
            {sizeError}
          </p>
        ) : (
          sizes && <p className="muted">Inner diameter {sizes.mm} mm</p>
        )}
      </fieldset>

      <NumberField id="band_width" label="Band width" value={form.band_width_mm}
        onChange={(v) => onChange({ band_width_mm: v })} />
      <NumberField id="band_thickness" label="Band thickness" value={form.band_thickness_mm}
        onChange={(v) => onChange({ band_thickness_mm: v })} />
      <NumberField id="stone_size" label="Stone size (round)" value={form.stone_size_mm}
        onChange={(v) => onChange({ stone_size_mm: v })} />
      <NumberField id="prong_diameter" label="Prong thickness" value={form.prong_diameter_mm}
        onChange={(v) => onChange({ prong_diameter_mm: v })} />

      <div className="field">
        <label htmlFor="prong_count">Prongs</label>
        <select
          id="prong_count"
          value={form.prong_count}
          onChange={(e) => onChange({ prong_count: Number(e.target.value) })}
        >
          {shape.prong_counts.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>
    </form>
  );
}
