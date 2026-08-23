import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Button } from '../src/components/Button';

describe('Button', () => {
  it('renders an accessible button with its label as the accessible name', () => {
    render(<Button>Start lab</Button>);
    const button = screen.getByRole('button', { name: 'Start lab' });
    expect(button).toBeInTheDocument();
    expect(button.tagName).toBe('BUTTON');
  });

  it('defaults to type=button so forms do not submit implicitly', () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button');
  });

  it('fires onClick on keyboard activation via Enter', () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Run</Button>);
    const button = screen.getByRole('button');
    fireEvent.keyDown(button, { key: 'Enter' });
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('exposes the disabled state and blocks clicks', () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Extend
      </Button>,
    );
    const button = screen.getByRole('button', { name: 'Extend' });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('marks destructive actions with the danger variant for non-color cues too', () => {
    render(<Button variant="danger">Stop lab</Button>);
    expect(screen.getByRole('button')).toHaveAttribute('data-variant', 'danger');
    expect(screen.getByRole('button').className).toContain('or-btn--danger');
  });
});
