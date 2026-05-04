import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-card py-4 px-6 mt-auto">
      <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
        <div>
          Undercut — F1 Strategy Simulator
        </div>
        <div className="flex items-center gap-4">
          <a
            href="https://github.com/Taleef7/Undercut"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-papaya transition-colors flex items-center gap-1"
          >
            <ExternalLink size={14} />
            GitHub
          </a>
          <Link to="/methodology" className="hover:text-foreground transition-colors">
            Methodology
          </Link>
          <Link to="/disclaimer" className="hover:text-foreground transition-colors">
            Disclaimer
          </Link>
        </div>
      </div>
    </footer>
  );
}
