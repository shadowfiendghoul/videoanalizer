import React from "react";
import { Composition } from "remotion";
import { QuizChallengeComp } from "./QuizChallenge";
import { VisualImageQuizComp } from "./VisualImageQuiz";
import { WidescreenGamingQuizComp } from "./WidescreenGamingQuiz";
import {
  RemotionRenderProps,
  VisualQuizRenderProps,
  WidescreenQuizRenderProps,
} from "./types";
import { loadFont as loadMontserrat } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadInterTight } from "@remotion/google-fonts/InterTight";
import "./style.css";

loadMontserrat("normal", { weights: ["700", "800", "900"] });
loadInterTight("normal", { weights: ["700", "800", "900"] });

const defaultProps: RemotionRenderProps = {
  challenge: {
    topic: "Мировая география",
    language: "ru",
    total_questions: 9,
    tiers: [
      {
        tier_level: "easy",
        tier_index: 1,
        theme_color: "#22C55E",
        questions: [
          {
            question_number: 1,
            difficulty: "easy",
            tier_index: 1,
            question_text: "What is the capital city of France?",
            correct_answer: "Paris",
            fun_fact: "Paris is known as the City of Light.",
            image_query: null,
            local_image_path: null,
          },
          {
            question_number: 2,
            difficulty: "easy",
            tier_index: 1,
            question_text: "Which continent is Egypt located on?",
            correct_answer: "Africa",
            fun_fact: "The Nile River runs through Egypt.",
            image_query: null,
            local_image_path: null,
          },
          {
            question_number: 3,
            difficulty: "easy",
            tier_index: 1,
            question_text: "What is the largest ocean on Earth?",
            correct_answer: "Pacific Ocean",
            fun_fact: "It covers over 30 percent of the Earth's surface.",
            image_query: null,
            local_image_path: null,
          },
        ],
      },
      {
        tier_level: "medium",
        tier_index: 2,
        theme_color: "#F59E0B",
        questions: [
          {
            question_number: 4,
            difficulty: "medium",
            tier_index: 2,
            question_text: "What is the capital of Australia?",
            correct_answer: "Canberra",
            fun_fact: "Canberra was selected as a compromise between Sydney and Melbourne.",
            image_query: null,
            local_image_path: null,
          },
          {
            question_number: 5,
            difficulty: "medium",
            tier_index: 2,
            question_text: "Which country has the most natural lakes in the world?",
            correct_answer: "Canada",
            fun_fact: "Canada has more than 50 percent of the world's natural lakes.",
            image_query: null,
            local_image_path: null,
          },
          {
            question_number: 6,
            difficulty: "medium",
            tier_index: 2,
            question_text: "What strait separates Spain and Morocco?",
            correct_answer: "Strait of Gibraltar",
            fun_fact: "It is only 14 kilometers wide at its narrowest point.",
            image_query: null,
            local_image_path: null,
          },
        ],
      },
      {
        tier_level: "hard",
        tier_index: 3,
        theme_color: "#EF4444",
        questions: [
          {
            question_number: 7,
            difficulty: "hard",
            tier_index: 3,
            question_text: "What is the highest mountain peak in North America?",
            correct_answer: "Denali",
            fun_fact: "Denali reaches an elevation of 6,190 meters.",
            image_query: null,
            local_image_path: null,
          },
          {
            question_number: 8,
            difficulty: "hard",
            tier_index: 3,
            question_text: "Which desert is the driest non-polar desert on Earth?",
            correct_answer: "Atacama Desert",
            fun_fact: "Some weather stations in Atacama have never received rain.",
            image_query: null,
            local_image_path: null,
          },
          {
            question_number: 9,
            difficulty: "hard",
            tier_index: 3,
            question_text: "What is the only sea without any land boundaries?",
            correct_answer: "Sargasso Sea",
            fun_fact: "It is bounded only by four ocean currents in the Atlantic.",
            image_query: null,
            local_image_path: null,
          },
        ],
      },
    ],
  },
  cue_sheet: {
    total_duration_ms: 54000,
    total_duration_frames: 3240,
    cues: [1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => {
      const start = (num - 1) * 360;
      return {
        question_number: num,
        start_frame: start,
        question_audio_file: "",
        question_duration_ms: 2000,
        question_words: [{ word: "Question", start_ms: 0, end_ms: 500 }],
        think_start_frame: start + 120,
        think_duration_ms: 3000,
        reveal_frame: start + 300,
        answer_audio_file: "",
        answer_duration_ms: 1000,
        answer_words: [{ word: "Answer", start_ms: 0, end_ms: 500 }],
        end_frame: start + 360,
      };
    }),
  },
  background_video_path: "bg.mp4",
  background_music_path: null,
  background_music_volume: 0.18,
  banner_image_path: null,
  sfx_paths: {
    timer_tick: "assets/sfx/timer_tick.wav",
    reveal_ding: "assets/sfx/reveal_ding.wav",
    level_up: "assets/sfx/level_up.wav",
    heartbeat_panic: "assets/sfx/heartbeat_panic.wav",
    streak_fire: "assets/sfx/streak_fire.wav",
    rank_levelup: "assets/sfx/rank_levelup.wav",
    comment_buzzer: "assets/sfx/comment_buzzer.wav",
  },
  retention: {
    enabled: true,
    rank_bar_enabled: true,
    rank_tiers: [
      { min_question: 1, max_question: 3, rank_title: "NPC", rank_color: "#64748B", rank_icon: "🤖", iq_label: "IQ < 90" },
      { min_question: 4, max_question: 6, rank_title: "Нормис", rank_color: "#22C55E", rank_icon: "🥉", iq_label: "IQ 90-110" },
      { min_question: 7, max_question: 8, rank_title: "Эрудит", rank_color: "#A855F7", rank_icon: "🥈", iq_label: "IQ 111-129" },
      { min_question: 9, max_question: 9, rank_title: "1% Гениев", rank_color: "#F59E0B", rank_icon: "👑", iq_label: "IQ 130+" },
    ],
    stress_timer_enabled: true,
    stress_tiers: [
      { tier_level: "easy", think_duration_sec: 3.0, theme_color: "#00A3FF", sfx_file: "assets/sfx/timer_tick.wav", panic_vignette: false },
      { tier_level: "medium", think_duration_sec: 2.5, theme_color: "#F59E0B", sfx_file: "assets/sfx/timer_tick.wav", panic_vignette: false },
      { tier_level: "hard", think_duration_sec: 1.8, theme_color: "#EF4444", sfx_file: "assets/sfx/heartbeat_panic.wav", panic_vignette: true },
    ],
    streak_fire: {
      enabled: true,
      fire_color_normal: "#FF5500",
      fire_color_ultra: "#38BDF8",
      ultra_threshold: 7,
      sfx_pitch_step: 0.05,
    },
    comment_trap: {
      enabled: true,
      trap_question_number: 8,
      outro_challenge_text: "Если набрал 8+ — ты соврал. Пиши честный счет в комменты! 👇",
      duration_frames: 90,
    },
    seamless_loop: true,
    anti_cheat_callout: true,
  },
  fps: 60,
  width: 1080,
  height: 1920,
};

export const Root: React.FC = () => {
  return (
    <>
      <Composition<any, RemotionRenderProps>
        id="QuizChallenge"
        component={QuizChallengeComp}
        durationInFrames={3240}
        fps={60}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
        calculateMetadata={({ props }) => {
          return {
            durationInFrames: props.cue_sheet?.total_duration_frames || 3240,
            fps: props.fps || 60,
            width: props.width || 1080,
            height: props.height || 1920,
          };
        }}
      />

      <Composition<any, VisualQuizRenderProps>
        id="VisualImageQuiz"
        component={VisualImageQuizComp}
        durationInFrames={3000}
        fps={60}
        width={1080}
        height={1920}
        defaultProps={{
          dataset: {
            mode: "visual_image_quiz",
            theme: "Пример викторины",
            hook_tts: "Угадай все эти предметы!",
            rapid_flip_duration_ms: 120,
            timer_duration_sec: 2.0,
            items: [],
          },
          fps: 60,
          width: 1080,
          height: 1920,
          total_duration_frames: 3000,
          hook_end_frame: 180,
          timing_slots: [],
          subtitles: [],
          audio_mix_path: "",
        }}
        calculateMetadata={({ props }) => {
          return {
            durationInFrames: props.total_duration_frames || 3000,
            fps: props.fps || 60,
            width: props.width || 1080,
            height: props.height || 1920,
          };
        }}
      />

      <Composition<any, WidescreenQuizRenderProps>
        id="WidescreenGamingQuiz"
        component={WidescreenGamingQuizComp}
        durationInFrames={32400}
        fps={60}
        width={1920}
        height={1080}
        defaultProps={{
          dataset: {
            mode: "widescreen_gaming_quiz",
            title: "50 GAMING QUESTIONS CHALLENGE",
            language: "ru",
            guessing_duration_sec: 6.0,
            reveal_hold_duration_sec: 3.0,
            intro: {
              hook_tts: "50 вопросов по играм. 5 уникальных раундов. Сможешь ли ты дойти до ранга God Tier?",
              duration_sec: 8.0,
              challenge_title: "50 GAMING QUESTIONS CHALLENGE",
            },
            outro: {
              duration_sec: 15.0,
              outro_tts: "Напиши свой результат в комментариях и подписывайся на канал!",
              call_to_action: "COMMENT YOUR SCORE & SUBSCRIBE!",
              score_tiers: [
                { tier_name: "Noob", min_score: 0, max_score: 20, badge_color: "#94A3B8" },
                { tier_name: "Gamer", min_score: 21, max_score: 35, badge_color: "#3B82F6" },
                { tier_name: "Pro", min_score: 36, max_score: 45, badge_color: "#8B5CF6" },
                { tier_name: "God Tier", min_score: 46, max_score: 50, badge_color: "#F59E0B" },
              ],
            },
            rounds: [],
          },
          fps: 60,
          width: 1920,
          height: 1080,
          total_duration_frames: 32400,
          timing_slots: [],
          sfx_ticking_path: "",
          sfx_chime_path: "",
          sfx_stinger_path: "",
        }}
        calculateMetadata={({ props }) => {
          return {
            durationInFrames: props.total_duration_frames || 32400,
            fps: props.fps || 60,
            width: props.width || 1920,
            height: props.height || 1080,
          };
        }}
      />
    </>
  );
};

