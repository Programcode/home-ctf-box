# Wrong Method

Nimbus says its admin console is closed to browsers, yet the only thing
checking is the HTTP verb on the request. You will confirm the block,
swap the method on the identical request, and see how little the filter
actually inspects.

## What you will practice

- Reading a route guard that trusts one request attribute.
- Sending the same request with a different HTTP method.
- Confirming the bypass by capturing the per-session flag.

## Scope

Only the console at `http://target:8000` is in scope. Nothing outside
your lab instance is a target.
