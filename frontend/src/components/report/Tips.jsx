export const Tips = ({ tips }) => (
  <section className="card fade-up" data-testid="negotiation-tips">
    <h2 className="font-display text-xl font-bold text-slate-100">Negotiation tips</h2>
    <ol className="mt-5 space-y-4">
      {tips.map((t, i) => (
        <li key={t} className="flex gap-4" data-testid={`tip-${i}`}>
          <span className="font-num text-sm font-bold text-emerald-400">{String(i + 1).padStart(2, "0")}</span>
          <span className="text-sm leading-relaxed text-slate-300">{t}</span>
        </li>
      ))}
    </ol>
  </section>
);
