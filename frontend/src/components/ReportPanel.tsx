import { STATUS_LABEL } from "../params";
import type { CheckResult } from "../types";

interface Props {
  report: CheckResult[];
  exportable: boolean;
}

export function ReportPanel({ report, exportable }: Props) {
  return (
    <section aria-label="Validation report">
      <h2>Checks</h2>
      <p className={exportable ? "ok" : "error"} role="status">
        {exportable ? "Ready to export." : "Not ready to export: fix the failed checks first."}
      </p>
      <ul className="report">
        {report.map((r) => (
          <li key={r.check_id} className={`check ${r.status}`}>
            <span className="badge">{STATUS_LABEL[r.status]}</span>
            <span className="message">{r.message}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
