import { useState, useMemo, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import type {
  ContradictionFlag,
  FactObject,
  MarketPulseReport,
  SignalType,
  WatchItem,
} from '@/types/api'
import { formatDate } from '@/lib/utils'
import TierBadge from '@/shared/components/tier-badge'
import SentimentBadge from '@/shared/components/sentiment-badge'
import {
  ArrowRight,
  ShieldCheck,
  ExternalLink,
  MessageSquare,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Activity,
  X,
} from 'lucide-react'

interface WorkspaceOverviewProps {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading?: boolean
}

// ─── Constants ───────────────────────────────────────────────────────────────

const SIGNAL_LABELS: Record<SignalType, string> = {
  hiring_momentum: 'Hiring Momentum',
  product_launch: 'Product Launch',
  pricing_pressure: 'Pricing Pressure',
  strategic_messaging: 'Strategic Messaging',
  investor_signal: 'Investor Signal',
  news_sentiment: 'News Sentiment',
  supplier_risk: 'Supplier Risk',
}

const SIGNAL_COLORS: Record<SignalType, string> = {
  product_launch: 'bg-blue-500',
  pricing_pressure: 'bg-amber-500',
  investor_signal: 'bg-purple-500',
  strategic_messaging: 'bg-indigo-500',
  supplier_risk: 'bg-red-500',
  news_sentiment: 'bg-teal-500',
  hiring_momentum: 'bg-emerald-500',
}

const URGENCY_STYLES: Record<WatchItem['urgency'], { label: string; cls: string }> = {
  this_week:    { label: 'This Week',    cls: 'bg-red-50 text-red-700 border-red-200' },
  next_2_weeks: { label: 'Next 2 Weeks', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  this_month:   { label: 'This Month',   cls: 'bg-blue-50 text-blue-700 border-blue-200' },
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function stripIds(text: string): string {
  return text.replace(/\[(?:fact|claim)_[^\]]+\]/gi, '').replace(/\s{2,}/g, ' ').trim()
}

function sourceDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

type SignalStat = {
  sig: SignalType
  sFacts: FactObject[]
  safeCount: number
  avgConf: number | null
  scoreContrib: number | null
  narrative: string | null
}

function computeSignalStats(facts: FactObject[], report: MarketPulseReport): SignalStat[] {
  const sigSet = new Set<SignalType>([
    ...report.top_signals.map(s => s.signal_type),
    ...facts.map(f => f.signal_type),
  ])
  return Array.from(sigSet).map(sig => {
    const sFacts = facts.filter(f => f.signal_type === sig)
    const safeCount = sFacts.filter(f => f.safe_verified).length
    const avgConf = sFacts.length > 0
      ? sFacts.reduce((a, f) => a + f.confidence, 0) / sFacts.length
      : null
    const scoreContrib = (report.signal_breakdown[sig] as number | undefined) ?? null
    const narrative = report.top_signals.find(s => s.signal_type === sig)?.narrative ?? null
    return { sig, sFacts, safeCount, avgConf, scoreContrib, narrative }
  }).sort((a, b) =>
    (b.scoreContrib ?? 0) - (a.scoreContrib ?? 0) || b.sFacts.length - a.sFacts.length
  )
}

// Marquee activates only when the section has at least this many unique items.
// Fewer items → static flex row (no duplication, no animation).
const MARQUEE_MIN_ITEMS = 3

// ─── Popover positioning ──────────────────────────────────────────────────────

const POPOVER_W = 400
const POPOVER_GAP = 12

/**
 * `PopoverState` stores a pre-computed absolute position so we only run
 * the geometry once (at click time, when both rects are fresh).
 */
type PopoverState = { idx: number; pos: PopoverPos } | null
type PopoverPos = { top: number; left: number }

/**
 * Compute the popover's position RELATIVE TO the section element so that
 * `position: absolute` inside that section scrolls naturally with the page.
 *
 * Math: both `cardRect` and `sectionRect` are viewport-relative, so their
 * difference is scroll-invariant and directly usable as absolute offsets.
 *
 *   absTop  = cardRect.top  − sectionRect.top   (unchanged as user scrolls)
 *   absLeft = cardRect.right − sectionRect.left + gap   (right-of-card)
 */
function computePopoverPos(cardRect: DOMRect, sectionEl: HTMLElement): PopoverPos {
  if (typeof window === 'undefined') return { top: 0, left: 0 }
  const sectionRect = sectionEl.getBoundingClientRect()

  const top = cardRect.top - sectionRect.top

  // Prefer right of card; fall back to left if right overflows viewport
  let left = cardRect.right - sectionRect.left + POPOVER_GAP
  if (cardRect.right + POPOVER_W + POPOVER_GAP > window.innerWidth - POPOVER_GAP) {
    left = cardRect.left - sectionRect.left - POPOVER_W - POPOVER_GAP
    if (left < 0) left = 0  // clamp to section left edge
  }

  return { top, left }
}

// ─── Brief Panel ─────────────────────────────────────────────────────────────

function BriefPanel({ report }: { report: MarketPulseReport }) {
  const [showFullBody, setShowFullBody] = useState(false)
  const narrative = report.market_narrative
  const headline = stripIds(narrative.narrative_headline)
  const bodyText = stripIds(narrative.narrative_body)
  const BODY_LIMIT = 300
  const isTruncatable = bodyText.length > BODY_LIMIT

  const drivers = useMemo(() => {
    const raw: string[] = [
      ...(report.grounded_brief?.what_we_found ?? []).map(s => stripIds(s.text)),
      ...report.top_signals.slice(0, 3).map(s => stripIds(s.narrative)).filter(Boolean),
      ...report.company_narratives
        .flatMap(n => n.key_drivers.slice(0, 1))
        .map(stripIds)
        .filter(Boolean),
    ]
    return Array.from(new Set(raw.filter(b => b.length > 10))).slice(0, 5)
  }, [report])

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Morning Brief</p>

      <h2 className="mt-2 text-2xl font-bold leading-snug text-gray-950">{headline}</h2>

      <div className="mt-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">Why it matters</p>
        <p className="text-base leading-7 text-gray-700">
          {showFullBody || !isTruncatable
            ? bodyText
            : bodyText.slice(0, BODY_LIMIT).replace(/\s+\S*$/, '') + '…'}
        </p>
        {isTruncatable && (
          <button
            type="button"
            onClick={() => setShowFullBody(v => !v)}
            className="mt-1.5 flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-700"
          >
            {showFullBody
              ? <><ChevronUp className="h-3 w-3" /> Show less</>
              : <><ChevronDown className="h-3 w-3" /> Show more</>}
          </button>
        )}
      </div>

      {drivers.length > 0 && (
        <div className="mt-6">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400">Key drivers</p>
          <div className="grid gap-2 md:grid-cols-2">
            {drivers.map((driver, idx) => (
              <div key={idx} className="flex items-start gap-2.5 rounded-xl bg-gray-50 px-4 py-3">
                <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                <p className="text-sm leading-relaxed text-gray-700">{driver}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Single CTA — navigation to deeper analysis is via workspace tabs */}
      <div className="mt-6 border-t border-gray-100 pt-5">
        <Link
          to="/chat?context=report"
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          <MessageSquare className="h-4 w-4" />
          Ask Chat about this report
        </Link>
      </div>
    </section>
  )
}

// ─── Watch Items Marquee ──────────────────────────────────────────────────────

function WatchItemCard({
  item,
  isSelected = false,
  onSelect,
  suppressKeyboard = false,
}: {
  item: WatchItem
  isSelected?: boolean
  onSelect?: (rect: DOMRect, e: React.MouseEvent) => void
  suppressKeyboard?: boolean
}) {
  const urgency = URGENCY_STYLES[item.urgency] ?? URGENCY_STYLES.this_month
  const rationale = stripIds(item.rationale)
  const trigger = stripIds(item.trigger)

  function handleClick(e: React.MouseEvent) {
    onSelect?.((e.currentTarget as HTMLElement).getBoundingClientRect(), e)
  }

  return (
    <article
      role="button"
      tabIndex={suppressKeyboard ? -1 : 0}
      aria-pressed={isSelected}
      onClick={handleClick}
      onKeyDown={suppressKeyboard ? undefined : (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect?.((e.currentTarget as HTMLElement).getBoundingClientRect(), e as unknown as React.MouseEvent)
        }
      }}
      className={[
        'flex w-[360px] shrink-0 flex-col gap-3 rounded-2xl border p-5 shadow-sm transition-all cursor-pointer',
        isSelected
          ? 'border-blue-400 bg-blue-50/40 ring-2 ring-blue-200 ring-offset-1'
          : 'border-gray-200 bg-white hover:border-blue-200 hover:shadow-md',
      ].join(' ')}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-bold leading-snug text-gray-950">{item.title}</h3>
        <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${urgency.cls}`}>
          {urgency.label}
        </span>
      </div>

      <p className="line-clamp-3 text-sm leading-relaxed text-gray-600">{rationale}</p>

      <div className="rounded-lg bg-gray-50 px-3 py-2">
        <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Trigger</p>
        <p className="line-clamp-2 text-xs leading-5 text-gray-700">{trigger}</p>
      </div>

      <div className="flex items-center justify-between border-t border-gray-100 pt-3">
        <span className="text-xs text-gray-500">{item.signals_pointing_there.length} signal refs</span>
        <Link
          to="/chat?context=report"
          className="flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
          onClick={e => e.stopPropagation()}
          tabIndex={suppressKeyboard ? -1 : undefined}
        >
          <MessageSquare className="h-3 w-3" /> Chat
        </Link>
      </div>
    </article>
  )
}

function WatchItemPopover({
  item,
  pos,
  onClose,
  containerRef,
}: {
  item: WatchItem
  pos: PopoverPos
  onClose: () => void
  containerRef: { current: HTMLDivElement | null }
}) {
  const urgency = URGENCY_STYLES[item.urgency] ?? URGENCY_STYLES.this_month
  const rationale = stripIds(item.rationale)
  const trigger = stripIds(item.trigger)

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-label={`Watch item: ${item.title}`}
      style={{
        position: 'absolute',
        top: pos.top,
        left: pos.left,
        width: `${POPOVER_W}px`,
        zIndex: 10,
      }}
      className="rounded-2xl border border-blue-200 bg-white p-6 shadow-xl"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-base font-bold text-gray-950">{item.title}</h3>
          <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${urgency.cls}`}>
            {urgency.label}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-4">
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-400">Rationale</p>
        <p className="text-sm leading-relaxed text-gray-700">{rationale}</p>
      </div>

      <div className="mb-4 rounded-lg bg-gray-50 px-4 py-3">
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-400">Trigger to watch</p>
        <p className="text-sm leading-relaxed text-gray-700">{trigger}</p>
      </div>

      <p className="mb-4 text-xs text-gray-500">{item.signals_pointing_there.length} signal references</p>

      <div className="flex flex-wrap gap-2 border-t border-gray-100 pt-4">
        <Link
          to="/chat?context=report"
          className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          <MessageSquare className="h-4 w-4" /> Ask Chat
        </Link>
      </div>
    </div>
  )
}

function WatchItemMarquee({ items }: { items: WatchItem[] }) {
  const [hoverPaused, setHoverPaused] = useState(false)
  const [popover, setPopover] = useState<PopoverState>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const sectionRef = useRef<HTMLElement>(null)
  const openedByRef = useRef<EventTarget | null>(null)
  const useMarquee = items.length >= MARQUEE_MIN_ITEMS
  const isPaused = hoverPaused || popover !== null
  const selectedItem = popover !== null ? (items[popover.idx] ?? null) : null
  // pos is pre-computed at click time and stored directly in state
  const popoverPos = popover?.pos ?? { top: 0, left: 0 }

  function close() {
    setPopover(null)
    openedByRef.current = null
  }

  function handleCardSelect(idx: number, rect: DOMRect, e: React.MouseEvent) {
    openedByRef.current = e.currentTarget
    if (popover?.idx === idx) { close(); return }
    // Compute section-relative position once at click time.
    // The difference (cardRect − sectionRect) is scroll-invariant, so the
    // absolute-positioned popover stays beside the card as the page scrolls.
    const pos = sectionRef.current
      ? computePopoverPos(rect, sectionRef.current)
      : { top: 0, left: 0 }
    setPopover({ idx, pos })
  }

  // Click outside closes the popover (but not clicking the card that opened it)
  useEffect(() => {
    if (!popover) return
    function handleDown(e: MouseEvent) {
      const t = e.target as Node
      if (popoverRef.current?.contains(t)) return
      if (openedByRef.current && (openedByRef.current as Node).contains(t)) return
      close()
    }
    document.addEventListener('mousedown', handleDown)
    return () => document.removeEventListener('mousedown', handleDown)
  }, [popover]) // eslint-disable-line react-hooks/exhaustive-deps

  // Escape closes the popover
  useEffect(() => {
    if (!popover) return
    function handleEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [popover]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section ref={sectionRef} className="relative rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Action Queue</p>
          <h2 className="mt-1 text-xl font-bold text-gray-950">What to monitor next</h2>
        </div>
        <Link to="/workspace/evidence" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          All evidence →
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="flex items-center justify-center rounded-xl bg-gray-50 px-6 py-8 text-center">
          <div>
            <p className="text-sm font-semibold text-gray-600">No watch items were generated for this report.</p>
            <p className="mt-1 text-xs text-gray-400">
              The narrative synthesizer did not surface unresolved forward indicators for this run.
            </p>
          </div>
        </div>
      ) : !useMarquee ? (
        /* Static row for 1–2 unique items */
        <div className="flex flex-wrap gap-5 py-1">
          {items.map((item, idx) => (
            <WatchItemCard
              key={idx}
              item={item}
              isSelected={popover?.idx === idx}
              onSelect={(rect, e) => handleCardSelect(idx, rect, e)}
            />
          ))}
        </div>
      ) : (
        /*
         * Seamless marquee for 3+ items.
         * Both groups are fully clickable. Group 2 uses suppressKeyboard so
         * keyboard users tab to group 1 only, but mouse clicks work on all cards.
         * The parent <div aria-hidden="true"> hides group 2 from screen readers.
         */
        <div
          className={isPaused ? 'marquee-paused marquee-viewport py-1' : 'marquee-viewport py-1'}
          onMouseEnter={() => setHoverPaused(true)}
          onMouseLeave={() => setHoverPaused(false)}
        >
          <div className="marquee-track" style={{ animationDuration: '18s' }}>
            {/* Group 1 — fully interactive (keyboard + mouse) */}
            <div className="marquee-group">
              {items.map((item, i) => (
                <WatchItemCard
                  key={`a-${i}`}
                  item={item}
                  isSelected={popover?.idx === i}
                  onSelect={(rect, e) => handleCardSelect(i, rect, e)}
                />
              ))}
            </div>
            {/* Group 2 — mouse-clickable; keyboard-hidden via suppressKeyboard;
                screen-reader-hidden via parent aria-hidden */}
            <div className="marquee-group" aria-hidden="true">
              {items.map((item, i) => (
                <WatchItemCard
                  key={`b-${i}`}
                  item={item}
                  isSelected={popover?.idx === i}
                  onSelect={(rect, e) => handleCardSelect(i, rect, e)}
                  suppressKeyboard
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Absolute-positioned popover — inside the relative section, scrolls with the page */}
      {selectedItem && (
        <WatchItemPopover
          item={selectedItem}
          pos={popoverPos}
          onClose={close}
          containerRef={popoverRef}
        />
      )}
    </section>
  )
}

// ─── Risk Alerts Marquee ──────────────────────────────────────────────────────

function RiskAlertCard({
  contradiction: c,
  isSelected = false,
  onSelect,
  suppressKeyboard = false,
}: {
  contradiction: ContradictionFlag
  isSelected?: boolean
  onSelect?: (rect: DOMRect, e: React.MouseEvent) => void
  suppressKeyboard?: boolean
}) {
  function handleClick(e: React.MouseEvent) {
    onSelect?.((e.currentTarget as HTMLElement).getBoundingClientRect(), e)
  }

  return (
    <article
      role="button"
      tabIndex={suppressKeyboard ? -1 : 0}
      aria-pressed={isSelected}
      onClick={handleClick}
      onKeyDown={suppressKeyboard ? undefined : (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect?.((e.currentTarget as HTMLElement).getBoundingClientRect(), e as unknown as React.MouseEvent)
        }
      }}
      className={[
        'flex w-[360px] shrink-0 flex-col gap-3 rounded-2xl border p-5 shadow-sm transition-all cursor-pointer',
        isSelected
          ? 'border-amber-400 bg-amber-50/40 ring-2 ring-amber-200 ring-offset-1'
          : 'border-amber-200 bg-white hover:border-amber-300 hover:shadow-md',
      ].join(' ')}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-800">
          {c.entity}
        </span>
        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">
          {SIGNAL_LABELS[c.signal_type] ?? c.signal_type}
        </span>
        <AlertTriangle className="ml-auto h-4 w-4 shrink-0 text-amber-500" />
      </div>

      <p className="line-clamp-3 text-sm leading-5 text-gray-700">{stripIds(c.note)}</p>

      <div className="flex items-center gap-3 text-xs">
        <span className="font-medium text-emerald-600">{c.positive_facts.length} supporting</span>
        <span className="text-gray-300">·</span>
        <span className="font-medium text-red-600">{c.negative_facts.length} against</span>
      </div>

      <div className="flex items-center gap-1.5 border-t border-amber-100 pt-3">
        <Link
          to={`/chat?context=signal&signal=${c.signal_type}`}
          className="flex items-center gap-1 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-100"
          onClick={e => e.stopPropagation()}
          tabIndex={suppressKeyboard ? -1 : undefined}
        >
          <MessageSquare className="h-3 w-3" /> Ask Chat
        </Link>
      </div>
    </article>
  )
}

function RiskAlertPopover({
  contradiction: c,
  pos,
  onClose,
  containerRef,
}: {
  contradiction: ContradictionFlag
  pos: PopoverPos
  onClose: () => void
  containerRef: { current: HTMLDivElement | null }
}) {
  const note = stripIds(c.note)

  return (
    <div
      ref={containerRef}
      role="dialog"
      aria-label={`Risk alert: ${c.entity}`}
      style={{
        position: 'absolute',
        top: pos.top,
        left: pos.left,
        width: `${POPOVER_W}px`,
        zIndex: 10,
      }}
      className="rounded-2xl border border-amber-300 bg-white p-6 shadow-xl"
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-gray-100 px-2.5 py-1 text-sm font-semibold text-gray-800">
            {c.entity}
          </span>
          <span className="rounded-full bg-amber-50 px-2.5 py-1 text-sm font-semibold text-amber-700">
            {SIGNAL_LABELS[c.signal_type] ?? c.signal_type}
          </span>
          <AlertTriangle className="h-4 w-4 text-amber-500" />
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="shrink-0 rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mb-5">
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-gray-400">Risk Summary</p>
        <p className="text-sm leading-relaxed text-gray-700">{note}</p>
      </div>

      <div className="mb-5 grid grid-cols-2 gap-4">
        <div className="rounded-lg bg-emerald-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">Supporting</p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">{c.positive_facts.length}</p>
          <p className="text-xs text-emerald-600">evidence facts</p>
        </div>
        <div className="rounded-lg bg-red-50 px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-red-600">Against</p>
          <p className="mt-1 text-2xl font-bold text-red-700">{c.negative_facts.length}</p>
          <p className="text-xs text-red-600">evidence facts</p>
        </div>
      </div>

      <div className="mb-5 rounded-lg bg-amber-50 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Recommended action</p>
        <p className="mt-1 text-sm text-amber-800">
          Review both supporting and against evidence before acting on this signal.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 border-t border-amber-100 pt-4">
        <Link
          to={`/chat?context=signal&signal=${c.signal_type}`}
          className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600"
        >
          <MessageSquare className="h-4 w-4" /> Ask Chat
        </Link>
      </div>
    </div>
  )
}

function RiskAlertMarquee({ contradictions }: { contradictions: ContradictionFlag[] }) {
  const [hoverPaused, setHoverPaused] = useState(false)
  const [popover, setPopover] = useState<PopoverState>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const sectionRef = useRef<HTMLElement>(null)
  const openedByRef = useRef<EventTarget | null>(null)
  const useMarquee = contradictions.length >= MARQUEE_MIN_ITEMS
  const isPaused = hoverPaused || popover !== null
  const selectedItem = popover !== null ? (contradictions[popover.idx] ?? null) : null
  const popoverPos = popover?.pos ?? { top: 0, left: 0 }

  function close() {
    setPopover(null)
    openedByRef.current = null
  }

  function handleCardSelect(idx: number, rect: DOMRect, e: React.MouseEvent) {
    openedByRef.current = e.currentTarget
    if (popover?.idx === idx) { close(); return }
    const pos = sectionRef.current
      ? computePopoverPos(rect, sectionRef.current)
      : { top: 0, left: 0 }
    setPopover({ idx, pos })
  }

  useEffect(() => {
    if (!popover) return
    function handleDown(e: MouseEvent) {
      const t = e.target as Node
      if (popoverRef.current?.contains(t)) return
      if (openedByRef.current && (openedByRef.current as Node).contains(t)) return
      close()
    }
    document.addEventListener('mousedown', handleDown)
    return () => document.removeEventListener('mousedown', handleDown)
  }, [popover]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!popover) return
    function handleEsc(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [popover]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section ref={sectionRef} className="relative rounded-2xl border border-amber-200 bg-amber-50/20 p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Risk Alerts</p>
          <h2 className="mt-1 text-xl font-bold text-gray-950">Contradiction review</h2>
        </div>
        <Link to="/workspace/evidence" className="text-sm font-semibold text-amber-700 hover:text-amber-800">
          All evidence →
        </Link>
      </div>

      {contradictions.length === 0 ? (
        <div className="flex items-center justify-center rounded-xl border border-emerald-100 bg-emerald-50/40 px-6 py-8 text-center">
          <div>
            <p className="text-sm font-semibold text-emerald-800">No contradictions detected in the latest report.</p>
            <p className="mt-1 text-xs text-emerald-600">
              The report found no conflicting evidence across entity-signal pairs.
            </p>
          </div>
        </div>
      ) : !useMarquee ? (
        /* Static row for 1–2 unique items */
        <div className="flex flex-wrap gap-5 py-1">
          {contradictions.map((c, idx) => (
            <RiskAlertCard
              key={idx}
              contradiction={c}
              isSelected={popover?.idx === idx}
              onSelect={(rect, e) => handleCardSelect(idx, rect, e)}
            />
          ))}
        </div>
      ) : (
        /* Seamless marquee for 3+ items — both groups are fully clickable */
        <div
          className={isPaused ? 'marquee-paused marquee-viewport py-1' : 'marquee-viewport py-1'}
          onMouseEnter={() => setHoverPaused(true)}
          onMouseLeave={() => setHoverPaused(false)}
        >
          <div className="marquee-track" style={{ animationDuration: '20s' }}>
            <div className="marquee-group">
              {contradictions.map((c, i) => (
                <RiskAlertCard
                  key={`a-${i}`}
                  contradiction={c}
                  isSelected={popover?.idx === i}
                  onSelect={(rect, e) => handleCardSelect(i, rect, e)}
                />
              ))}
            </div>
            <div className="marquee-group" aria-hidden="true">
              {contradictions.map((c, i) => (
                <RiskAlertCard
                  key={`b-${i}`}
                  contradiction={c}
                  isSelected={popover?.idx === i}
                  onSelect={(rect, e) => handleCardSelect(i, rect, e)}
                  suppressKeyboard
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Absolute-positioned popover — inside the relative section, scrolls with the page */}
      {selectedItem && (
        <RiskAlertPopover
          contradiction={selectedItem}
          pos={popoverPos}
          onClose={close}
          containerRef={popoverRef}
        />
      )}
    </section>
  )
}

// ─── Signal Cockpit ───────────────────────────────────────────────────────────

function SignalCockpit({
  report,
  facts,
  factsLoading,
  selectedSignal,
  onSelectSignal,
}: {
  report: MarketPulseReport
  facts: FactObject[]
  factsLoading: boolean
  selectedSignal: SignalType | null
  onSelectSignal: (sig: SignalType) => void
}) {
  const signalStats = useMemo(() => computeSignalStats(facts, report), [facts, report])
  const maxCount = Math.max(...signalStats.map(s => s.sFacts.length), 1)
  const selectedStat = selectedSignal
    ? (signalStats.find(s => s.sig === selectedSignal) ?? null)
    : null

  const signalTopFacts = useMemo(() => {
    if (!selectedSignal) return []
    return facts
      .filter(f => f.signal_type === selectedSignal)
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 2)
  }, [selectedSignal, facts])

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Signal Cockpit</p>
          <h2 className="mt-1 text-xl font-bold text-gray-950">Evidence depth by signal type</h2>
          <p className="mt-1 text-xs text-gray-400">
            Evidence counts from live facts ·{' '}
            <span className="font-mono">signal_breakdown</span> values are weighted score contributions, not counts
          </p>
        </div>
        <Link
          to="/workspace/signals"
          className="flex shrink-0 items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700"
        >
          Open Signal Radar <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
        <div className="flex flex-col gap-1.5">
          {factsLoading ? (
            <div className="flex flex-col gap-2">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="h-14 animate-pulse rounded-xl bg-gray-100" />
              ))}
            </div>
          ) : (
            signalStats.map(stat => {
              const pct = maxCount > 0 ? (stat.sFacts.length / maxCount) * 100 : 0
              const isSelected = selectedSignal === stat.sig
              return (
                <button
                  key={stat.sig}
                  type="button"
                  onClick={() => onSelectSignal(stat.sig)}
                  className={[
                    'flex flex-col gap-1.5 rounded-xl border p-3 text-left transition-all',
                    isSelected
                      ? 'border-blue-200 bg-blue-50/60 ring-1 ring-blue-200'
                      : 'border-gray-100 hover:border-gray-300 hover:bg-gray-50',
                  ].join(' ')}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${SIGNAL_COLORS[stat.sig]}`} />
                      <span className={`text-sm font-semibold ${isSelected ? 'text-blue-900' : 'text-gray-800'}`}>
                        {SIGNAL_LABELS[stat.sig]}
                      </span>
                    </div>
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-bold tabular-nums text-gray-700">
                      {stat.sFacts.length} facts
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${SIGNAL_COLORS[stat.sig]}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </button>
              )
            })
          )}
        </div>

        {selectedStat ? (
          <div className="flex flex-col gap-4 rounded-xl border border-blue-100 bg-blue-50/20 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className={`h-3 w-3 rounded-full ${SIGNAL_COLORS[selectedStat.sig]}`} />
                  <h3 className="text-lg font-bold text-gray-900">{SIGNAL_LABELS[selectedStat.sig]}</h3>
                </div>
                {selectedStat.narrative && (
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-700">
                    {stripIds(selectedStat.narrative)}
                  </p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Evidence', value: String(selectedStat.sFacts.length), accent: '' },
                { label: 'SAFE', value: String(selectedStat.safeCount), accent: 'text-emerald-700' },
                {
                  label: 'Avg Conf',
                  value: selectedStat.avgConf !== null
                    ? `${(selectedStat.avgConf * 100).toFixed(0)}%` : '—',
                  accent: '',
                },
              ].map(item => (
                <div key={item.label} className="rounded-lg border border-gray-100 bg-white p-3 text-center">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">{item.label}</p>
                  <p className={`mt-1 text-xl font-bold tabular-nums ${item.accent || 'text-gray-900'}`}>
                    {item.value}
                  </p>
                </div>
              ))}
            </div>

            {signalTopFacts.length > 0 && (
              <div>
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
                  Top evidence for this signal
                </p>
                <div className="flex flex-col gap-2">
                  {signalTopFacts.map(fact => (
                    <div key={fact.fact_id} className="rounded-lg border border-gray-200 bg-white p-3">
                      <p className="text-sm font-semibold leading-snug text-gray-900">{fact.claim}</p>
                      <p className="mt-1.5 border-l-2 border-blue-200 pl-2.5 text-xs italic leading-relaxed text-gray-500">
                        "{fact.evidence_quote.length > 160
                          ? fact.evidence_quote.slice(0, 160) + '…'
                          : fact.evidence_quote}"
                      </p>
                      <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                        <span>{sourceDomain(fact.source_url)}</span>
                        <span className="text-gray-300">·</span>
                        <span className="font-medium text-gray-700">{(fact.confidence * 100).toFixed(0)}% conf</span>
                        {fact.safe_verified && (
                          <span className="flex items-center gap-0.5 rounded-full bg-emerald-50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                            <ShieldCheck className="h-2.5 w-2.5" /> SAFE
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-wrap items-center gap-2 border-t border-blue-100 pt-3">
              <Link
                to="/workspace/signals"
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50"
              >
                Open Signal Radar
              </Link>
              <Link
                to={`/workspace/evidence?signal=${selectedStat.sig}`}
                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50"
              >
                Review evidence for this signal
              </Link>
              <Link
                to={`/chat?context=signal&signal=${selectedStat.sig}`}
                className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
              >
                <MessageSquare className="h-3 w-3" /> Ask Chat
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-gray-200 bg-gray-50 p-8 text-center">
            <Activity className="mb-3 h-8 w-8 text-gray-300" />
            <p className="text-sm font-medium text-gray-500">Select a signal on the left</p>
            <p className="mt-1 text-xs text-gray-400">
              See narrative, evidence depth, SAFE count, and top facts.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}

// ─── Evidence Preview ─────────────────────────────────────────────────────────

function FactCard({ fact }: { fact: FactObject }) {
  return (
    <article className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
          {SIGNAL_LABELS[fact.signal_type]}
        </span>
        <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">
          {fact.entity}
        </span>
        {fact.safe_verified && (
          <span className="flex items-center gap-0.5 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
            <ShieldCheck className="h-3 w-3" /> SAFE
          </span>
        )}
        <div className="ml-auto flex items-center gap-1.5">
          <TierBadge tier={fact.source_tier} />
          <SentimentBadge sentiment={fact.sentiment} />
        </div>
      </div>

      <h3 className="text-sm font-bold leading-snug text-gray-950">{fact.claim}</h3>

      <blockquote className="border-l-2 border-blue-200 pl-3 text-sm italic leading-6 text-gray-600">
        "{fact.evidence_quote.length > 200
          ? fact.evidence_quote.slice(0, 200) + '…'
          : fact.evidence_quote}"
      </blockquote>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{sourceDomain(fact.source_url)} · {(fact.confidence * 100).toFixed(0)}% conf</span>
        <span>{formatDate(fact.published_date) || ''}</span>
      </div>

      <div className="flex items-center gap-2 border-t border-gray-100 pt-3">
        <a
          href={fact.source_url}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1 rounded-lg border border-gray-200 px-2.5 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50"
        >
          <ExternalLink className="h-3 w-3" /> Open source
        </a>
        <Link
          to={`/chat?context=fact&fact_id=${fact.fact_id}`}
          className="ml-auto flex items-center gap-1 rounded-lg bg-blue-600 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
        >
          <MessageSquare className="h-3 w-3" /> Ask Chat
        </Link>
      </div>
    </article>
  )
}

function EvidencePreview({
  facts,
  selectedSignal,
  factsLoading,
}: {
  facts: FactObject[]
  selectedSignal: SignalType | null
  factsLoading: boolean
}) {
  const preview = useMemo(() => {
    const base = selectedSignal
      ? facts.filter(f => f.signal_type === selectedSignal)
      : [...facts]
    return base.sort((a, b) => b.confidence - a.confidence).slice(0, 4)
  }, [facts, selectedSignal])

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Evidence Preview</p>
          <h2 className="mt-1 text-xl font-bold text-gray-950">
            {selectedSignal
              ? `Top facts · ${SIGNAL_LABELS[selectedSignal]}`
              : 'Highest-confidence facts'}
          </h2>
          {selectedSignal && (
            <p className="mt-1 text-xs text-gray-400">
              Filtered to {SIGNAL_LABELS[selectedSignal]} — select a different signal in the cockpit above to change.
            </p>
          )}
        </div>
        <Link
          to="/workspace/evidence"
          className="flex items-center gap-1 text-sm font-semibold text-blue-600 hover:text-blue-700"
        >
          Open Evidence Explorer <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      {factsLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map(i => (
            <div key={i} className="animate-pulse rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex gap-2">
                <div className="h-5 w-20 rounded-full bg-gray-200" />
                <div className="h-5 w-16 rounded-full bg-gray-200" />
              </div>
              <div className="mt-3 h-5 w-full rounded bg-gray-200" />
              <div className="mt-2 h-16 w-full rounded bg-gray-100" />
            </div>
          ))}
        </div>
      ) : preview.length === 0 ? (
        <div className="rounded-xl border border-gray-100 bg-gray-50 p-6 text-center">
          <p className="text-sm text-gray-500">
            {selectedSignal
              ? `No facts for ${SIGNAL_LABELS[selectedSignal]} in this report.`
              : 'No evidence facts loaded yet.'}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {preview.map(fact => (
            <FactCard key={fact.fact_id} fact={fact} />
          ))}
        </div>
      )}
    </section>
  )
}

// ─── Market Data Context ──────────────────────────────────────────────────────

function MarketDataContext({ report }: { report: MarketPulseReport }) {
  const rows = report.company_narratives.filter(
    n => n.price_current != null || n.price_change_7d_pct != null || n.signal_lead_days != null,
  )

  if (rows.length === 0) {
    return (
      <p className="text-center text-xs text-gray-400">
        Market data coverage is limited for this report — price context was not available at pipeline run time.{' '}
        <Link to="/workspace/companies" className="font-semibold text-blue-500 hover:text-blue-600">
          Open company lens →
        </Link>
      </p>
    )
  }

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-7 shadow-sm">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-600">Market Data Context</p>
          <h2 className="mt-1 text-xl font-bold text-gray-950">Price context</h2>
        </div>
        <Link to="/workspace/companies" className="text-sm font-semibold text-blue-600 hover:text-blue-700">
          Open company lens →
        </Link>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200">
              {['Company', 'Price', '7d change', 'Signal lead'].map(h => (
                <th key={h} className="pb-2 pr-4 text-left text-xs font-semibold uppercase tracking-wide text-gray-400">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(n => (
              <tr key={n.ticker} className="border-b border-gray-100 last:border-0">
                <td className="py-3 pr-4 text-sm font-semibold text-gray-900">{n.company} ({n.ticker})</td>
                <td className="py-3 pr-4 text-sm tabular-nums text-gray-700">
                  {n.price_current != null ? `$${n.price_current.toFixed(2)}` : 'Unavailable'}
                </td>
                <td className="py-3 pr-4 text-sm tabular-nums text-gray-700">
                  {n.price_change_7d_pct != null
                    ? `${n.price_change_7d_pct >= 0 ? '+' : ''}${n.price_change_7d_pct.toFixed(1)}%`
                    : 'Unavailable'}
                </td>
                <td className="py-3 text-sm text-gray-700">
                  {n.signal_lead_days != null ? `${n.signal_lead_days} days` : 'Unavailable'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ─── Main export ──────────────────────────────────────────────────────────────

export default function WorkspaceOverview({ report, facts, factsLoading = false }: WorkspaceOverviewProps) {
  const [selectedSignal, setSelectedSignal] = useState<SignalType | null>(null)

  // Compute signal stats at the top level so the initialisation effect can use them.
  // SignalCockpit also calls computeSignalStats internally; the computation is cheap
  // and both useMemos share the same deps so results are always in sync.
  const signalStats = useMemo(() => computeSignalStats(facts, report), [facts, report])

  // Auto-select the best default signal once stats are available.
  // Uses the functional updater to read the previous value without including
  // selectedSignal in the deps (which would cause re-runs on every user click).
  useEffect(() => {
    if (signalStats.length === 0) return
    setSelectedSignal(prev => {
      // Preserve a valid user selection that still exists in the new stat list.
      if (prev !== null && signalStats.some(s => s.sig === prev)) return prev
      // Prefer the first signal that has at least one evidence fact.
      const firstWithFacts = signalStats.find(s => s.sFacts.length > 0)
      return firstWithFacts?.sig ?? signalStats[0].sig
    })
  }, [signalStats])

  // Clicking a signal always selects it.  No toggle-off: the detail panel
  // should never be blank once signals are available.
  function handleSignalSelect(sig: SignalType) {
    setSelectedSignal(sig)
  }

  return (
    <div className="flex flex-col gap-7">
      {/* 1. Morning brief */}
      <BriefPanel report={report} />

      {/* 2. Watch list — infinite horizontal marquee */}
      <WatchItemMarquee items={report.market_narrative.watch_list ?? []} />

      {/* 3. Risk alerts — infinite horizontal marquee */}
      <RiskAlertMarquee contradictions={report.contradictions ?? []} />

      {/* 4. Interactive Signal Cockpit */}
      <SignalCockpit
        report={report}
        facts={facts}
        factsLoading={factsLoading}
        selectedSignal={selectedSignal}
        onSelectSignal={handleSignalSelect}
      />

      {/* 5. Evidence Preview — responds to selected signal */}
      <EvidencePreview
        facts={facts}
        selectedSignal={selectedSignal}
        factsLoading={factsLoading}
      />

      {/* 6. Market Data Context — table if data, muted note if not */}
      <MarketDataContext report={report} />
    </div>
  )
}
