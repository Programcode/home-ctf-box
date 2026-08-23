import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '../components/Button';

const meta = {
  title: 'Components/Button',
  component: Button,
} satisfies Meta<typeof Button>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Primary: Story = {
  args: { children: 'Start lab', variant: 'primary' },
};

export const Secondary: Story = {
  args: { children: 'View catalog', variant: 'secondary' },
};

export const Ghost: Story = {
  args: { children: 'Cancel', variant: 'ghost' },
};

export const Danger: Story = {
  args: { children: 'Stop lab', variant: 'danger' },
};

export const Small: Story = {
  args: { children: 'Extend +30m', variant: 'secondary', size: 'sm' },
};

export const Large: Story = {
  args: { children: 'Create account', variant: 'primary', size: 'lg' },
};

export const Disabled: Story = {
  args: { children: 'Sign in required', variant: 'primary', disabled: true },
};
