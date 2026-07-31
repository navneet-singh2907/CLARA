import type { NextConfig } from "next";

const internalApiUrl = process.env.CLARA_INTERNAL_API_URL?.replace(/\/$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    if (!internalApiUrl) {
      return [];
    }

    const exactPaths = [
      "/health",
      "/readiness",
      "/cases",
      "/evaluation",
      "/ablation",
      "/guardrails",
      "/drift",
      "/judge-agreement",
      "/report",
      "/docs",
      "/openapi.json",
      "/favicon.ico"
    ];
    const nestedPaths = [
      "/review",
      "/evaluation",
      "/drift",
      "/judge-agreement",
      "/report"
    ];

    return [
      ...exactPaths.map((path) => ({
        source: path,
        destination: `${internalApiUrl}${path}`
      })),
      ...nestedPaths.map((path) => ({
        source: `${path}/:path*`,
        destination: `${internalApiUrl}${path}/:path*`
      }))
    ];
  }
};

export default nextConfig;
