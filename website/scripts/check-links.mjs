import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

const output = resolve('dist');
const basePath = '/mlx-local-lab/';

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(path) : [path];
  });
}

function destinationFor(pathname) {
  const sitePath = pathname.startsWith(basePath) ? pathname.slice(basePath.length) : pathname.slice(1);
  const decoded = decodeURIComponent(sitePath);
  if (!decoded || decoded.endsWith('/')) return join(output, decoded, 'index.html');
  if (decoded.endsWith('.html')) return join(output, decoded);
  if (/\.[a-z0-9]+$/i.test(decoded)) return join(output, decoded);
  return join(output, decoded, 'index.html');
}

const failures = [];
const htmlFiles = walk(output).filter((file) => file.endsWith('.html'));

for (const file of htmlFiles) {
  const html = readFileSync(file, 'utf8');
  for (const match of html.matchAll(/href=["']([^"']+)["']/g)) {
    const href = match[1];
    if (/^(https?:|mailto:|tel:|data:)/.test(href)) continue;

    const sourcePath = `/${relative(output, file).replace(/index\.html$/, '')}`;
    const resolved = new URL(href, `https://local.invalid${basePath}${sourcePath.replace(/^\//, '')}`);
    if (!resolved.pathname.startsWith(basePath)) {
      failures.push(`${relative(output, file)}: ${href} escapes ${basePath}`);
      continue;
    }

    const destination = destinationFor(resolved.pathname);
    if (!existsSync(destination)) {
      failures.push(`${relative(output, file)}: ${href} -> missing ${relative(output, destination)}`);
      continue;
    }

    if (resolved.hash && destination.endsWith('.html')) {
      const targetHtml = readFileSync(destination, 'utf8');
      const id = resolved.hash.slice(1);
      if (!targetHtml.includes(`id="${id}"`) && !targetHtml.includes(`id='${id}'`)) {
        failures.push(`${relative(output, file)}: ${href} -> missing anchor ${id}`);
      }
    }
  }
}

if (failures.length > 0) {
  console.error(`Found ${failures.length} broken internal link(s):\n${failures.join('\n')}`);
  process.exit(1);
}

console.log(`Checked ${htmlFiles.length} HTML files; all internal links resolve.`);
