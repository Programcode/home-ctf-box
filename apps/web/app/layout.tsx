import type { Metadata } from 'next';
import { ToastProvider } from '@openrange/ui';
import { Footer } from '@/components/Footer';
import { TopNav } from '@/components/TopNav';
import './globals.css';

export const metadata: Metadata = {
  title: {
    default: 'OpenRange',
    template: '%s · OpenRange',
  },
  description:
    'Self-hosted, browser-accessible cyber range for learning offensive and defensive security in isolated labs.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh bg-bg font-sans text-content antialiased flex flex-col">
        <a
          href="#main-content"
          className="absolute left-4 top-3 z-50 -translate-y-20 rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-accent-ink no-underline focus-visible:translate-y-0"
        >
          Skip to content
        </a>
        <TopNav />
        <main id="main-content" className="flex-1" tabIndex={-1}>
          <ToastProvider>{children}</ToastProvider>
        </main>
        <Footer />
      </body>
    </html>
  );
}
