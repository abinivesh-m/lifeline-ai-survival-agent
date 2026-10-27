/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The demo runs from a laptop with no internet: never reach out at build time.
  images: { unoptimized: true },
};

export default nextConfig;
