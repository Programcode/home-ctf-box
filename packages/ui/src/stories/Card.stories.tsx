import type { Meta, StoryObj } from '@storybook/react';
import { Badge } from '../components/Badge';
import { Card, CardBody, CardFooter, CardHeader } from '../components/Card';
import { Button } from '../components/Button';

const meta = {
  title: 'Components/Card',
  component: Card,
} satisfies Meta<typeof Card>;

export default meta;

type Story = StoryObj<typeof meta>;

export const RoomCard: Story = {
  name: 'Room card',
  render: () => (
    <Card style={{ width: '20rem' }}>
      <CardHeader title="Pickle Jar" actions={<Badge variant="warning">medium</Badge>} />
      <CardBody>
        Craft a pickle payload whose reduce method runs code inside the service and capture the flag
        from the restored-state echo.
      </CardBody>
      <CardFooter>
        <span>275 pts</span>
        <span>~35 min</span>
        <Button size="sm">Open room</Button>
      </CardFooter>
    </Card>
  ),
};

export const PlainPanel: Story = {
  name: 'Plain panel',
  render: () => (
    <Card style={{ width: '24rem' }}>
      <CardHeader title="Session details" />
      <CardBody>Created 2 hours ago from 203.0.113.7 via Firefox on Linux.</CardBody>
    </Card>
  ),
};
