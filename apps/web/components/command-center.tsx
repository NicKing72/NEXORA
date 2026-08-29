import {
  ArrowUpRight,
  Bell,
  ChevronRight,
  Clock,
  RefreshCcw,
  Satellite,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";

import { ui } from "@/lib/i18n";

const signals = [
  { ...ui.commandCenter.signals.items[0], icon: Satellite },
  { ...ui.commandCenter.signals.items[1], icon: Clock },
  { ...ui.commandCenter.signals.items[2], icon: Bell },
] as const;

export function CommandCenter() {
  return (
    <div className="workspace command-center">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">{ui.commandCenter.eyebrow}</span>
          <h1>{ui.commandCenter.title}</h1>
          <p>{ui.commandCenter.subtitle}</p>
        </div>
        <div className="header-actions">
          <span className="system-state"><span /> {ui.commandCenter.systemReady}</span>
          <button className="icon-button" type="button" aria-label={ui.commandCenter.refresh}>
            <RefreshCcw size={17} />
          </button>
          <button className="icon-button" type="button" aria-label={ui.commandCenter.notifications}>
            <Bell size={17} />
          </button>
        </div>
      </header>

      <section className="timeline-panel" aria-labelledby="demand-timeline-title">
        <div className="panel-heading">
          <div>
            <span className="section-index">{ui.commandCenter.timeline.index}</span>
            <h2 id="demand-timeline-title">{ui.commandCenter.timeline.title}</h2>
          </div>
          <div className="timeline-key" aria-label={ui.commandCenter.timeline.legend}>
            <span><i className="key-line key-line--solid" /> {ui.commandCenter.timeline.actual}</span>
            <span><i className="key-line key-line--dash" /> {ui.commandCenter.timeline.forecast}</span>
          </div>
        </div>

        <div className="timeline-stage">
          <div className="timeline-overlay">
            <span className="stage-kicker">{ui.commandCenter.timeline.reserved}</span>
            <strong>{ui.commandCenter.timeline.connect}</strong>
            <p>{ui.commandCenter.timeline.later}</p>
            <Link className="text-action" href="/data-studio">
              {ui.commandCenter.timeline.review} <ArrowUpRight size={15} />
            </Link>
          </div>
          <svg
            className="timeline-graphic"
            viewBox="0 0 1000 310"
            role="img"
            aria-label={ui.commandCenter.timeline.graphicLabel}
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="lineFade" x1="0" x2="1">
                <stop offset="0" stopColor="#738b88" stopOpacity="0.2" />
                <stop offset="0.65" stopColor="#8cc6bd" stopOpacity="0.75" />
                <stop offset="1" stopColor="#8cc6bd" stopOpacity="0.12" />
              </linearGradient>
            </defs>
            {[56, 112, 168, 224, 280].map((y) => (
              <line key={y} x1="0" x2="1000" y1={y} y2={y} className="chart-grid" />
            ))}
            {[125, 250, 375, 500, 625, 750, 875].map((x) => (
              <line key={x} x1={x} x2={x} y1="0" y2="310" className="chart-grid chart-grid--vertical" />
            ))}
            <path
              d="M0 238 C90 228 104 192 180 205 S300 242 370 196 S492 112 560 139 S650 209 724 171 S844 91 920 126 S971 154 1000 132"
              fill="none"
              stroke="url(#lineFade)"
              strokeWidth="2.2"
              vectorEffect="non-scaling-stroke"
            />
            <line x1="702" x2="702" y1="0" y2="310" className="today-line" />
          </svg>
          <div className="timeline-axis" aria-hidden="true">
            {ui.commandCenter.timeline.weeks.map((week) => <span key={week}>{week}</span>)}
          </div>
        </div>
      </section>

      <div className="intelligence-grid">
        <section className="intelligence-section forecast-health" aria-labelledby="forecast-health-title">
          <div className="section-heading-row">
            <div>
              <span className="section-index">{ui.commandCenter.health.index}</span>
              <h2 id="forecast-health-title">{ui.commandCenter.health.title}</h2>
            </div>
            <ShieldCheck size={19} aria-hidden="true" />
          </div>
          <div className="health-score">
            <span className="score-ring"><span>—</span></span>
            <div>
              <strong>{ui.commandCenter.health.baseline}</strong>
              <p>{ui.commandCenter.health.description}</p>
            </div>
          </div>
          <dl className="metric-list">
            {ui.commandCenter.health.metrics.map((metric) => (
              <div key={metric.label}>
                <dt>{metric.label}</dt>
                <dd className={`metric-value metric-value--${metric.tone}`}>{metric.value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="intelligence-section external-signals" aria-labelledby="external-signals-title">
          <div className="section-heading-row">
            <div>
              <span className="section-index">{ui.commandCenter.signals.index}</span>
              <h2 id="external-signals-title">{ui.commandCenter.signals.title}</h2>
            </div>
            <Satellite size={19} aria-hidden="true" />
          </div>
          <div className="signal-list">
            {signals.map(({ source, state, icon: Icon }) => (
              <div className="signal-row" key={source}>
                <span className="signal-icon"><Icon size={16} /></span>
                <span><strong>{source}</strong><small>{state}</small></span>
                <ChevronRight size={15} aria-hidden="true" />
              </div>
            ))}
          </div>
        </section>

        <section className="intelligence-section attention-zone" aria-labelledby="attention-title">
          <div className="section-heading-row">
            <div>
              <span className="section-index">{ui.commandCenter.attention.index}</span>
              <h2 id="attention-title">{ui.commandCenter.attention.title}</h2>
            </div>
            <TriangleAlert size={19} aria-hidden="true" />
          </div>
          <div className="attention-list">
            {ui.commandCenter.attention.items.map((item, index) => (
              <div className="attention-row" key={item.sku}>
                <span className="queue-number">0{index + 1}</span>
                <span className="attention-copy"><strong>{item.sku}</strong><small>{item.reason}</small></span>
                <span className={`priority-tag${item.required ? " priority-tag--required" : ""}`}>
                  {item.level}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <footer className="workspace-footer">
        <span><ShieldCheck size={14} /> {ui.commandCenter.footer.environment}</span>
        <span>{ui.commandCenter.footer.milestone}</span>
      </footer>
    </div>
  );
}
