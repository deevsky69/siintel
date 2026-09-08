/**
 * Penambal jsdom untuk test komponen.
 *
 * jsdom tidak mengimplementasikan `matchMedia`, sedangkan pengalih tema memakainya untuk
 * mengetahui setelan gelap/terang perangkat. Tanpa penambal ini seluruh test yang merender
 * shell gagal dengan `window.matchMedia is not a function` — kegagalan yang tidak ada
 * hubungannya dengan apa yang sedang diuji.
 *
 * Nilai bawaannya `matches: false`, yang berarti "perangkat tidak meminta mode gelap".
 * Dipilih begitu supaya test yang tidak peduli tema berjalan pada satu keadaan yang tetap.
 */
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}
