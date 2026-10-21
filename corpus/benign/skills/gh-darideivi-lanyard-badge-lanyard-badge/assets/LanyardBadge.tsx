"use client";

// lanyard-badge: decorative hanging badge for a website hero (NOT a credential).
// No barcodes, QR codes, ID numbers or security marks, by design.
// Requires: React 19+ (boolean `inert`), Tailwind v3.4+ or v4, next/image.
// Configure everything through `config`; colors and fonts come from `config.theme`.

import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";

export type BadgePerson = {
  name: string; // "First Last"; first name becomes the signature
  role: string; // e.g. "Co-Owner"
  photo: string; // 3:4 portrait, e.g. /badge/david.webp
  photoFocusY?: string; // object-position Y for the square crop; default "22%" keeps head + chest logo
};

export type BadgeConfig = {
  company: {
    name: string;
    descriptor?: string; // e.g. "Commercial cleaning and facility services"
    tagline?: string; // shown in the script font
    iconSrc: string; // square-ish logo mark (transparent PNG/SVG)
    iconSize?: [number, number];
    wordmarkSrc?: string; // optional wordmark under the mark on the company card
    wordmarkSize?: [number, number];
  };
  chip?: string; // short pill on fronts, e.g. "MA and Southern NH"
  chipLabel?: string; // screen-reader prefix, e.g. "Serving"
  people: BadgePerson[];
  personBack: {
    heading: string; // e.g. "What we do"
    items: { title: string; detail: string; icon?: ReactNode }[]; // 3 fits best
  };
  companyFacts: [string, string][]; // verified facts only, 4-6 rows
  phone?: string;
  cta: { href: string; label: string };
  // Per card, ms from when it appears: auto-flip toggle times, and when the next card spins in.
  timeline?: { person: { flips: number[]; next: number }; company: { flips: number[]; next: number } };
  theme?: Partial<{
    ink: string; // names and headings
    accent: string; // role, links
    highlight: string; // top rule, active dot, chip icon
    strap: string; // lanyard strap
    muted: string; // secondary text
    surface: string; // chip and back gradient
    line: string; // dividers
    onDark: string; // control text on the hero background
    shine: string; // light that runs around the holder edge; "transparent" turns it off
    displayFont: string;
    scriptFont: string;
  }>;
};

const DEFAULT_TIMELINE = {
  person: { flips: [5_000, 8_000], next: 10_000 },
  company: { flips: [10_000, 20_000, 30_000, 40_000], next: 50_000 },
};
const TICK_MS = 100;
const SPIN_OUT_MS = 380;

const DEFAULT_THEME = {
  ink: "#0f2f5f",
  accent: "#1e78d7",
  highlight: "#21a9e8",
  strap: "#1e78d7",
  muted: "#4b5563",
  surface: "#f3f4f6",
  line: "#dde3ea",
  onDark: "#ffffff",
  shine: "#ffffff",
  displayFont: "inherit",
  scriptFont: "cursive",
};

const display: CSSProperties = { fontFamily: "var(--lb-display)" };
const script: CSSProperties = { fontFamily: "var(--lb-script)" };

function Chip({ children, label }: { children: ReactNode; label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full bg-[var(--lb-surface)] px-2.5 py-1 text-[0.6875rem] font-semibold text-[var(--lb-ink)]">
      <svg aria-hidden="true" viewBox="0 0 24 24" className="size-3 text-[var(--lb-accent)]" fill="none" stroke="currentColor" strokeWidth={2.25}>
        <path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21Z" />
        <circle cx="12" cy="9.5" r="2.5" />
      </svg>
      {label && <span className="sr-only">{label} </span>}
      {children}
    </span>
  );
}

function PersonFront({ person, config, priority }: { person: BadgePerson; config: BadgeConfig; priority: boolean }) {
  const [first, ...rest] = person.name.split(" ");
  const last = rest.join(" ");
  const { company } = config;
  return (
    <div className="flex h-full flex-col bg-white text-left">
      <div className="relative aspect-square w-full shrink-0 bg-[var(--lb-surface)]">
        <Image
          src={person.photo}
          alt={`${person.name}, ${person.role} of ${company.name}`}
          fill
          sizes="17rem"
          className="object-cover"
          style={{ objectPosition: `50% ${person.photoFocusY ?? "22%"}` }}
          priority={priority}
        />
      </div>
      <div className="flex flex-1 border-t-[3px] border-[var(--lb-highlight)]">
        <div className="flex min-w-0 flex-1 flex-col justify-center py-3 pr-2 pl-4">
          <p style={display} className="text-[1.5rem] leading-[0.95] font-extrabold tracking-[-0.03em] text-[var(--lb-ink)] uppercase">
            {first}
            {last && (
              <>
                <br />
                {last}
              </>
            )}
          </p>
          <p className="mt-2 text-[0.8125rem] leading-tight">
            <span className="font-semibold text-[var(--lb-accent)]">{person.role}</span>
            <span className="block text-[var(--lb-muted)]">{company.name}</span>
          </p>
          {config.chip && (
            <div className="mt-2.5">
              <Chip label={config.chipLabel}>{config.chip}</Chip>
            </div>
          )}
        </div>
        <div className="flex w-[4.25rem] shrink-0 flex-col items-center justify-between border-l border-dashed border-[var(--lb-line)] py-3">
          <span aria-hidden="true" style={script} className="-rotate-12 whitespace-nowrap text-[1.4rem] leading-none text-[var(--lb-ink)]">
            {first}
          </span>
          <Image src={company.iconSrc} alt="" width={company.iconSize?.[0] ?? 128} height={company.iconSize?.[1] ?? 128} className="h-auto w-8" />
        </div>
      </div>
    </div>
  );
}

function CompanyFront({ config }: { config: BadgeConfig }) {
  const { company } = config;
  return (
    <div className="relative flex h-full flex-col items-center justify-center gap-5 bg-white px-6 text-center">
      <div className="absolute inset-x-0 top-0 h-[3px] bg-[var(--lb-highlight)]" />
      <Image
        src={company.iconSrc}
        alt={company.wordmarkSrc ? "" : company.name}
        width={company.iconSize?.[0] ?? 128}
        height={company.iconSize?.[1] ?? 128}
        className="h-auto w-32 object-contain"
      />
      {company.wordmarkSrc && (
        <Image
          src={company.wordmarkSrc}
          alt={company.name}
          width={company.wordmarkSize?.[0] ?? 400}
          height={company.wordmarkSize?.[1] ?? 130}
          className="h-auto w-48 object-contain"
        />
      )}
      {company.tagline && (
        <p style={script} className="text-[1.6rem] leading-tight text-[var(--lb-ink)]">
          {company.tagline}
        </p>
      )}
      {config.chip && <Chip label={config.chipLabel}>{config.chip}</Chip>}
    </div>
  );
}

function BackFooter({ config }: { config: BadgeConfig }) {
  return (
    <div className="mt-auto flex flex-col items-start gap-1 border-t border-dashed border-[var(--lb-line)] pt-2.5 text-[0.8125rem]">
      {config.phone && (
        <a href={`tel:${config.phone.replace(/[^\d+]/g, "")}`} className="font-semibold text-[var(--lb-ink)] hover:opacity-80 active:opacity-70">
          {config.phone}
        </a>
      )}
      <a href={safeHref(config.cta.href)} className="font-semibold text-[var(--lb-accent)] hover:opacity-80 active:opacity-70">
        {config.cta.label}
      </a>
    </div>
  );
}

const backShell = "flex h-full flex-col bg-gradient-to-b from-white to-[var(--lb-surface)] px-4 pt-4 pb-3.5";
const tile = "rounded-xl bg-white shadow-[0_1px_2px_rgb(15_47_95/0.06)]";

function PersonBack({ config }: { config: BadgeConfig }) {
  return (
    <div className={backShell}>
      <p style={display} className="text-base font-bold text-[var(--lb-ink)]">
        {config.personBack.heading}
      </p>
      <ul className="mt-3 space-y-2">
        {config.personBack.items.map((item) => (
          <li key={item.title} className={`flex items-center gap-3 px-3 py-2.5 ${tile}`}>
            {item.icon && (
              <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-lg bg-[var(--lb-surface)] text-[var(--lb-accent)]">
                {item.icon}
              </span>
            )}
            <span className="min-w-0">
              <span className="block text-[0.8125rem] leading-tight font-bold text-[var(--lb-ink)]">{item.title}</span>
              <span className="block text-[0.6875rem] leading-snug text-[var(--lb-muted)]">{item.detail}</span>
            </span>
          </li>
        ))}
      </ul>
      {config.company.tagline && (
        <p style={script} className="mt-3 text-[1.5rem] leading-none text-[var(--lb-ink)]">
          {config.company.tagline}
        </p>
      )}
      <BackFooter config={config} />
    </div>
  );
}

function CompanyBack({ config }: { config: BadgeConfig }) {
  return (
    <div className={backShell}>
      <p style={display} className="text-base font-bold text-[var(--lb-ink)]">
        {config.company.name}
      </p>
      {config.company.descriptor && <p className="text-[0.75rem] text-[var(--lb-muted)]">{config.company.descriptor}</p>}
      <dl className={`mt-3 divide-y divide-[var(--lb-line)] px-3 text-[0.8125rem] ${tile}`}>
        {config.companyFacts.map(([k, v]) => (
          <div key={k} className="grid grid-cols-[4rem_1fr] gap-2 py-1.5">
            <dt className="text-[var(--lb-muted)]">{k}</dt>
            <dd className="font-semibold text-[var(--lb-ink)]">{v}</dd>
          </div>
        ))}
      </dl>
      <BackFooter config={config} />
    </div>
  );
}

// The clear plastic sleeve, drawn on both faces.
function Holder({ children }: { children: ReactNode }) {
  return (
    <>
      <div className="absolute inset-0 rounded-[1.6rem] border border-white/45 bg-[linear-gradient(160deg,rgb(255_255_255/0.24),rgb(255_255_255/0.07)_45%,rgb(255_255_255/0.14))] shadow-[inset_0_1px_0_rgb(255_255_255/0.4),0_34px_60px_-22px_rgb(0_0_0/0.6)]" />
      <div className="absolute top-[1.05rem] left-1/2 h-[0.95rem] w-24 -translate-x-1/2 rounded-full border border-white/55 bg-black/25" />
      <div className="absolute inset-x-3 top-12 bottom-3 overflow-hidden rounded-[1.1rem]">{children}</div>
      <div className="pointer-events-none absolute inset-0 rounded-[1.6rem] bg-[linear-gradient(115deg,transparent_38%,rgb(255_255_255/0.13)_46%,transparent_56%)]" />
      <span aria-hidden="true" className="lb-beams">
        {["top", "right", "bottom", "left"].map((s) => <i key={s} className={`lb-beam lb-${s}`} />)}
        {["tl", "tr", "br", "bl"].map((s) => <i key={s} className={`lb-spot lb-${s}`} />)}
      </span>
    </>
  );
}

const face = "absolute inset-0 [backface-visibility:hidden]";

// Links may be relative, #anchors, http(s), mailto or tel. Any other scheme (javascript:, data:) becomes "#".
const safeHref = (v: string) => {
  const s = v.trim();
  const bare = s.replace(/[\u0000-\u0020]/g, "");
  return /^[a-z][a-z\d+.-]*:/i.test(bare) && !/^(https?|mailto|tel):/i.test(bare) ? "#" : s;
};

// Sway, plus the edge shine: four beams run around the holder in turn, with soft corner dots.
const BADGE_CSS = `
@keyframes lb-sway { 0%,100% { transform: rotate(-1.1deg) } 50% { transform: rotate(1.1deg) } }
.lb-sway { transform-origin: 50% 0; animation: lb-sway 7s ease-in-out infinite; }
.lb-beams { position: absolute; inset: 0; border-radius: 1.6rem; overflow: hidden; pointer-events: none; color: var(--lb-shine, #fff); }
.lb-beam { position: absolute; filter: drop-shadow(0 0 3px currentColor); background: linear-gradient(var(--d), transparent, currentColor, transparent);
  animation: lb-beam-run 3.5s ease-in-out var(--t) infinite backwards, lb-beam-fade 1.2s ease-in-out var(--t) infinite alternate; }
.lb-top { --d: to right; --from: translateX(-100%); --to: translateX(200%); --t: 0s; top: 0; left: 0; width: 50%; height: 2px; }
.lb-right { --d: to bottom; --from: translateY(-100%); --to: translateY(200%); --t: .6s; top: 0; right: 0; width: 2px; height: 50%; }
.lb-bottom { --d: to right; --from: translateX(100%); --to: translateX(-200%); --t: 1.2s; bottom: 0; right: 0; width: 50%; height: 2px; }
.lb-left { --d: to bottom; --from: translateY(100%); --to: translateY(-200%); --t: 1.8s; bottom: 0; left: 0; width: 2px; height: 50%; }
.lb-spot { position: absolute; width: 5px; height: 5px; margin: -2.5px; border-radius: 9999px; background: currentColor; filter: blur(1px); animation: lb-spot-fade 2s ease-in-out infinite alternate; }
.lb-tr, .lb-br { width: 8px; height: 8px; margin: -4px; filter: blur(2px); }
.lb-tl { top: 7.5px; left: 7.5px; } .lb-tr { top: 7.5px; right: 7.5px; animation-duration: 2.4s; animation-delay: .5s; }
.lb-br { bottom: 7.5px; right: 7.5px; animation-duration: 2.2s; animation-delay: 1s; } .lb-bl { bottom: 7.5px; left: 7.5px; animation-duration: 2.3s; animation-delay: 1.5s; }
@keyframes lb-beam-run { 0% { transform: var(--from) } 71.4%, 100% { transform: var(--to) } }
@keyframes lb-beam-fade { from { opacity: .5 } to { opacity: 1 } }
@keyframes lb-spot-fade { from { opacity: .3 } to { opacity: .7 } }
@media (prefers-reduced-motion: reduce) { .lb-sway { animation: none; } .lb-beams { display: none; } }
`;

export function LanyardBadge({ config, className = "" }: { config: BadgeConfig; className?: string }) {
  const timeline = config.timeline ?? DEFAULT_TIMELINE;
  const theme = { ...DEFAULT_THEME, ...config.theme };

  const cards = [
    ...config.people.map((p, i) => ({
      key: p.name,
      label: p.name,
      front: <PersonFront person={p} config={config} priority={i === 0} />,
      back: <PersonBack config={config} />,
    })),
    { key: "company", label: config.company.name, front: <CompanyFront config={config} />, back: <CompanyBack config={config} /> },
  ];

  const [shown, setShown] = useState(0);
  const [phase, setPhase] = useState<"idle" | "out" | "in">("idle");
  const [flipped, setFlipped] = useState(false);
  const [manual, setManual] = useState(false); // visitor flipped it; timeline waits
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const timers = useRef<number[]>([]);
  const elapsed = useRef(0);
  const count = cards.length;

  // Plain data (no JSX) so the timer callbacks can depend on it safely.
  const plans = useMemo(
    () => [...config.people.map(() => timeline.person), timeline.company],
    [config.people, timeline],
  );
  const backAt = useCallback(
    (i: number, t: number) => plans[i].flips.filter((f) => f <= t).length % 2 === 1,
    [plans],
  );

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    const pending = timers.current;
    return () => {
      mq.removeEventListener("change", update);
      pending.forEach((t) => window.clearTimeout(t));
    };
  }, []);

  // Spin edge-on, swap the card, spin back to face front.
  const goTo = useCallback(
    (i: number) => {
      setFlipped(false);
      setManual(false);
      elapsed.current = 0;
      if (i === shown) return;
      if (reducedMotion) {
        setShown(i);
        return;
      }
      setPhase("out");
      timers.current.push(
        window.setTimeout(() => {
          setShown(i);
          setPhase("in");
          requestAnimationFrame(() => requestAnimationFrame(() => setPhase("idle")));
        }, SPIN_OUT_MS),
      );
    },
    [shown, reducedMotion],
  );

  // Advance the current card's timeline; elapsed time is kept while paused.
  useEffect(() => {
    if (reducedMotion || manual || hovered || focused || phase !== "idle") return;
    let last = performance.now();
    const id = window.setInterval(() => {
      const now = performance.now();
      elapsed.current += now - last;
      last = now;
      if (elapsed.current >= plans[shown].next) goTo((shown + 1) % count);
      else setFlipped(backAt(shown, elapsed.current));
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [shown, phase, reducedMotion, manual, hovered, focused, goTo, backAt, plans, count]);

  function userFlip(toBack: boolean) {
    setFlipped(toBack);
    setManual(toBack);
    // Flipping to the front ends any automatic back window so it doesn't flip straight back.
    const t = elapsed.current;
    if (!toBack && backAt(shown, t)) {
      const plan = plans[shown];
      elapsed.current = plan.flips.find((f) => f > t) ?? plan.next;
    }
  }

  const card = cards[Math.min(shown, count - 1)];
  const angle = phase === "out" ? (flipped ? 270 : 90) : phase === "in" ? -90 : flipped ? 180 : 0;
  const transition =
    phase === "in"
      ? "none"
      : phase === "out"
        ? `transform ${SPIN_OUT_MS}ms cubic-bezier(0.5,0,0.75,0)`
        : "transform 750ms cubic-bezier(0.2,0.75,0.2,1)";

  const vars = {
    "--lb-ink": theme.ink,
    "--lb-accent": theme.accent,
    "--lb-highlight": theme.highlight,
    "--lb-strap": theme.strap,
    "--lb-muted": theme.muted,
    "--lb-surface": theme.surface,
    "--lb-line": theme.line,
    "--lb-on-dark": theme.onDark,
    "--lb-shine": theme.shine,
    "--lb-display": theme.displayFont,
    "--lb-script": theme.scriptFont,
  } as CSSProperties;

  return (
    <div style={vars} className={`mx-auto w-full max-w-[17.5rem] [--strap:5rem] lg:mx-0 lg:w-[17.5rem] lg:[--strap:8rem] ${className}`}>
      <style>{BADGE_CSS}</style>
      <div className="lb-sway relative pt-[var(--strap)]">
        {/* Strap and clip stay put while the badge spins. */}
        <div
          aria-hidden="true"
          className="absolute top-0 left-1/2 h-[calc(var(--strap)+0.6rem)] w-7 -translate-x-1/2 border-x border-white/20 bg-[var(--lb-strap)] [mask-image:linear-gradient(to_bottom,transparent,black_45%)]"
        />
        <div
          aria-hidden="true"
          className="absolute top-[calc(var(--strap)-0.2rem)] left-1/2 z-10 h-7 w-[1.15rem] -translate-x-1/2 rounded-[5px] bg-gradient-to-b from-[#eef1f5] to-[#9aa6b6] shadow-[0_2px_4px_rgb(0_0_0/0.35)]"
        />

        <div
          role="region"
          aria-roledescription="carousel"
          aria-label={`${config.company.name} team badges`}
          className="relative aspect-[17.5/31] [perspective:1200px]"
          onPointerEnter={(e) => e.pointerType === "mouse" && setHovered(true)}
          onPointerLeave={() => setHovered(false)}
          onFocus={() => setFocused(true)}
          onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setFocused(false)}
        >
          <div
            role="group"
            aria-roledescription="slide"
            aria-label={`${card.label} (${shown + 1} of ${count})`}
            className="relative size-full [transform-style:preserve-3d]"
            style={{ transform: `rotateY(${angle}deg)`, transition }}
          >
            <div className={face} inert={flipped}>
              <Holder>
                <button
                  type="button"
                  onClick={() => userFlip(true)}
                  aria-label={`${card.label}: show details`}
                  className="block size-full cursor-pointer rounded-[1.1rem] text-left"
                >
                  {card.front}
                </button>
              </Holder>
            </div>
            <div className={`${face} [transform:rotateY(180deg)]`} inert={!flipped}>
              {/* Clicking anywhere but a link flips back; keyboard users have the toggle button. */}
              <div className="size-full cursor-pointer" onClick={(e) => !(e.target as HTMLElement).closest("a") && userFlip(false)}>
                <Holder>{card.back}</Holder>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-1">
          {cards.map((c, i) => (
            <button
              key={c.key}
              type="button"
              onClick={() => goTo(i)}
              aria-label={`Show ${c.label} badge`}
              aria-current={i === shown}
              className="group grid size-6 place-items-center rounded-full"
            >
              <span
                className={`block size-1.5 rounded-full transition-[transform,opacity] duration-300 group-hover:opacity-100 group-active:scale-90 ${
                  i === shown ? "scale-[1.6] bg-[var(--lb-highlight)] opacity-100" : "bg-[var(--lb-on-dark)] opacity-40"
                }`}
              />
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => userFlip(!flipped)}
          aria-pressed={flipped}
          className="rounded-md px-1 text-sm font-semibold text-[var(--lb-on-dark)] opacity-80 hover:opacity-100 active:opacity-70"
        >
          {flipped ? "Show front" : "Show details"}
        </button>
      </div>
    </div>
  );
}
