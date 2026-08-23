# Route Less Traveled

The gateway service on this host fronts a simulated router fabric.
Like a lot of operational software, it exposes more about itself than
it intends: the metrics endpoint prints the whole interface table, and
the route action steers a probe toward any subnet you can name. Three
interfaces exist. One is where you already are, one is a bridge that
goes nowhere useful, and one is a tunnel to a segment that has
something worth reading.

## What you will practice

- Enumerating before acting. The table in /metrics separates local,
  bridge, and tunnel interfaces; each line names the device and the
  subnet behind it. Reading it beats guessing subnets one POST at a
  time.
- Reading Prometheus-style text output. Real infrastructure exports
  state exactly this way: comment lines, then key-value samples with
  labeled braces. Being fluent in that format pays off on nearly every
  engagement and incident you will touch.
- Routing deliberately. The /route action fails closed: wrong or
  unreachable segments return an explanatory 404 rather than an error
  splat. In real networks a route to nowhere disappears silently, so
  this room's prose replies are a kindness you should not expect twice.

Subnet notation matters here. The gateway wants the network address
with its prefix length, which is how routing tables actually speak;
bare addresses are refused.

## Scope

Only `http://target:8000` is in scope. All interfaces, tunnels, and
segments are simulated inside one Flask process; nothing touches real
network namespaces or host routing tables.
