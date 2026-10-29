import { useEffect, useState } from "react";

interface Props {
  id: string;
  label: string;
  value: number;
  onChange: (v: number) => void;
  unit?: string;
  step?: number;
  hint?: string;
}

/** Keeps what the user is typing (for example "1.") separate from the number sent upstream. */
export function NumberField({ id, label, value, onChange, unit = "mm", step = 0.1, hint }: Props) {
  const [text, setText] = useState(String(value));
  useEffect(() => {
    if (Number(text) !== value) setText(String(value));
    // only when the upstream value changes, for example when a suggested fix is applied
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-row">
        <input
          id={id}
          aria-describedby={hint ? `${id}-hint` : undefined}
          type="number"
          inputMode="decimal"
          step={step}
          min={step}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            const v = e.target.valueAsNumber;
            if (!Number.isNaN(v) && v > 0) onChange(v);
          }}
        />
        {unit && <span className="unit">{unit}</span>}
      </div>
      {hint && (
        <span id={`${id}-hint`} className="muted small">
          {hint}
        </span>
      )}
    </div>
  );
}
