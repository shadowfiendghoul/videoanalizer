export type DifficultyTier = "easy" | "medium" | "hard";

export interface QuizItem {
  question_number: number;
  difficulty: DifficultyTier;
  tier_index: number;
  question_text: string;
  correct_answer: string;
  fun_fact: string;
  image_query: string | null;
  local_image_path: string | null;
}

export interface QuizTier {
  tier_level: DifficultyTier;
  tier_index: number;
  theme_color: string;
  questions: QuizItem[];
}

export interface QuizChallenge {
  topic: string;
  language: "ru" | "en";
  total_questions: number;
  tiers: QuizTier[];
}

export interface WordCue {
  word: string;
  start_ms: number;
  end_ms: number;
}

export interface QuestionAudioCue {
  question_number: number;
  start_frame: number;
  question_audio_file: string;
  question_duration_ms: number;
  question_words: WordCue[];
  think_start_frame: number;
  think_duration_ms: number;
  reveal_frame: number;
  answer_audio_file: string;
  answer_duration_ms: number;
  answer_words: WordCue[];
  end_frame: number;
}

export interface AudioCueSheet {
  total_duration_ms: number;
  total_duration_frames: number;
  cues: QuestionAudioCue[];
}

export interface SfxPaths {
  timer_tick: string;
  reveal_ding: string;
  level_up: string;
}

export interface RemotionRenderProps extends Record<string, unknown> {
  challenge: QuizChallenge;
  cue_sheet: AudioCueSheet;
  background_video_path: string;
  sfx_paths: SfxPaths;
  fps: number;
  width: number;
  height: number;
  banner_video_path?: string | null;
  banner_start_frame?: number | null;
  banner_duration_frames?: number | null;
}
