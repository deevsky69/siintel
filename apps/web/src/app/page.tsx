export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center gap-4 p-8">
      <h1 className="text-2xl font-semibold">PREDIKSI PRESISI</h1>
      <p className="text-sm opacity-80">
        Skeleton aplikasi web (TASK 001). Belum ada fitur bisnis.
      </p>
      <p className="text-sm opacity-80">
        API base URL: <code>{process.env.NEXT_PUBLIC_API_BASE_URL ?? "belum dikonfigurasi"}</code>
      </p>
    </main>
  );
}
