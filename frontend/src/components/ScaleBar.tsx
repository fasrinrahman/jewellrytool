import { mmToPx } from "../trueScale";

export function ScaleBar({ mm, pxPerMm }: { mm: number; pxPerMm: number }) {
  return (
    <div className="scale-bar" data-testid="scale-bar">
      <div className="bar" style={{ width: mmToPx(mm, pxPerMm) }} />
      <span>{mm} mm</span>
    </div>
  );
}
