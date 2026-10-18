export type DifficultyTier = "easy" | "medium" | "hard";

export interface QuizItem {
  question_number: number;
  difficulty: DifficultyTier;
  tier_index: number;
  question_text: string;
  correct_answer: string;
  fun_fact: string;
  image_query: string | null;
  image_url?: string | null;
  local_image_path: string | null;
  decoy_answer?: string | null;
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
  intro_hook_text?: string | null;
  intro_hook_audio_file?: string | null;
  intro_hook_duration_ms?: number;
  intro_hook_words?: WordCue[];
  intro_hook_duration_frames?: number;
}

export interface SfxPaths {
  timer_tick: string;
  reveal_ding: string;
  level_up: string;
  heartbeat_panic?: string | null;
  streak_fire?: string | null;
  rank_levelup?: string | null;
  comment_buzzer?: string | null;
}

export interface RankTierConfig {
  min_question: number;
  max_question: number;
  rank_title: string;
  rank_color: string;
  rank_icon: string;
  iq_label: string;
}

export interface StressTimerTier {
  tier_level: DifficultyTier;
  think_duration_sec: number;
  theme_color: string;
  sfx_file: string;
  panic_vignette: boolean;
}

export interface ComboStreakConfig {
  enabled: boolean;
  fire_color_normal: string;
  fire_color_ultra: string;
  ultra_threshold: number;
  sfx_pitch_step: number;
}

export interface CommentTrapConfig {
  enabled: boolean;
  trap_question_number: number;
  outro_challenge_text: string;
  duration_frames: number;
}

export interface QuizRetentionConfig {
  enabled: boolean;
  rank_bar_enabled: boolean;
  rank_tiers: RankTierConfig[];
  stress_timer_enabled: boolean;
  stress_tiers: StressTimerTier[];
  streak_fire: ComboStreakConfig;
  comment_trap: CommentTrapConfig;
  seamless_loop: boolean;
  anti_cheat_callout: boolean;
}

export interface RemotionRenderProps extends Record<string, unknown> {
  challenge: QuizChallenge;
  cue_sheet: AudioCueSheet;
  background_video_path: string;
  sfx_paths: SfxPaths;
  retention?: QuizRetentionConfig;
  fps: number;
  width: number;
  height: number;
  banner_video_path?: string | null;
  banner_start_frame?: number | null;
  banner_duration_frames?: number | null;
  banner_width?: number | null;
  banner_height?: number | null;
  background_music_path?: string | null;
  background_music_volume?: number | null;
}

// ==========================================
// 007-visual-image-quiz Type Contracts
// ==========================================

export type VisualDifficulty = "easy" | "medium" | "hard" | "master";

export interface VisualQuizItem {
  id: number;
  difficulty: VisualDifficulty;
  answer_text: string;
  image_query: string;
  image_url?: string | null;
  image_path?: string | null;
  is_approved: boolean;
  prompt_tts: string;
  answer_tts: string;
}

export type VisualQuizInterstitialType = "comment_bait" | "share_bait";

export interface VisualQuizInterstitial {
  after_question: number;
  type: VisualQuizInterstitialType;
  tts_text: string;
  duration_sec: number;
}

export interface VisualQuizDataset {
  mode: "visual_image_quiz";
  theme: string;
  language?: string;
  hook_tts: string;
  rapid_flip_duration_ms: number;
  timer_duration_sec: number;
  items: VisualQuizItem[];
  interstitials?: VisualQuizInterstitial[];
}

export interface VisualQuizTimingSlot {
  question_id: number;
  start_frame: number;
  prompt_audio_start_frame: number;
  timer_start_frame: number;
  timer_duration_frames: number;
  answer_audio_start_frame: number;
  reveal_frame: number;
  end_frame: number;
}

export interface VisualQuizWordTiming {
  word: string;
  start_frame: number;
  end_frame: number;
  start_ms?: number;
  end_ms?: number;
}

export interface VisualQuizRenderProps extends Record<string, unknown> {
  dataset: VisualQuizDataset;
  fps: number;
  width: number;
  height: number;
  total_duration_frames: number;
  hook_end_frame: number;
  timing_slots: VisualQuizTimingSlot[];
  subtitles: VisualQuizWordTiming[];
  audio_mix_path: string;
  background_video_path?: string | null;
  background_music_path?: string | null;
  background_music_volume?: number;
  banner_video_path?: string | null;
  banner_start_frame?: number | null;
  banner_duration_frames?: number | null;
  banner_height?: number | null;
}

