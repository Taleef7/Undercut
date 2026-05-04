import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { ArrowLeft } from "lucide-react";

export default function Disclaimer() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-background text-foreground px-6 py-8 flex flex-col">
      <div className="max-w-2xl mx-auto text-left flex-1">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-foreground mb-4">
            Disclaimer
          </h1>
          <div className="bg-card border border-border rounded-xl p-6">
            <p className="text-sm text-muted-foreground leading-relaxed">
              This is an unofficial fan project created for educational and portfolio purposes. 
              It is not affiliated with Formula 1, the FIA, any F1 team, driver, or data provider. 
              All trademarks belong to their respective owners. Data is used under the terms of 
              the respective source licenses and is intended for non-commercial personal use only.
            </p>
          </div>
        </div>

        <Button variant="outline" onClick={() => navigate("/")}>
          <ArrowLeft size={16} className="mr-2" />
          Back to Home
        </Button>
      </div>
    </div>
  );
}
