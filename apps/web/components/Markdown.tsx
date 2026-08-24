import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Markdown renderer for learner-facing content (module blocks, challenge
 * descriptions). Raw HTML is disabled by react-markdown default, so content
 * from the API can never inject scripts.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="or-prose max-w-[70ch] text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent underline underline-offset-4 hover:no-underline"
              >
                {children}
              </a>
            );
          },
          ul({ children }) {
            return <ul className="my-2 list-disc pl-5">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="my-2 list-decimal pl-5">{children}</ol>;
          },
          li({ children }) {
            return <li className="mt-1">{children}</li>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="my-3 border-l-2 border-edge-strong pl-3 text-muted">
                {children}
              </blockquote>
            );
          },
          code({ className, children }) {
            const isBlock = typeof className === 'string' && className.includes('language-');
            if (!isBlock) {
              return (
                <code className="rounded bg-raised px-1 py-0.5 font-mono text-[0.85em]">
                  {children}
                </code>
              );
            }
            return <code className="font-mono text-[0.85em]">{children}</code>;
          },
          pre({ children }) {
            return (
              <pre className="my-3 overflow-x-auto rounded-md border border-edge bg-raised p-3">
                {children}
              </pre>
            );
          },
          table({ children }) {
            return (
              <div className="my-3 overflow-x-auto">
                <table className="w-full border-collapse text-left text-xs">{children}</table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="border-b border-edge-strong px-2 py-1.5 font-mono uppercase tracking-wide text-muted">
                {children}
              </th>
            );
          },
          td({ children }) {
            return <td className="border-b border-edge px-2 py-1.5">{children}</td>;
          },
          hr() {
            return <hr className="my-4 border-edge" />;
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
