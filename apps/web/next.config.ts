import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Menghasilkan server mandiri di `.next/standalone` — dipakai image produksi
  // agar container tidak perlu memuat seluruh node_modules (infra/docker/Dockerfile).
  output: "standalone",
};

export default nextConfig;
