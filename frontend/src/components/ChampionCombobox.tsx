import { useState } from "react"
import type { Champion } from "@/types"
import {
	Combobox,
	ComboboxContent,
	ComboboxEmpty,
	ComboboxInput,
	ComboboxItem,
	ComboboxList,
} from "@/components/ui/combobox"

// Searchable dropdown for picking a champion.
// Used twice in App.tsx, for both champs
// The champion list comes from GET /champions on the backend.
interface Props {
	label: string // displayed above the input, e.g. "Your champion"
	champions: Champion[]
	value: string // currently selected champion name
	onChange: (v: string) => void
}

export function ChampionCombobox({ label, champions, value, onChange }: Props) {
	const [query, setQuery] = useState("") // tracks what user is typing

	// the filtered array re renders only the matching champs
	let filtered
	if (query) {
		filtered = champions.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()))
	} else {
		filtered = champions
	}

	return (
		<div className="flex flex-col gap-1.5 w-full">
		<span className="text-sm font-medium text-muted-foreground">{label}</span>

		<Combobox
			value={value}
			onValueChange={(v) => onChange(v as string)}
			onInputValueChange={(q) => setQuery(q)} // when query changes, react re renders
		>
			<ComboboxInput
				placeholder={`Search ${label.toLowerCase()}...`}
				showClear={!!value}
				className="w-full"
			/>
			<ComboboxContent>
				<ComboboxList>
					{filtered.map((champ) => (
						<ComboboxItem key={champ.name} value={champ.name}>
							{champ.name}
						</ComboboxItem>
					))}
					
					<ComboboxEmpty>No champions found.</ComboboxEmpty>
				</ComboboxList>
			</ComboboxContent>
		</Combobox>
		</div>
	)
}
