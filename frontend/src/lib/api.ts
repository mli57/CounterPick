import type { Champion, PredictResult, TiltResult } from "@/types"

// All requests go to the FastAPI backend
const BASE = "http://localhost:8000"

// Fetches the full champion list for the dropdowns.
export async function fetchChampions(): Promise<Champion[]> {
	const response = await fetch(`${BASE}/champions`)
	if (!response.ok) {
		throw new Error("Failed to fetch champions")
	}
	return response.json()
}

// Sends the selected champion, opponent, and role to the model and returns a prediction.
// On failure, reads the detail field from FastAPI's error response for the UI to show unique messages
export async function fetchPredict(champion: string, opponent: string, role: string): Promise<PredictResult> {
	const response = await fetch(`${BASE}/predict`, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({champion, opponent, role}),
	})

	if (!response.ok) {
		const body = await response.json().catch(() => ({}))
		throw new Error(body.detail ?? "Prediction failed")
	}
	return response.json()
}

export async function fetchTilt(riotId: string): Promise<TiltResult> {
	const [gameName, tagLine] = riotId.split("#")
    	if (!gameName || !tagLine) throw new Error("Enter your Riot ID as GameName#Tag")
	const response = await fetch(`${BASE}/tilt/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`)
	
	if (!response.ok) {
		const body = await response.json().catch(() => ({}))
		throw new Error(body.detail ?? "Tilt lookup failed")
	}
	return response.json()
}
