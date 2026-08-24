import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { parse } from 'yaml';

export interface Model {
  name: string;
  model_id: string;
  runtime: string;
  model_type: string;
  multimodal: boolean;
  reasoning: boolean;
  context_limit: number;
  estimated_download_gb: number;
  responses_api: boolean;
  request_profile?: string;
  notes: string;
}

interface TrialSummary {
  coverage: {
    observed_trials: number;
    expected_trials: number;
    observed_cases: number;
    expected_cases: number;
    complete_cases: number;
  };
  ttft_seconds: { mean: number; median: number; stdev: number; min: number; max: number };
  tokens_per_second: { mean: number; median: number; stdev: number; min: number; max: number };
  output_tokens: { mean: number; median: number; stdev: number; min: number; max: number };
  schema_success_rate: number | null;
  schema_observations: number;
  peak_system_used_gb: number;
  peak_swap_used_gb: number;
}

interface RoutingResult {
  qwen: number | null;
  gemma: number | null;
  'gptoss-final': number | null;
  recommendation: string;
  basis?: string;
}

const modelDocument = parse(
  readFileSync(resolve(process.cwd(), '../config/models.yaml'), 'utf8'),
) as { models: Record<string, Model> };

export const models = modelDocument.models;

export const reliability = JSON.parse(
  readFileSync(resolve(process.cwd(), '../docs/results/reliability-trials.json'), 'utf8'),
) as {
  trials: Record<string, TrialSummary>;
  routing: Record<string, RoutingResult>;
};

export const modelLabels: Record<string, string> = {
  qwen: 'Qwen 3.5 9B',
  gemma: 'Gemma 4 12B',
  'gptoss-final': 'GPT-OSS 20B',
};

export function percent(value: number | null): string {
  return value === null ? 'N/A' : `${(value * 100).toFixed(1)}%`;
}
