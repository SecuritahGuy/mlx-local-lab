export interface PublishedDocument {
  id: string;
  slug: string;
  title: string;
  description: string;
  section: 'results' | 'guides' | 'methodology';
  date?: string;
}

export const publishedDocuments: PublishedDocument[] = [
  {
    id: 'results/mlx-candidates-2026-08-24',
    slug: 'results/mlx-candidates-2026-08-24',
    title: 'MLX candidate evaluation',
    description: 'Four August 2026 checkpoints tested for runtime fit, memory behavior, and output quality.',
    section: 'results',
    date: '2026-08-24',
  },
  {
    id: 'results/gptoss-evaluation-2026-08-19',
    slug: 'results/gptoss-evaluation-2026-08-19',
    title: 'GPT-OSS evaluation snapshot',
    description: 'Capability, reliability, and prompt-profile findings for GPT-OSS 20B on the reference host.',
    section: 'results',
    date: '2026-08-19',
  },
  {
    id: 'results/reliability-trials',
    slug: 'results/reliability-trials',
    title: 'Repeated-trial reliability',
    description: 'Coverage-aware distributions for latency, throughput, schema validity, and routing recommendations.',
    section: 'results',
  },
  {
    id: 'gemma-template-investigation',
    slug: 'results/gemma-template-investigation',
    title: 'Gemma template investigation',
    description: 'An investigation of channel markers, strict requests, and structured-output behavior.',
    section: 'results',
  },
  {
    id: 'gptoss-readiness',
    slug: 'results/gptoss-readiness',
    title: 'GPT-OSS benchmark readiness',
    description: 'The capability skip matrix, request profile, and completed-run status.',
    section: 'results',
  },
  {
    id: 'practical-benchmarks',
    slug: 'benchmarks/methodology',
    title: 'Practical benchmark methodology',
    description: 'How retrieval, infrastructure, model inference, scoring, and limitations are kept separate.',
    section: 'methodology',
  },
  {
    id: 'codex-local-provider',
    slug: 'guides/codex',
    title: 'Codex local-provider experiment',
    description: 'Using this lab as an OpenAI-compatible local provider for Codex experiments.',
    section: 'guides',
  },
];
