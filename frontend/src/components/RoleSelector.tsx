import { Button } from "@/components/ui/button"

// These are the display names sent to the backend.
// The backend maps them to Riot's internal role names (E.g "MID" = "MIDDLE").
const ROLES = ["Top", "Jng", "Mid", "ADC", "Sup"] as const

interface Props {
  value: string  // currently selected role
  onChange: (role: string) => void
}

export function RoleSelector({ value, onChange }: Props) {
  return (
    <div className="flex gap-1.5">
      {ROLES.map((role) => (
        // selected role gets solid "default" style, others get "outline"
        <Button
          key={role}
          variant={value === role ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(role)}
        >
          {role}
        </Button>
      ))}
    </div>
  )
}
