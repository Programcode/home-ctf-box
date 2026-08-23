import type { Meta, StoryObj } from '@storybook/react';
import { Badge } from '../components/Badge';

const meta = {
  title: 'Components/Badge',
  component: Badge,
} satisfies Meta<typeof Badge>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: { children: 'web-foundations' },
};

export const Beginner: Story = {
  name: 'Difficulty: beginner',
  render: () => <Badge variant="success">beginner</Badge>,
};

export const Medium: Story = {
  name: 'Difficulty: medium',
  render: () => <Badge variant="warning">medium</Badge>,
};

export const ExpiredLab: Story = {
  name: 'Lab state: expired',
  render: () => <Badge variant="danger">expired</Badge>,
};
