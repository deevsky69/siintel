import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PoliceUnitRow } from "@/lib/operations";
import { AssignmentForm } from "./assignment-form";
import type { AssignmentState } from "./operation-state";

/**
 * Server action digantikan tiruan: yang diuji di sini adalah formulirnya — bahwa daftar
 * satuan berasal dari data yang diberikan (bukan ditanam di kode), bahwa status satuan
 * terlihat, dan bahwa satuan yang dipilih benar-benar terkirim.
 */
const assign = vi.fn<(previous: AssignmentState, form: FormData) => Promise<AssignmentState>>();

vi.mock("./actions", () => ({
  assign: (previous: AssignmentState, form: FormData) => assign(previous, form),
}));

const UNITS: PoliceUnitRow[] = [
  {
    code: "UNIT-003",
    unit_name: "Unit Patroli Charlie",
    function: "SAMAPTA",
    jurisdiction: "Polsek Pasar Minggu",
    status: "STANDBY",
  },
  {
    code: "UNIT-004",
    unit_name: "Unit Pembinaan Wilayah",
    function: "BINMAS",
    jurisdiction: "Polres Metro Jakarta Selatan",
    status: "ACTIVE",
  },
];

const SCOPE_BASIS =
  "Pengguna yang dibatasi wilayah menerima satuan di polseknya, ditambah satuan tingkat Polres.";

beforeEach(() => {
  assign.mockReset();
});

function form(props: Partial<Parameters<typeof AssignmentForm>[0]> = {}) {
  return render(
    <AssignmentForm decisionCode="DEC-0086" units={UNITS} scopeBasis={SCOPE_BASIS} {...props} />,
  );
}

describe("formulir penugasan", () => {
  it("menawarkan satuan beserta fungsi dan statusnya", () => {
    // Satuan Standby tetap boleh dipilih; statusnya harus terlihat, bukan disembunyikan.
    form();

    expect(
      screen.getByRole("option", { name: /Unit Patroli Charlie · Samapta · Standby/ }),
    ).toBeDefined();
    expect(
      screen.getByRole("option", { name: /Unit Pembinaan Wilayah · Binmas · Aktif/ }),
    ).toBeDefined();
  });

  it("menyertakan keterangan cakupan dari backend apa adanya", () => {
    // Pengguna Polsek melihat satuan tingkat Polres; alasannya harus terbaca di layar.
    form();

    expect(screen.getByText(SCOPE_BASIS)).toBeDefined();
  });

  it("mengirim keputusan asal dan satuan yang benar-benar dipilih", async () => {
    assign.mockResolvedValue({ error: null, done: "ACT-0054" });
    form();

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "UNIT-004" } });
    fireEvent.click(screen.getByRole("button", { name: /catat penugasan/i }));

    await waitFor(() => expect(assign).toHaveBeenCalledTimes(1));
    const sent = assign.mock.calls[0][1];
    expect(sent.get("decision_code")).toBe("DEC-0086");
    expect(sent.get("unit_code")).toBe("UNIT-004");
  });

  it("menyatakan kegagalan backend sebagai kalimat, bukan kode kesalahan", async () => {
    assign.mockResolvedValue({
      error: "Keputusan ini sudah ditindaklanjuti oleh ACT-0012.",
      done: null,
    });
    form();

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "UNIT-004" } });
    fireEvent.click(screen.getByRole("button", { name: /catat penugasan/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toMatch(/sudah ditindaklanjuti oleh ACT-0012/),
    );
  });

  it("menyatakan daftar satuan kosong apa adanya, bukan mengarang pilihan", () => {
    form({ units: [] });

    expect(screen.queryByRole("combobox")).toBeNull();
    expect(screen.getByText(/Tidak ada satuan yang dapat ditugaskan/i)).toBeDefined();
  });
});
