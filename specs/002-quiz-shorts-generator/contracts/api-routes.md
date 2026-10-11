# API Contracts: Quiz Shorts Generator (FastAPI)

**Feature**: `002-quiz-shorts-generator`  
**Protocol**: REST / JSON over HTTP  
**Base URL**: `/api/v1/quiz`

---

## 1. POST `/api/v1/quiz/generate`

Triggers an asynchronous background job to generate a complete 9-question quiz video.

### Request Body (`QuizGenerateRequest`)
```json
{
  "topic": "Мировая география",
  "language": "ru",
  "background_video": null,
  "voice": "ru-RU-DmitryNeural"
}
```

### Response (`202 Accepted`)
```json
{
  "job_id": "qz_8f9a2b1c4e",
  "status": "pending",
  "topic": "Мировая география",
  "created_at": "2026-10-10T21:00:00Z",
  "status_url": "/api/v1/quiz/jobs/qz_8f9a2b1c4e"
}
```

---

## 2. GET `/api/v1/quiz/jobs/{job_id}`

Polls the execution status and progress of a quiz rendering job.

### Response (`200 OK`)
```json
{
  "job_id": "qz_8f9a2b1c4e",
  "status": "rendering_video",
  "progress_percent": 65,
  "stage": "remotion_rendering",
  "challenge_summary": {
    "topic": "Мировая география",
    "total_questions": 9,
    "duration_seconds": 58.4
  },
  "video_path": null,
  "error_message": null
}
```

### Terminal Success Response (`200 OK`)
```json
{
  "job_id": "qz_8f9a2b1c4e",
  "status": "completed",
  "progress_percent": 100,
  "stage": "finished",
  "challenge_summary": {
    "topic": "Мировая география",
    "total_questions": 9,
    "duration_seconds": 58.4
  },
  "video_path": "outputs/quiz_world_geography_qz_8f9a2b1c4e.mp4",
  "download_url": "/api/v1/quiz/jobs/qz_8f9a2b1c4e/download",
  "error_message": null
}
```

---

## 3. GET `/api/v1/quiz/jobs/{job_id}/download`

Downloads the final rendered 1080x1920 60fps MP4 file.

### Response
- Content-Type: `video/mp4`
- Content-Disposition: `attachment; filename="quiz_world_geography.mp4"`
