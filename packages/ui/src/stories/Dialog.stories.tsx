import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { Dialog } from '../components/Dialog';
import { Button } from '../components/Button';

function ControlledDialog() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Open dialog</Button>
      <Dialog open={open} onClose={() => setOpen(false)} title="Quick actions">
        <p>Focus is trapped here; Escape closes the dialog.</p>
      </Dialog>
    </>
  );
}

const meta = {
  title: 'Components/Dialog',
  component: Dialog,
} satisfies Meta<typeof Dialog>;

export default meta;

type Story = StoryObj<typeof meta>;

export const Interactive: Story = {
  name: 'Command palette style',
  parameters: { layout: 'fullscreen' },
  args: {
    open: false,
    title: 'Quick actions',
    children: null,
    onClose: () => {},
  },
  render: () => (
    <div style={{ padding: '2rem' }}>
      <ControlledDialog />
    </div>
  ),
};
