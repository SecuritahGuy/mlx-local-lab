// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { unified } from '@astrojs/markdown-remark';

const publishedMarkdownRoutes = new Map([
  ['results/gptoss-evaluation-2026-08-19.md', '/mlx-local-lab/results/gptoss-evaluation-2026-08-19/'],
]);

function rewritePublishedMarkdownLinks() {
  /** @param {{ type?: string, url?: string, children?: any[] }} tree */
  return (tree) => {
    /** @param {{ type?: string, url?: string, children?: any[] }} node */
    function walk(node) {
      if (node.type === 'link' && node.url) {
        const route = publishedMarkdownRoutes.get(node.url);
        if (route) node.url = route;
      }
      if (node.children) node.children.forEach(walk);
    }
    walk(tree);
  };
}

function normalizeGeneratedTables() {
  /** @param {any} tree */
  return (tree) => {
    /** @param {any} node @param {string | undefined} section */
    function walk(node, section) {
      const nextSection = node.tagName === 'thead' || node.tagName === 'tbody' ? node.tagName : section;
      if (node.tagName === 'th') {
        node.properties ??= {};
        node.properties.scope = nextSection === 'thead' ? 'col' : 'row';
      }
      const align = node.properties?.align;
      if (align) {
        node.properties.className = [...(node.properties.className ?? []), `align-${align}`];
        delete node.properties.align;
      }
      if (node.children) {
        for (const child of node.children) walk(child, nextSection);
      }
    }
    walk(tree, undefined);
  };
}

// https://astro.build/config
export default defineConfig({
  site: 'https://securitahguy.github.io',
  base: '/mlx-local-lab',
  trailingSlash: 'always',
  integrations: [sitemap()],
  markdown: {
    processor: unified({
      remarkPlugins: [rewritePublishedMarkdownLinks],
      rehypePlugins: [normalizeGeneratedTables],
    }),
  },
});
