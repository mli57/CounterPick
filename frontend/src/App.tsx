import { useState, useEffect } from "react"
import { ChampionCombobox } from "@/components/ChampionCombobox"
import { RoleSelector } from "@/components/RoleSelector"
import { MatchupResult } from "@/components/MatchupResult"
import { TiltLookup } from "@/components/TiltLookup"
import { Button } from "@/components/ui/button"
import { fetchChampions, fetchPredict } from "@/lib/api"
import type { Champion, PredictResult } from "@/types"

export default function App() {
    // champion list loaded once on mount from GET /champions
    const [champions, setChampions] = useState<Champion[]>([])

    // user selections
    const [champion, setChampion] = useState("")
    const [opponent, setOpponent] = useState("")
    const [role, setRole] = useState("")

    // prediction result, null until a successful POST /predict
    const [result, setResult] = useState<PredictResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // load champion list when the page first opens
    useEffect(() => {
        fetchChampions().then(setChampions).catch(() => {})
    }, [])


    async function handleAnalyze() {
        if (!champion || !opponent || !role) {
            return
        }
        setLoading(true)
        setError(null)

        try {
        const data = await fetchPredict(champion, opponent, role)
        setResult(data)
        } catch (error) {
            // show the error message from the backend if available
            setError(error instanceof Error ? error.message : "Prediction failed. Is the backend running?")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-background">
            <div className="mx-auto max-w-5xl px-6 py-10 flex flex-col gap-6">

                <div className="flex flex-col gap-2">
                    <h1 className="text-4xl font-semibold">CounterPick</h1>
                    <p className="text-base text-muted-foreground">Champion matchup analyzer</p>
                </div>

                {/* dark mode button */}
                <Button
                variant="outline"
                size="lg"
                className="w-40 mt-4"
                onClick={() => document.documentElement.classList.toggle("dark")}
                >
                    Toggle dark mode
                </Button>

                {/* two champion pickers */}
                <div className="flex flex-col gap-6">
                    <div className="grid grid-cols-2 gap-4">
                        <ChampionCombobox
                        label="Your champion"
                        champions={champions}
                        value={champion}
                        onChange={setChampion}
                        />
                        <ChampionCombobox
                        label="Opponent"
                        champions={champions}
                        value={opponent}
                        onChange={setOpponent}
                        />
                    </div>

                    {/* role select */}
                    <div className="flex flex-col gap-2">
                        <span className="text-base font-medium text-muted-foreground">Role</span>
                        <RoleSelector value={role} onChange={setRole} />
                    </div>

                    {error && <p className="text-base text-destructive">{error}</p>}


                    {/* analysis button is disabled until all three fields are filled */}
                    <Button
                        onClick={handleAnalyze}
                        disabled={!champion || !opponent || !role || loading}
                        size="lg"
                        className="w-full"
                    >
                        {loading ? "Analyzing…" : "Analyze Matchup"}
                    </Button>
                </div>

                {/* only shown after a successful prediction */}
                {result && (
                    <MatchupResult result={result} champion={champion} opponent={opponent} />
                )}

                <div className="flex flex-col gap-6">
                    <h2 className="text-xl font-semibold">Tilt Check</h2>
                    <p className="text-sm text-muted-foreground">Win rate over last 10 ranked games</p>
                    <TiltLookup />
                </div>
            </div>
        </div>
    )
}