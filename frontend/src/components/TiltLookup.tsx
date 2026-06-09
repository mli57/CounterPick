import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { fetchTilt } from "@/lib/api"
import type { TiltResult } from "@/types"

export function TiltLookup() {
    const [riotId, setRiotId] = useState("")
    const [result, setResult] = useState<TiltResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    async function handleLookup() {
        setLoading(true)
        setError(null)
        try { // stores api call result if successful
            setResult(await fetchTilt(riotId))
        } catch (e) { // throw error for fails
            setError(e instanceof Error ? e.message : "Lookup failed")
        } finally { // runs on both success and fail
            setLoading(false)
        }
    }

    // calculates percentage, assign color based on streak
    const percent = result ? Math.round(result.win_rate * 100) : 0
    const color = result?.status === "hot streak" ? "text-green-500"
        : (result?.status === "cold streak" ? "text-red-500" : "text-muted-foreground")

    return (
        <div className="flex flex-col gap-4">
            {/* before user input */}
            <div className="flex gap-2">
                <Input
                    placeholder="GameName#TAG"
                    value={riotId}
                    onChange={e => setRiotId(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && riotId && handleLookup()}
                    className="max-w-64"
                />
                <Button onClick={handleLookup} disabled={!riotId || loading} variant="outline">
                    {loading ? "Looking up..." : "Check tilt"}
                </Button>
            </div>

            {/* error */}
            {error && <p className="text-sm text-destructive">{error}</p>}

            {/* successfully found player */}
            {result && (
                <Card className="w-full max-w-sm">
                    <CardHeader>
                        <CardTitle className="text-base">{riotId}</CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-1">
                        <span className={`text-2xl font-semibold ${color}`}>{percent}% WR</span>
                        <span className="text-sm text-muted-foreground">
                            {result.wins}W {result.total - result.wins}L in last {result.total} ranked games
                        </span>
                        <span className={`text-sm font-medium ${color}`}>{result.status}</span>
                    </CardContent>
                </Card>
            )}
        </div>
    )
}