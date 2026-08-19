`is_safe_redirect` accepts protocol-relative URLs such as `//evil.example`.
Make the smallest defensive change that blocks external/protocol-relative and
backslash-based redirects while preserving normal local paths and query strings.
