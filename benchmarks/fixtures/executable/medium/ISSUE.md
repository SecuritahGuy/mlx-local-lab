The timeout is configured in milliseconds, but the transport accepts seconds.
Requests currently wait hundreds of seconds. Preserve the configuration API and
fix the cross-file unit mismatch with the smallest safe change.
