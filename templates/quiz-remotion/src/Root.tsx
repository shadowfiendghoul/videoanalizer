import React from "react";
import { Composition } from "remotion";
import { QuizChallengeComp } from "./QuizChallenge";
import { RemotionRenderProps } from "./types";
import "./style.css";

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
  sfx_paths: {
    timer_tick: "",
    reveal_ding: "",
    level_up: "",
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
    </>
  );
};
