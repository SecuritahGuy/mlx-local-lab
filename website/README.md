# Local MLX Lab website

The static Astro site published at `https://securitahguy.github.io/mlx-local-lab/`.

The site reads model configuration and reviewed result artifacts from the repository at build time.
Generated output is never committed.

```bash
npm ci
npm run dev -- --background
npm run verify
```

`npm run verify` performs Astro/TypeScript validation, creates the production site, and verifies
internal routes and anchors under the `/mlx-local-lab/` project base path.
