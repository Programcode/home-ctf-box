import type { Preview } from '@storybook/react';
import '../src/tokens.css';
import '../src/components.css';

const preview: Preview = {
  parameters: {
    layout: 'centered',
    backgrounds: {
      default: 'openrange',
      values: [{ name: 'openrange', value: '#0b0d10' }],
    },
  },
};

export default preview;
