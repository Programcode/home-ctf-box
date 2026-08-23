import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <p className="m-0 font-mono text-6xl font-bold text-accent">404</p>
      <h1 className="mt-4 text-xl font-semibold">This room does not exist.</h1>
      <p className="mt-2 mb-8 text-sm text-muted">
        The catalog is the source of truth; if a room was retired, its page goes with it.
      </p>
      <Link
        href="/catalog"
        className="rounded-md border border-edge-strong px-4 py-2 text-sm text-content no-underline hover:border-muted"
      >
        Back to the catalog
      </Link>
    </div>
  );
}
