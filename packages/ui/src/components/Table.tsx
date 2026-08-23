import type {
  HTMLAttributes,
  ReactNode,
  TableHTMLAttributes,
  TdHTMLAttributes,
  ThHTMLAttributes,
} from 'react';

/** Horizontally scrollable region for data tables on narrow viewports. */
export function TableContainer({ children }: { children: ReactNode }) {
  return (
    <div style={{ overflowX: 'auto' }} tabIndex={0} aria-label="Scrollable table">
      {children}
    </div>
  );
}

export function Table({ className, ...rest }: TableHTMLAttributes<HTMLTableElement>) {
  return <table className={['or-table', className].filter(Boolean).join(' ')} {...rest} />;
}

export function THead(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead {...props} />;
}

export function TBody(props: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody {...props} />;
}

export function TR(props: HTMLAttributes<HTMLTableRowElement>) {
  return <tr {...props} />;
}

export function TH({ className, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={className} scope="col" {...rest} />;
}

export function TD({ className, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={className} {...rest} />;
}
