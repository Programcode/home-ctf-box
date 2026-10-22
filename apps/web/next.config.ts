import path from 'node:path';
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Playwright and local curls use 127.0.0.1 while `next dev` also answers
  // on localhost. Allow both so dev assets are not treated as cross-origin.
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  transpilePackages: ['@openrange/ui', '@openrange/contracts'],
  // The monorepo root is one level up; keeps Next from guessing wrong when
  // stray lockfiles exist elsewhere on the machine.
  outputFileTracingRoot: path.join(import.meta.dirname, '..', '..'),
  // Emit .next/standalone so the production image ships a minimal server
  // bundle instead of the full node_modules tree.
  output: 'standalone',
};

export default nextConfig;
