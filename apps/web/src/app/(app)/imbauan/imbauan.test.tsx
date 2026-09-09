import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { AlertCandidate, PublicAlert } from "@/lib/public-alerts";
import { AlertBoard } from "./alert-board";

vi.mock("./actions", () => ({
  publish: vi.fn(),
  withdraw: vi.fn(),
}));

/**
 * Yang diuji di sini adalah hal-hal yang membuat layar ini **menyesatkan** bila rusak:
 *
 * - tombol terbit yang tampak bagi peran yang tidak berwenang;
 * - rancangan kalimat yang terbaca sebagai isi yang sudah tersimpan;
 * - ketiadaan ambang severity yang didiamkan.
 */

const GATE =
  "TIDAK ada ambang severity minimum di kanal ini. Kewenangan menerbitkan ditetapkan pemilik proyek 9 September 2026 pada peran Pimpinan, tetapi ambang severity-nya belum ditetapkan (sisa U-10).";
const DRAFT =
  "`suggested_message` diturunkan ATURAN dari kolom peringatannya dan berstatus RANCANGAN.";
const LIST = "Imbauan tidak menyimpan lokasi internal.";

const alert: PublicAlert = {
  code: "PAL-0026",
  severity: "CRITICAL",
  threat_type: "CURANMOR",
  area_text: "Kecamatan Tebet",
  time_window: "18:00-23:59",
  window_start: null,
  window_end: null,
  status: "ACTIVE",
  public_message: "Imbauan kewaspadaan terhadap CURANMOR di wilayah Kecamatan Tebet.",
  warning_code: "WRN-00053",
  published_at: "2026-09-09T02:00:00Z",
};

const candidate: AlertCandidate = {
  warning_code: "WRN-00062",
  severity: "WARNING",
  threat_type: "CURAT",
  time_window: "12:00-18:00",
  window_start: null,
  window_end: null,
  kecamatan: "Pancoran",
  suggested_message:
    "Imbauan kewaspadaan terhadap CURAT di wilayah Pancoran pada pukul 12:00-18:00 WIB. Laporkan hal mencurigakan.",
};

function board(canPublish: boolean) {
  return render(
    <AlertBoard
      alerts={[alert]}
      candidates={[candidate]}
      canPublish={canPublish}
      gateBasis={GATE}
      draftBasis={DRAFT}
      listBasis={LIST}
    />,
  );
}

describe("kanal imbauan", () => {
  it("menyatakan bahwa tidak ada ambang severity, alih-alih mendiamkannya", () => {
    // Layar yang diam soal ini membuat pembacanya mengira ada penyaringan.
    board(true);

    expect(screen.getByText(/TIDAK ada ambang severity minimum/)).toBeDefined();
    expect(screen.getByText("TANPA AMBANG")).toBeDefined();
  });

  it("menyembunyikan tombol terbit dari peran yang tidak berwenang", () => {
    // Penyembunyian ini hanya kenyamanan — backend tetap yang menolak (CLAUDE.md §21) —
    // tetapi menjanjikan tombol yang pasti gagal adalah kekejaman tersendiri.
    board(false);

    expect(screen.queryByRole("button", { name: /Terbitkan Imbauan/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Cabut Imbauan/ })).toBeNull();
    expect(screen.getByText(/keputusan komando dan berada pada Pimpinan/)).toBeDefined();
  });

  it("mengisi kotak dengan rancangan, dan menyebutnya rancangan", () => {
    board(true);

    const isian = screen.getByRole("textbox") as HTMLTextAreaElement;
    expect(isian.value).toBe(candidate.suggested_message);
    expect(screen.getByText(/berstatus RANCANGAN/)).toBeDefined();
  });

  it("menyebut peringatan yang menjadi dasar tiap imbauan yang beredar", () => {
    // Imbauan yang tidak dapat dikembalikan ke prediksinya tidak dapat dipertanggungjawabkan.
    board(true);

    expect(screen.getByText(/Dasar: WRN-00053/)).toBeDefined();
  });

  it("menyatakan keadaan kosong sebagai belum ada yang diumumkan, bukan layar rusak", () => {
    render(
      <AlertBoard
        alerts={[]}
        candidates={[]}
        canPublish
        gateBasis={GATE}
        draftBasis={DRAFT}
        listBasis={LIST}
      />,
    );

    expect(screen.getByText(/belum ada yang diputuskan untuk diumumkan/)).toBeDefined();
  });
});
