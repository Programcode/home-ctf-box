import type { HTMLAttributes, ReactNode } from 'react';

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={['or-card', className].filter(Boolean).join(' ')} {...rest} />;
}

export function CardHeader({ title, actions }: { title: ReactNode; actions?: ReactNode }) {
  return (
    <div className="or-card__header">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '0.75rem',
        }}
      >
        <h3 className="or-card__title">{title}</h3>
        {actions}
      </div>
    </div>
  );
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={['or-card__body', className].filter(Boolean).join(' ')} {...rest} />;
}

export function CardFooter({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={['or-card__footer', className].filter(Boolean).join(' ')} {...rest} />;
}
