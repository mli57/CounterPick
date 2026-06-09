// Shapes returned by the backend API.
// These must stay in sync with what FastAPI actually returns.

// returned by GET /champions
export type Champion = {
  name: string
  roles: string[]  // Riot's internal role names E.g "UTILITY", "TOP"
}

// returned by POST /predict
export type PredictResult = {
  win_probability: number  // 0.0 to 1.0
  warnings: string[]       // off-role or fallback notices from predict.py
  champion_phase: string   // e.g. "strong early", "peaks mid game", "strong late", "even scaling"
  opponent_phase: string
}

export type TiltResult = {
  wins: number
  total: number
  win_rate: number   // 0.0 to 1.0
  status: string     // hot streak, cold streak, neutral
}