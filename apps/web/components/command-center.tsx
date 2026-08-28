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

const healthMetrics = [
  { label: "Data readiness", value: "Ready", tone: "positive" },
  { label: "Coverage", value: "—", tone: "neutral" },
  { label: "Last cycle", value: "Not run", tone: "neutral" },
] as const;

const signals = [
  { source: "Market context", state: "Awaiting sources", icon: Satellite },
  { source: "Calendar effects", state: "Not configured", icon: Clock },
  { source: "Operational events", state: "Ready for input", icon: Bell },
] as const;

const attentionItems = [
  { sku: "Portfolio baseline", reason: "Import product data to begin", level: "Setup" },
  { sku: "Demand history", reason: "No historical series connected", level: "Required" },
] as const;

export function CommandCenter() {
  return (
    <div className="workspace command-center">
      <header className="workspace-header">
        <div>
          <span className="eyebrow">Operational overview / 01</span>
          <h1>Command Center</h1>
          <p>Your demand operation, composed into one decision surface.</p>
        </div>
        <div className="header-actions">
          <span className="system-state"><span /> System ready</span>
          <button className="icon-button" type="button" aria-label="Refresh workspace">
            <RefreshCcw size={17} />
          </button>
          <button className="icon-button" type="button" aria-label="Notifications">
            <Bell size={17} />
          </button>
        </div>
      </header>

      <section className="timeline-panel" aria-labelledby="demand-timeline-title">
        <div className="panel-heading">
          <div>
            <span className="section-index">01 / Demand horizon</span>
            <h2 id="demand-timeline-title">Demand timeline</h2>
          </div>
          <div className="timeline-key" aria-label="Timeline legend">
            <span><i className="key-line key-line--solid" /> Actual</span>
            <span><i className="key-line key-line--dash" /> Forecast</span>
          </div>
        </div>

        <div className="timeline-stage">
          <div className="timeline-overlay">
            <span className="stage-kicker">Analysis surface reserved</span>
            <strong>Connect demand history to activate the horizon.</strong>
            <p>Forecasting and scenario logic will be introduced in a later milestone.</p>
            <Link className="text-action" href="/data-studio">
              Review data requirements <ArrowUpRight size={15} />
            </Link>
          </div>
          <svg
            className="timeline-graphic"
            viewBox="0 0 1000 310"
            role="img"
            aria-label="Empty demand timeline prepared for future demand history and forecast data"
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
            <span>W01</span><span>W04</span><span>W08</span><span>W12</span><span>W16</span><span>W20</span>
          </div>
        </div>
      </section>

      <div className="intelligence-grid">
        <section className="intelligence-section forecast-health" aria-labelledby="forecast-health-title">
          <div className="section-heading-row">
            <div>
              <span className="section-index">02 / Reliability</span>
              <h2 id="forecast-health-title">Forecast health</h2>
            </div>
            <ShieldCheck size={19} aria-hidden="true" />
          </div>
          <div className="health-score">
            <span className="score-ring"><span>—</span></span>
            <div>
              <strong>Baseline pending</strong>
              <p>Health metrics begin after the first validated forecast cycle.</p>
            </div>
          </div>
          <dl className="metric-list">
            {healthMetrics.map((metric) => (
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
              <span className="section-index">03 / Context</span>
              <h2 id="external-signals-title">External signals</h2>
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
              <span className="section-index">04 / Priority queue</span>
              <h2 id="attention-title">Products requiring attention</h2>
            </div>
            <TriangleAlert size={19} aria-hidden="true" />
          </div>
          <div className="attention-list">
            {attentionItems.map((item, index) => (
              <div className="attention-row" key={item.sku}>
                <span className="queue-number">0{index + 1}</span>
                <span className="attention-copy"><strong>{item.sku}</strong><small>{item.reason}</small></span>
                <span className={`priority-tag${item.level === "Required" ? " priority-tag--required" : ""}`}>
                  {item.level}
                </span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <footer className="workspace-footer">
        <span><ShieldCheck size={14} /> Foundation environment</span>
        <span>Milestone 01</span>
      </footer>
    </div>
  );
}
