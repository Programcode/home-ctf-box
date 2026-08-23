'use client';

import { useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';

export interface TabItem {
  id: string;
  label: string;
  content: ReactNode;
}

export interface TabsProps {
  items: readonly TabItem[];
  label: string;
}

/**
 * WAI-ARIA tabs with roving tabindex and arrow-key navigation
 * (selection follows focus). Client component.
 */
export function Tabs({ items, label }: TabsProps) {
  const [activeId, setActiveId] = useState(items[0]?.id ?? '');
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  const activeIndex = Math.max(
    0,
    items.findIndex((item) => item.id === activeId),
  );
  const active = items[activeIndex];

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const count = items.length;
    if (count === 0) {
      return;
    }
    let next: number | undefined;
    switch (event.key) {
      case 'ArrowRight': {
        next = (activeIndex + 1) % count;
        break;
      }
      case 'ArrowLeft': {
        next = (activeIndex - 1 + count) % count;
        break;
      }
      case 'Home': {
        next = 0;
        break;
      }
      case 'End': {
        next = count - 1;
        break;
      }
      default: {
        return;
      }
    }
    event.preventDefault();
    const candidate = items[next];
    if (candidate === undefined) {
      return;
    }
    setActiveId(candidate.id);
    tabRefs.current[next]?.focus();
  }

  return (
    <div>
      <div className="or-tabs__list" role="tablist" aria-label={label}>
        {items.map((item, index) => (
          <button
            key={item.id}
            ref={(node) => {
              tabRefs.current[index] = node;
            }}
            type="button"
            role="tab"
            id={`tab-${item.id}`}
            className="or-tab"
            aria-selected={item.id === activeId}
            aria-controls={`tabpanel-${item.id}`}
            tabIndex={item.id === activeId ? 0 : -1}
            onClick={() => setActiveId(item.id)}
            onKeyDown={onKeyDown}
          >
            {item.label}
          </button>
        ))}
      </div>
      {active === undefined ? null : (
        <div
          key={active.id}
          role="tabpanel"
          id={`tabpanel-${active.id}`}
          aria-labelledby={`tab-${active.id}`}
          className="or-tabpanel"
          tabIndex={0}
        >
          {active.content}
        </div>
      )}
    </div>
  );
}
