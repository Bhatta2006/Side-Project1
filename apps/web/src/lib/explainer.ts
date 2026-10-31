export interface VisualArtifact {
  id: string;
  title: string;
  request: string;
  transcript: string;
  level: 'simple' | 'standard' | 'deep';
  language: string;
  mode?: 'sketch' | '3d';
  accuracy: string;
  created_at: number;
  frame_url: string;
  qa: { step_count: number; checks: string[]; ai_review?: 'passed' | 'flagged' | 'unavailable'; review_notes?: string };
}

export interface VisualState { count: number; current: number; description: string; height: number }
