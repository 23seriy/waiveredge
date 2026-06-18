/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    // Backend base URL. Override in .env.local for deployments.
    NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || "https://localhost:8000",
  },
};

module.exports = nextConfig;
