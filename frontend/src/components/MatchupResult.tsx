import type { PredictResult } from "@/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

// Displays the result of POST /predict.
interface Props {
	result: PredictResult
	champion: string
	opponent: string
}

export function MatchupResult({ result, champion, opponent }: Props) {
	const { win_probability, warnings, champion_phase, opponent_phase } = result
	const pct = Math.round(win_probability * 100)
	const winning = win_probability >= 0.5  // determines bar/text color(green = high, red = low)

	return (
		<Card className="w-full">
		<CardHeader>
			<CardTitle>
			{champion} vs {opponent}
			</CardTitle>
		</CardHeader>
		<CardContent className="flex flex-col gap-4">

			{/* Win probability bar: green if >= 50%, red if below */}
			<div className="flex flex-col gap-2">
			<div className="flex items-center justify-between">
				<span className="text-muted-foreground">Lane Win Probability</span>
				<span className={cn("font-semibold text-lg", winning ? "text-green-500" : "text-red-500")}>
				{pct}%
				</span>
			</div>
			{/* The inner div's width is set inline so it can be any percentage value */}
			<div className="h-3 w-full rounded-full bg-muted overflow-hidden">
				<div
				className={cn("h-full rounded-full transition-all", winning ? "bg-green-500" : "bg-red-500")}
				style={{ width: `${pct}%` }}
				/>
			</div>
			</div>

			{/* Phase breakdown: one row per champion */}
			<div className="grid grid-cols-2 gap-3">
				<div className="rounded-lg border border-border bg-muted/40 px-3 py-2 flex flex-col gap-0.5">
					<span className="text-xs text-muted-foreground">{champion}</span>
					<span className="text-sm font-medium">{champion_phase}</span>
				</div>
				<div className="rounded-lg border border-border bg-muted/40 px-3 py-2 flex flex-col gap-0.5">
					<span className="text-xs text-muted-foreground">{opponent}</span>
					<span className="text-sm font-medium">{opponent_phase}</span>
				</div>
			</div>

			{/* Warnings from the backend: off-role picks, fallback stats used, etc. */}
			{warnings.length > 0 && (
			<div className="flex flex-col gap-1">
				{warnings.map((w, i) => (
				<div key={i} className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-600 dark:text-yellow-400">
					{w}
				</div>
				))}
			</div>
			)}

		</CardContent>
		</Card>
	)
}
