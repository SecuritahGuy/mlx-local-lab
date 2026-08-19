# Local inference network policy

The authoritative security requirement is that every MLX inference server bind
to `127.0.0.1`. Public or LAN binding is not permitted by this project. Health
checks must use the same loopback endpoint and report the active model without
exposing credentials.
