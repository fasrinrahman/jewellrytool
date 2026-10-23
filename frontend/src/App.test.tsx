import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { ApiError, buildDesign, exportDesign, fetchRules, fetchSizes } from "./api";
import { saveBlob } from "./download";
import { PARAMS, RULES, SIZES, badBuild, goodBuild } from "./test/fixtures";
import type { BuildResponse } from "./types";

vi.mock("./api", async () => ({
  ...(await vi.importActual<typeof import("./api")>("./api")),
  buildDesign: vi.fn(), exportDesign: vi.fn(), fetchRules: vi.fn(), fetchSizes: vi.fn(),
}));
vi.mock("./download", () => ({ saveBlob: vi.fn() }));
// WebGL does not exist in jsdom, so the 3D scene is replaced by a stub that reports its props.
vi.mock("./components/RingPreview", () => ({
  RingPreview: (p: { mesh: unknown; mode: string; metal: string }) => (
    <div data-testid="preview" data-has-mesh={String(!!p.mesh)} data-mode={p.mode} data-metal={p.metal} />
  ),
}));

const build = vi.mocked(buildDesign);
const lastParams = () => build.mock.calls[build.mock.calls.length - 1][0];
const renderApp = () => render(<App debounceMs={10} />);

beforeEach(() => {
  vi.clearAllMocks();
  window.localStorage.clear();
  vi.mocked(fetchRules).mockResolvedValue(RULES);
  vi.mocked(fetchSizes).mockResolvedValue(SIZES);
  build.mockResolvedValue(goodBuild());
});

describe("live preview (FR-11)", () => {
  it("converts the ring size, builds, and shows the mesh and the checks", async () => {
    renderApp();
    await waitFor(() => expect(build).toHaveBeenCalled());
    expect(lastParams()).toMatchObject({ metal: "silver_925", ring_size_mm: 17.32, prong_diameter_mm: 1 });
    expect(await screen.findByText("Ready to export.")).toBeInTheDocument();
    expect(screen.getByTestId("preview")).toHaveAttribute("data-has-mesh", "true");
    expect(screen.getByText("4.90 g")).toBeInTheDocument();
  });

  it("rebuilds with the new value after a parameter changes", async () => {
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.change(screen.getByLabelText("Prong thickness"), { target: { value: "0.9" } });
    await waitFor(() => expect(lastParams().prong_diameter_mm).toBe(0.9));
  });

  it("sends a changed size system through the server converter", async () => {
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.change(screen.getByLabelText("Size system"), { target: { value: "uk" } });
    fireEvent.change(screen.getByLabelText("Size value"), { target: { value: "N\u00bd" } });
    await waitFor(() => expect(fetchSizes).toHaveBeenLastCalledWith("uk", "N\u00bd"));
  });

  it("ignores a slow old response that arrives after a newer one", async () => {
    let releaseFirst!: (r: BuildResponse) => void;
    build.mockImplementationOnce(() => new Promise<BuildResponse>((res) => { releaseFirst = res; }));
    build.mockResolvedValue(goodBuild(2.0));

    renderApp();
    await waitFor(() => expect(build).toHaveBeenCalledTimes(1)); // first request is still pending
    fireEvent.change(screen.getByLabelText("Prong thickness"), { target: { value: "0.9" } });
    expect(await screen.findByText("2.00 g")).toBeInTheDocument(); // the newer answer is on screen

    await act(async () => releaseFirst(goodBuild(9.99))); // the old answer finally arrives
    expect(screen.getByText("2.00 g")).toBeInTheDocument();
    expect(screen.queryByText("9.99 g")).not.toBeInTheDocument();
  });

  it("passes the chosen metal to the preview so it can colour the ring", async () => {
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.change(screen.getByLabelText("Metal"), { target: { value: "gold_14k" } });
    expect(screen.getByTestId("preview")).toHaveAttribute("data-metal", "gold_14k");
  });
});

describe("a design that cannot be built (FR-06, NFR-01)", () => {
  beforeEach(() => {
    build.mockImplementation(async (p) => (p.prong_diameter_mm < 0.8 ? badBuild() : goodBuild()));
  });

  it("keeps the last buildable ring on screen, says why, and blocks export", async () => {
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.change(screen.getByLabelText("Prong thickness"), { target: { value: "0.4" } });
    expect(await screen.findByText(/last buildable version is shown/)).toBeInTheDocument();
    expect(screen.getByTestId("preview")).toHaveAttribute("data-has-mesh", "true");
    expect(screen.getByText(/could bend or break/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Export STL/ })).toBeDisabled();
  });

  it("applies the nearest buildable version in one click", async () => {
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.change(screen.getByLabelText("Prong thickness"), { target: { value: "0.4" } });
    fireEvent.click(await screen.findByRole("button", { name: "Use the nearest buildable version" }));
    await waitFor(() => expect(lastParams().prong_diameter_mm).toBe(0.8));
    expect(await screen.findByText("Ready to export.")).toBeInTheDocument();
    expect(screen.getByLabelText("Prong thickness")).toHaveValue(0.8);
  });
});

describe("export (FR-09, FR-10)", () => {
  it("downloads the zip for a design that passes", async () => {
    const blob = new Blob(["zip"]);
    vi.mocked(exportDesign).mockResolvedValue(blob);
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.click(screen.getByRole("button", { name: /Export STL/ }));
    await waitFor(() => expect(saveBlob).toHaveBeenCalledWith(blob, "ring_design.zip"));
    expect(exportDesign).toHaveBeenCalledWith(expect.objectContaining({ ...PARAMS }));
    expect(await screen.findByText(/Downloaded ring_design.zip/)).toBeInTheDocument();
  });

  it("shows the server's reason when an export is refused", async () => {
    vi.mocked(exportDesign).mockRejectedValue(new ApiError("Export refused: a check failed.", 422));
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.click(screen.getByRole("button", { name: /Export STL/ }));
    expect(await screen.findByText("Export refused: a check failed.")).toBeInTheDocument();
    expect(saveBlob).not.toHaveBeenCalled();
  });
});

describe("true-scale view (FR-11)", () => {
  it("switches to life size, shows the scale bar, and keeps the calibration", async () => {
    renderApp();
    await screen.findByText("Ready to export.");
    expect(screen.queryByTestId("scale-bar")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Life size" }));
    expect(screen.getByTestId("preview")).toHaveAttribute("data-mode", "life-size");
    expect(screen.getByTestId("scale-bar")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Screen scale"), { target: { value: "4.5" } });
    expect(screen.getByTestId("card-outline").style.width).toBe(`${85.6 * 4.5}px`);
    expect(window.localStorage.getItem("pxPerMm")).toBe("4.5");
  });

  it("starts from a saved calibration", async () => {
    window.localStorage.setItem("pxPerMm", "5");
    renderApp();
    await screen.findByText("Ready to export.");
    fireEvent.click(screen.getByRole("button", { name: "Life size" }));
    expect(screen.getByTestId("card-outline").style.width).toBe(`${85.6 * 5}px`);
  });
});

describe("honesty and errors (NFR-04)", () => {
  it("tells the user the rules and prices are placeholders", async () => {
    renderApp();
    expect(await screen.findByText(/placeholders and have not been reviewed by a jeweler/)).toBeInTheDocument();
  });

  it("says so when the design server cannot be reached", async () => {
    vi.mocked(fetchRules).mockRejectedValue(new ApiError("Could not reach the design server. Is it running?", 0));
    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach the design server");
  });

  it("shows a size the converter rejects, without crashing", async () => {
    vi.mocked(fetchSizes).mockRejectedValueOnce(new ApiError("That size is outside the supported range.", 422));
    renderApp();
    expect(await screen.findByText("That size is outside the supported range.")).toBeInTheDocument();
  });
});
