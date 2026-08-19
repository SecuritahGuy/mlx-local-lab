# Sample service contract

`profile()` returns the stored user for a known integer ID. For an unknown ID, the repository's
documented contract intentionally propagates `KeyError`; the API host outside this fixture maps that
exception to HTTP 404. Do not change `get_user()` or `profile()` to return `None`.

Refresh tokens are valid only when their kind is `refresh` and their expiration is in the future.
Production error payloads must not contain exception details unless debug mode is explicitly true.
