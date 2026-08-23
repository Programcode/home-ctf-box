export function Footer() {
  return (
    <footer className="mt-auto border-t border-edge bg-panel">
      <div className="mx-auto grid max-w-6xl gap-4 px-4 py-8 text-sm text-muted sm:px-6 md:grid-cols-2">
        <div>
          <p className="m-0">
            OpenRange is free software under{' '}
            <a
              className="text-content underline decoration-edge-strong underline-offset-4 hover:decoration-muted"
              href="https://www.gnu.org/licenses/agpl-3.0.html"
              rel="noreferrer noopener"
              target="_blank"
            >
              AGPL-3.0-or-later
            </a>
            . Room content is CC BY-SA 4.0.
          </p>
        </div>
        <div>
          <p className="m-0 font-mono text-xs leading-relaxed">
            Safety notice: labs run only inside isolated containers on your own infrastructure.
            Nothing here targets systems you do not own.
          </p>
          <a
            className="mt-2 inline-block text-content underline decoration-edge-strong underline-offset-4 hover:decoration-muted"
            href="https://github.com/Programcode/home-ctf-box"
            rel="noreferrer noopener"
            target="_blank"
          >
            Source on GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
