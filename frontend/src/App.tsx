import { useState } from "react";

type PredictResult = {
    win_probability: number;
    warnings: string[];
}

export default function App() {
    const [champion, setChampion] = useState("");
    const [opponent, setOpponent] = useState("");
    const [role, setRole] = useState("");
    const [result, setResult] = useState<PredictResult | null>(null);

    async function fetchChampionData(){
        const response = await fetch("http://localhost:8000/predict", { 
            method: "POST",
            headers: { "Content-Type": "application/json" }, //send champion, opponent, role as JSON
            body: JSON.stringify({ champion, opponent, role})
        });
        const data = await response.json();
        setResult(data);
    }
    return(
        <div>
            CounterPick UI
            <input placeholder="Enter your champion" value={champion} onChange={(e) => setChampion(e.target.value)}/>
            <input placeholder="Enter opponent champion" value={opponent} onChange={(e) => setOpponent(e.target.value)}/>
            <input placeholder="Enter role" value={role} onChange={(e) => setRole(e.target.value)}/>
            <button className="bg-blue-500 text-white px-4 py-2 rounded" onClick={fetchChampionData}>fetch champion data</button>
            
            {result && <p>{result.win_probability}</p>}
        </div>
    );
}