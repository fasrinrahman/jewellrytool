import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { DEFAULT_FORM } from "../params";
import { RULES, SIZES, goodBuild } from "../test/fixtures";
import { DEFAULT_PX_PER_MM } from "../trueScale";
import { CalibrationCard } from "./CalibrationCard";
import { NumberField } from "./NumberField";
import { NumbersPanel } from "./NumbersPanel";
import { ParamForm } from "./ParamForm";
import { ReportPanel } from "./ReportPanel";
import { ScaleBar } from "./ScaleBar";

describe("ReportPanel (FR-05)", () => {
  it("shows a text label for every status, not just a colour", () => {
    render(<ReportPanel exportable={false} report={[
      { check_id: "a", layer: 1, status: "pass", message: "Passed thing.", fix: null },
      { check_id: "b", layer: 1, status: "warn", message: "Warned thing.", fix: null },
      { check_id: "c", layer: 1, status: "fail", message: "Failed thing.", fix: null },
      { check_id: "d", layer: null, status: "unverified", message: "Unchecked thing.", fix: null },
    ]} />);
    for (const label of ["PASS", "WARN", "FAIL", "NOT CHECKED"]) expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText("Failed thing.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Not ready to export");
  });

  it("says when the design is ready", () => {
    render(<ReportPanel exportable report={goodBuild().report} />);
    expect(screen.getByRole("status")).toHaveTextContent("Ready to export.");
  });
});

describe("NumbersPanel (FR-07, FR-08, NFR-03)", () => {
  it("shows sizes, weight, cost range, source and date, and flags unverified prices", () => {
    const b = goodBuild();
    render(<NumbersPanel sizes={b.sizes} numbers={b.numbers} />);
    expect(screen.getByText("N\u00bd")).toBeInTheDocument();
    expect(screen.getByText("UK size (approximate)")).toBeInTheDocument();
    expect(screen.getByText("4.90 g")).toBeInTheDocument();
    expect(screen.getByText(/USD 3.92 to 5.88 for the metal only/)).toBeInTheDocument();
    expect(screen.getByText(/PLACEHOLDER, as of 2026-10-14/)).toBeInTheDocument();
    expect(screen.getByText(/have not been verified/)).toBeInTheDocument();
  });

  it("explains why there is no weight yet", () => {
    render(<NumbersPanel sizes={SIZES} numbers={null} />);
    expect(screen.getByText(/appear once the design can be built/)).toBeInTheDocument();
  });
});

describe("ParamForm", () => {
  const base = { rules: RULES, form: DEFAULT_FORM, sizeInput: { system: "us" as const, value: "7" }, sizeError: null, sizes: SIZES };

  it("offers the metals and prong counts that the rules allow", () => {
    render(<ParamForm {...base} onChange={vi.fn()} onSizeChange={vi.fn()} />);
    expect(screen.getByRole("option", { name: "silver 925" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "gold 14k" })).toBeInTheDocument();
    expect(screen.getByLabelText("Prongs").querySelectorAll("option")).toHaveLength(2);
  });

  it("shows the allowed range next to each measurement, so users do not have to guess", () => {
    render(<ParamForm {...base} onChange={vi.fn()} onSizeChange={vi.fn()} />);
    expect(screen.getByLabelText("Band thickness")).toHaveAccessibleDescription("Allowed: 1.2 to 5 mm");
    expect(screen.getByLabelText("Prong thickness")).toHaveAccessibleDescription("Allowed: 0.8 to 2 mm");
    expect(screen.getByLabelText("Band width")).toHaveAccessibleDescription("Allowed: 1.5 to 8 mm");
    expect(screen.getByLabelText("Stone size (round)")).toHaveAccessibleDescription("Allowed: 3 to 10 mm");
    expect(screen.getByText("Supported: 14 to 24 mm inner diameter")).toBeInTheDocument();
  });

  it("the hints follow the chosen metal", () => {
    const rules = { ...RULES, metals: { ...RULES.metals, gold_14k: { ...RULES.metals.gold_14k, max_band_thickness_mm: 4 } } };
    render(<ParamForm {...base} rules={rules} form={{ ...DEFAULT_FORM, metal: "gold_14k" }} onChange={vi.fn()} onSizeChange={vi.fn()} />);
    expect(screen.getByLabelText("Band thickness")).toHaveAccessibleDescription("Allowed: 1.2 to 4 mm");
  });

  it("reports a changed number as a number", () => {
    const onChange = vi.fn();
    render(<ParamForm {...base} onChange={onChange} onSizeChange={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Prong thickness"), { target: { value: "0.9" } });
    expect(onChange).toHaveBeenCalledWith({ prong_diameter_mm: 0.9 });
  });

  it("reports a changed size system and value", () => {
    const onSizeChange = vi.fn();
    render(<ParamForm {...base} onChange={vi.fn()} onSizeChange={onSizeChange} />);
    fireEvent.change(screen.getByLabelText("Size system"), { target: { value: "uk" } });
    expect(onSizeChange).toHaveBeenCalledWith({ system: "uk", value: "7" });
    fireEvent.change(screen.getByLabelText("Size value"), { target: { value: "8" } });
    expect(onSizeChange).toHaveBeenCalledWith({ system: "us", value: "8" });
  });

  it("shows a size problem in plain words", () => {
    render(<ParamForm {...base} sizeError="That size is outside the supported range." onChange={vi.fn()} onSizeChange={vi.fn()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("outside the supported range");
  });

  it("waits for the rules instead of showing an empty form", () => {
    render(<ParamForm {...base} rules={null} onChange={vi.fn()} onSizeChange={vi.fn()} />);
    expect(screen.getByText(/Loading design rules/)).toBeInTheDocument();
  });
});

describe("NumberField", () => {
  it("does not send half-typed or empty input upstream", () => {
    const onChange = vi.fn();
    render(<NumberField id="x" label="Width" value={3} onChange={onChange} />);
    const input = screen.getByLabelText("Width");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.change(input, { target: { value: "-2" } });
    expect(onChange).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "2.5" } });
    expect(onChange).toHaveBeenCalledWith(2.5);
  });

  it("follows the value when it is changed from outside, for example by a suggested fix", () => {
    const { rerender } = render(<NumberField id="x" label="Width" value={0.4} onChange={vi.fn()} />);
    rerender(<NumberField id="x" label="Width" value={0.8} onChange={vi.fn()} />);
    expect(screen.getByLabelText("Width")).toHaveValue(0.8);
  });
});

describe("true-scale controls (FR-11)", () => {
  it("draws the bank card outline at card size times the scale", () => {
    render(<CalibrationCard pxPerMm={4} onChange={vi.fn()} />);
    const card = screen.getByTestId("card-outline");
    expect(card.style.width).toBe(`${85.6 * 4}px`);
    expect(card.style.height).toBe(`${53.98 * 4}px`);
  });

  it("changes the scale from the slider and can reset it", () => {
    const onChange = vi.fn();
    render(<CalibrationCard pxPerMm={4} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Screen scale"), { target: { value: "4.5" } });
    expect(onChange).toHaveBeenCalledWith(4.5);
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(onChange).toHaveBeenLastCalledWith(DEFAULT_PX_PER_MM);
  });

  it("scale bar is mm times the scale wide", () => {
    render(<ScaleBar mm={20} pxPerMm={4} />);
    expect(screen.getByTestId("scale-bar").querySelector(".bar")).toHaveStyle({ width: "80px" });
    expect(screen.getByText("20 mm")).toBeInTheDocument();
  });
});
