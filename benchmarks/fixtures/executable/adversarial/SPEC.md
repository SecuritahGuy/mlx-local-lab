`profile(user_id)` returns a profile for a known user. Unknown IDs must raise
`KeyError`; callers use that signal to return an HTTP 404 response.
