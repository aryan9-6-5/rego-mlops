# DESIGN.md — Design System & Visual Language
# Project Rego — Continuous Regulatory Compliance Reasoning
# Version: 1.0 | Status: FINALIZED
# ============================================================
# READ THIS BEFORE: writing any UI component, choosing any color,
# setting any spacing, or making any layout decision.
# Every visual choice in Rego flows from one source of truth: this file.
# ============================================================

## 1. Design Philosophy

**Rego is infrastructure that banks use to stay out of jail.**

The design language reflects that weight. No gradients. No rounded-everything. No playful illustrations. Rego looks like the tool it is — a compliance operations platform where every number matters and every status has legal consequence.

**Inspiration triptych:**
- **Bloomberg Terminal** — information density without chaos, monospaced trust
- **Linear** — speed, precision, zero decoration, every interaction earns its place
- **Palantir Gotham** — dark command-center feel for the ML engineer interface

**Two interfaces, two emotional registers:**

| Interface | Feel | Analogy |
|-----------|------|---------|
| Compliance Officer | Calm authority. Clean. Readable. Never intimidating. | A well-designed legal document viewer |
| ML Engineer | Dense. Technical. Fast. Real-time. | A deployment dashboard for a payment processor |
> Status must never be ambiguous. COMPLIANT and NON-COMPLIANT must be unmistakable at a glance — across both interfaces, in any lighting condition, for any user.

---

## 2. Color System

### Design Decision: Light-first, both interfaces
Both interfaces default to light mode. Light theme was chosen deliberately — Rego operates in formal compliance and legal contexts where document-like readability and institutional trust matter more than terminal aesthetics. Dark mode remains available as user preference via `[data-theme="dark"]` tokens, but neither interface applies it by default. The ML Engineer interface uses light mode with higher information density, not a dark theme.

```css
:root {
  /* ─────────────────────────────────────────
     PRIMARY — Rego Indigo
     Chosen rationale: Indigo sits between blue (trust/financial) and
     purple (intelligence/AI). Not the generic SaaS blue. More serious.
  ───────────────────────────────────────── */
  --color-primary-50:  #EEF2FF;
  --color-primary-100: #E0E7FF;
  --color-primary-200: #C7D2FE;
  --color-primary-300: #A5B4FC;
  --color-primary-400: #818CF8;
  --color-primary-500: #6366F1;   /* Primary action */
  --color-primary-600: #4F46E5;   /* Primary hover */
  --color-primary-700: #4338CA;   /* Primary active */
  --color-primary-800: #3730A3;
  --color-primary-900: #312E81;

  /* ─────────────────────────────────────────
     COMPLIANCE STATUS — the most important colors in the product
     These must be immediately legible. No ambiguity. Ever.
  ───────────────────────────────────────── */
  --color-compliant:        #10B981;   /* Emerald — COMPLIANT */
  --color-compliant-bg:     #ECFDF5;
  --color-compliant-border: #6EE7B7;
  --color-compliant-text:   #065F46;

  --color-violation:        #EF4444;   /* Red — VIOLATION / BLOCKED */
  --color-violation-bg:     #FEF2F2;
  --color-violation-border: #FECACA;
  --color-violation-text:   #991B1B;

  --color-pending:          #F59E0B;   /* Amber — PENDING / AWAITING APPROVAL */
  --color-pending-bg:       #FFFBEB;
  --color-pending-border:   #FDE68A;
  --color-pending-text:     #92400E;

  --color-running:          #3B82F6;   /* Blue — RUNNING / IN PROGRESS */
  --color-running-bg:       #EFF6FF;
  --color-running-border:   #BFDBFE;
  --color-running-text:     #1E40AF;

  /* ─────────────────────────────────────────
     NEUTRALS — Light mode base
  ───────────────────────────────────────── */
  --color-neutral-0:   #FFFFFF;
  --color-neutral-50:  #F9FAFB;
  --color-neutral-100: #F3F4F6;
  --color-neutral-200: #E5E7EB;
  --color-neutral-300: #D1D5DB;
  --color-neutral-400: #9CA3AF;
  --color-neutral-500: #6B7280;
  --color-neutral-600: #4B5563;
  --color-neutral-700: #374151;
  --color-neutral-800: #1F2937;
  --color-neutral-900: #111827;
  --color-neutral-950: #030712;

  /* ─────────────────────────────────────────
     SEMANTIC — Standard states
  ───────────────────────────────────────── */
  --color-success:  #10B981;
  --color-warning:  #F59E0B;
  --color-error:    #EF4444;
  --color-info:     #3B82F6;

  /* ─────────────────────────────────────────
     SURFACE LEVELS — Light mode
  ───────────────────────────────────────── */
  --surface-page:       #F9FAFB;   /* Page background */
  --surface-card:       #FFFFFF;   /* Card / panel */
  --surface-raised:     #FFFFFF;   /* Modal / dropdown */
  --surface-sunken:     #F3F4F6;   /* Input background, code blocks */
  --surface-overlay:    rgba(17, 24, 39, 0.5);

  /* ─────────────────────────────────────────
     TEXT LEVELS — Light mode
  ───────────────────────────────────────── */
  --text-primary:   #111827;
  --text-secondary: #4B5563;
  --text-tertiary:  #9CA3AF;
  --text-disabled:  #D1D5DB;
  --text-inverse:   #FFFFFF;
  --text-code:      #4338CA;   /* Indigo — for rule IDs, version strings */

  /* ─────────────────────────────────────────
     BORDER LEVELS — Light mode
  ───────────────────────────────────────── */
  --border-subtle:   #F3F4F6;
  --border-default:  #E5E7EB;
  --border-strong:   #D1D5DB;
  --border-focus:    #6366F1;   /* Primary indigo on focus */

  /* ─────────────────────────────────────────
     Z3 PROOF SPECIFIC — for certificate display
  ───────────────────────────────────────── */
  --color-proof-hash:    #4338CA;   /* Indigo — proof hash strings */
  --color-proof-bg:      #EEF2FF;   /* Light indigo — certificate background */
  --color-proof-border:  #A5B4FC;
  --color-rule-id:       #0F172A;   /* Near-black — rule identifiers */
  --font-mono:           'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
}

/* ─────────────────────────────────────────
   DARK MODE — optional user preference override
   NOT applied by default on any interface.
   Apply via: <html data-theme="dark"> only when
   user explicitly toggles dark mode preference.
───────────────────────────────────────── */
[data-theme="dark"] {
  --surface-page:       #0F1117;   /* Near-black — Bloomberg-dark */
  --surface-card:       #161B27;   /* Slightly lighter */
  --surface-raised:     #1E2433;   /* Modal / dropdown */
  --surface-sunken:     #0A0E16;   /* Input background */
  --surface-overlay:    rgba(0, 0, 0, 0.7);

  --text-primary:   #F1F5F9;
  --text-secondary: #94A3B8;
  --text-tertiary:  #64748B;
  --text-disabled:  #334155;
  --text-inverse:   #0F172A;
  --text-code:      #818CF8;   /* Brighter indigo on dark */

  --border-subtle:   #1E2433;
  --border-default:  #263044;
  --border-strong:   #374151;
  --border-focus:    #818CF8;

  /* Compliance status — same hue, adjusted for dark legibility */
  --color-compliant-bg:     #022C22;
  --color-compliant-border: #065F46;
  --color-compliant-text:   #6EE7B7;

  --color-violation-bg:     #2D0A0A;
  --color-violation-border: #991B1B;
  --color-violation-text:   #FCA5A5;

  --color-pending-bg:       #2D1B00;
  --color-pending-border:   #92400E;
  --color-pending-text:     #FDE68A;

  --color-running-bg:       #0C1A3A;
  --color-running-border:   #1E40AF;
  --color-running-text:     #93C5FD;

  --color-proof-bg:      #1A1F3A;
  --color-proof-border:  #4338CA;
  --color-proof-hash:    #A5B4FC;
}
```

### Tailwind config extension
```js
// tailwind.config.ts
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#EEF2FF', 100: '#E0E7FF', 200: '#C7D2FE',
          300: '#A5B4FC', 400: '#818CF8', 500: '#6366F1',
          600: '#4F46E5', 700: '#4338CA', 800: '#3730A3', 900: '#312E81',
        },
        compliant:  '#10B981',
        violation:  '#EF4444',
        pending:    '#F59E0B',
        running:    '#3B82F6',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
}
```

---

## 3. Typography Scale

**Font decisions:**
- **Inter** — UI text. Clean, neutral, designed for screens. Not a hot take, but the right choice for compliance infrastructure.
- **JetBrains Mono** — All code: rule IDs, proof hashes, Z3 output, model versions, regulation version strings. Monospace is trust for technical content.
- Never use a display font. This is not a marketing site.

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
```

| Role | Font | Weight | Size | Line Height | Usage |
|------|------|--------|------|-------------|-------|
| `display` | Inter | 600 | 28px / 1.75rem | 1.2 | Page titles only |
| `heading-lg` | Inter | 600 | 20px / 1.25rem | 1.3 | Section headers |
| `heading-md` | Inter | 600 | 16px / 1rem | 1.4 | Card titles |
| `heading-sm` | Inter | 500 | 14px / 0.875rem | 1.4 | Subsection labels |
| `body-lg` | Inter | 400 | 16px / 1rem | 1.6 | CO interface body text, descriptions |
| `body-md` | Inter | 400 | 14px / 0.875rem | 1.5 | Standard UI text |
| `body-sm` | Inter | 400 | 13px / 0.8125rem | 1.5 | Helper text, captions |
| `label` | Inter | 500 | 12px / 0.75rem | 1.4 | Form labels, table headers |
| `code-md` | JetBrains Mono | 400 | 13px / 0.8125rem | 1.6 | Rule IDs, proof hashes |
| `code-sm` | JetBrains Mono | 400 | 12px / 0.75rem | 1.5 | Version strings, model IDs |

**CO interface:** Use `body-lg` as the base — slightly larger, more breathing room, less dense.
**MLE interface:** Use `body-md` as the base — dense, more information per viewport.

---

## 4. Spacing Scale

**Base unit: 4px.** Every spacing value is a multiple of 4.

```css
/* Spacing tokens */
--space-0:   0px;
--space-1:   4px;    /* Tight: icon padding, badge inner */
--space-2:   8px;    /* Compact: input padding, tag gap */
--space-3:   12px;   /* Default: button padding-y, list gap */
--space-4:   16px;   /* Standard: card padding-x, section gap */
--space-5:   20px;   /* Comfortable: form field gap */
--space-6:   24px;   /* Generous: card padding, panel gap */
--space-8:   32px;   /* Section break */
--space-10:  40px;   /* Large break */
--space-12:  48px;   /* Page section gap */
--space-16:  64px;   /* Hero/major section gap */
```

**Interface density:**

| Token | CO Interface | MLE Interface |
|-------|-------------|---------------|
| Card padding | `--space-6` (24px) | `--space-4` (16px) |
| Row height (table) | 52px | 40px |
| Section gap | `--space-12` (48px) | `--space-8` (32px) |
| Sidebar width | — | 240px |

---

## 5. Border, Radius & Shadow Tokens

```css
/* Border radius — deliberately restrained */
--radius-sm:   4px;    /* Tags, badges, code blocks */
--radius-md:   6px;    /* Buttons, inputs */
--radius-lg:   8px;    /* Cards, panels */
--radius-xl:   12px;   /* Modals, bottom sheets */
--radius-full: 9999px; /* Pills only — for status badges */

/* Shadows — flat with purposeful elevation */
--shadow-none:   none;
--shadow-sm:     0 1px 2px 0 rgba(0,0,0,0.05);
--shadow-md:     0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
--shadow-lg:     0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.05);
--shadow-focus:  0 0 0 3px rgba(99,102,241,0.25);  /* Indigo focus ring */

/* Dark mode shadows — near-invisible, use borders instead */
[data-theme="dark"] {
  --shadow-sm: 0 1px 2px 0 rgba(0,0,0,0.3);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.5);
}
```

**Shadow philosophy:** Cards use `shadow-sm` + `border-default`. Modals use `shadow-lg`. In dark mode, prefer `border-strong` over shadows — shadows disappear on dark backgrounds.

---

## 6. Component Patterns

### Compliance Status Badge — THE most important component in Rego

```tsx
// Always use this exact pattern. Never improvise compliance status display.
// This component appears on every dashboard view.

type ComplianceStatus = 'compliant' | 'violation' | 'pending' | 'running'

const statusConfig = {
  compliant: {
    label: 'Compliant',
    bg: 'bg-emerald-50 dark:bg-emerald-950',
    text: 'text-emerald-700 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
    dot: 'bg-emerald-500',
  },
  violation: {
    label: 'Violation',
    bg: 'bg-red-50 dark:bg-red-950',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-red-200 dark:border-red-800',
    dot: 'bg-red-500 animate-pulse',   // Pulse on violation — urgent
  },
  pending: {
    label: 'Pending Approval',
    bg: 'bg-amber-50 dark:bg-amber-950',
    text: 'text-amber-700 dark:text-amber-300',
    border: 'border-amber-200 dark:border-amber-800',
    dot: 'bg-amber-500',
  },
  running: {
    label: 'Running',
    bg: 'bg-blue-50 dark:bg-blue-950',
    text: 'text-blue-700 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800',
    dot: 'bg-blue-500 animate-pulse',
  },
}

// <StatusBadge status="compliant" />
// <StatusBadge status="violation" size="lg" />
```

### Buttons

```tsx
// Primary — one action per screen
className="bg-primary-600 hover:bg-primary-700 active:bg-primary-800
           text-white font-medium text-sm
           px-4 py-2 rounded-md
           transition-colors duration-150
           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
           disabled:opacity-50 disabled:cursor-not-allowed"

// Secondary — supporting actions
className="bg-white hover:bg-neutral-50 active:bg-neutral-100
           text-neutral-700 font-medium text-sm
           border border-neutral-300
           px-4 py-2 rounded-md
           transition-colors duration-150
           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"

// Danger — destructive or block actions
className="bg-red-600 hover:bg-red-700
           text-white font-medium text-sm
           px-4 py-2 rounded-md
           transition-colors duration-150"

// Ghost — low-emphasis
className="text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100
           font-medium text-sm
           px-3 py-2 rounded-md
           transition-colors duration-150"

// Approve (CO interface only) — deliberate green
className="bg-emerald-600 hover:bg-emerald-700
           text-white font-medium text-sm
           px-4 py-2 rounded-md
           transition-colors duration-150"

// Reject (CO interface only) — deliberate red
className="bg-red-50 hover:bg-red-100
           text-red-700 font-medium text-sm
           border border-red-200
           px-4 py-2 rounded-md
           transition-colors duration-150"
```

### Inputs

```tsx
// Default state
className="w-full bg-neutral-50 border border-neutral-300 rounded-md
           px-3 py-2 text-sm text-neutral-900
           placeholder:text-neutral-400
           focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
           transition-shadow duration-150"

// Error state — add
className="... border-red-500 focus:ring-red-500"
// + <p className="mt-1 text-xs text-red-600">{error}</p>

// Regulation text area (CO interface — larger, drag-drop target)
className="w-full min-h-[200px] bg-neutral-50 border-2 border-dashed border-neutral-300
           rounded-lg p-4 text-sm text-neutral-700
           focus:border-primary-500 focus:ring-0
           transition-colors duration-150
           font-mono"  // Monospace — regulatory text is formal
```

### Cards

```tsx
// Standard card
className="bg-white border border-neutral-200 rounded-lg shadow-sm p-6"

// Dark mode card (MLE)
className="bg-[#161B27] border border-[#263044] rounded-lg p-4"

// Proof certificate card — distinctive
className="bg-indigo-50 border border-indigo-200 rounded-lg p-6
           dark:bg-[#1A1F3A] dark:border-indigo-800"

// Pipeline gate row (MLE interface)
className="flex items-center justify-between
           px-4 py-3
           border-b border-neutral-100 dark:border-[#1E2433]
           hover:bg-neutral-50 dark:hover:bg-[#1E2433]
           transition-colors duration-100"
```

### Rule ID & Proof Hash Display

```tsx
// Rule ID — monospace, distinctive
<code className="font-mono text-xs text-indigo-700 bg-indigo-50
                 px-1.5 py-0.5 rounded
                 dark:text-indigo-300 dark:bg-indigo-950">
  RBI-MD-2022-§4.1.c
</code>

// Proof hash — monospace, truncated with copy button
<div className="font-mono text-xs text-neutral-500 truncate max-w-[200px]"
     title={fullHash}>
  z3:sha256:a1b2c3d4...
</div>
```

---

## 7. Motion Tokens

```css
/* Duration */
--duration-instant:  100ms;   /* Hover state changes */
--duration-fast:     150ms;   /* Button clicks, badge updates */
--duration-standard: 200ms;   /* Panel opens, status transitions */
--duration-slow:     300ms;   /* Modal enter, page transitions */

/* Easing */
--ease-standard: cubic-bezier(0.4, 0, 0.2, 1);   /* Material standard */
--ease-decel:    cubic-bezier(0, 0, 0.2, 1);      /* Elements entering */
--ease-accel:    cubic-bezier(0.4, 0, 1, 1);      /* Elements leaving */
```

**Animation rules:**
- Compliance status changes: always animate. A badge flipping from COMPLIANT → VIOLATION should be unmissable. Use a 300ms cross-fade + scale(1.05) pulse.
- Pipeline gate transitions: slide-in from left as each gate completes
- Violation pulse: `animate-pulse` on red dot — draws the eye to what needs attention
- No page transition animations — this is a dashboard, not a marketing site
- Reduce motion: always wrap animations in `@media (prefers-reduced-motion: no-preference)`

```css
/* Compliance status transition — the only "hero" animation in Rego */
.status-badge {
  transition: background-color var(--duration-slow) var(--ease-standard),
              color var(--duration-slow) var(--ease-standard),
              border-color var(--duration-slow) var(--ease-standard);
}

@keyframes violation-alert {
  0%   { transform: scale(1); }
  50%  { transform: scale(1.04); }
  100% { transform: scale(1); }
}

.status-badge--violation {
  animation: violation-alert 0.4s var(--ease-standard);
}
```

---

## 8. Key Screen Layout Notes

### CO Interface — Dashboard (primary screen)
```
┌─────────────────────────────────────────────────────────────┐
│  Header: Rego logo | "Compliance Officer" role pill | Auth  │
├─────────────────────────────────────────────────────────────┤
│  Hero status bar: [COMPLIANT] [Model v2.1.4] [RBI-MD-2022] │
│  — Full-width, color-coded, unmissable. First thing seen.  │
├──────────────────┬──────────────────────────────────────────┤
│  Active Rules    │  Pending Approvals                       │
│  (list of rules  │  (LLM translations awaiting             │
│   currently      │   human review — approve/reject)        │
│   enforced)      │                                         │
├──────────────────┴──────────────────────────────────────────┤
│  Recent Certificates (table: date, model ver, reg ver, DL) │
└─────────────────────────────────────────────────────────────┘
```
Layout notes: Max content width 1200px, centered. 3-column grid on wide screens, stacks to 1-col on tablet. Font base: `body-lg`. No sidebar — CO interface is full-bleed.

### CO Interface — Regulation Upload & Human Validation Workflow

**SLA:** CO must be able to review and approve a rule in under 3 minutes from paste to active.
**Cognitive load principle:** CO sees one decision at a time. Never multiple rules pending simultaneously on the same screen.

```
SCREEN 1 — Paste Regulation
┌─────────────────────────────────────────────────────────────┐
│  "Add New Regulation"                        [← Back]       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Paste regulatory text here, or drag a PDF...        │   │
│  │                                                     │   │
│  │ (monospace, 200px min, dashed border, 2px)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Source reference (optional): [__________________]         │
│  e.g. "RBI Master Direction §4.1, Aug 2022"                │
│                                                             │
│  [Extract Rule →]  ← primary button, disabled if empty     │
└─────────────────────────────────────────────────────────────┘

SCREEN 2 — LLM Processing (shown while OpenRouter + Z3 run)
┌─────────────────────────────────────────────────────────────┐
│  Extracting rule...                                         │
│  ● Sending to AI for interpretation        [2s elapsed]     │
│  ○ Checking logical structure (Z3)                          │
│  ○ Calculating confidence score                             │
│                                                             │
│  This usually takes 10–30 seconds.                         │
└─────────────────────────────────────────────────────────────┘

SCREEN 3A — Validation Result: HIGH/MEDIUM CONFIDENCE
┌─────────────────────────────────────────────────────────────┐
│  Rule extracted — please review                             │
│                                              [confidence]   │
│  ┌──────────────────────────┬──────────────────────────┐   │
│  │  YOUR REGULATION TEXT    │  EXTRACTED RULE          │   │
│  │  ─────────────────────   │  ─────────────────────   │   │
│  │  "...shall not use       │  pin_code_weight == 0    │   │
│  │  geographic proxies      │                          │   │
│  │  such as PIN codes..."   │  Confidence: 82%  ●●●○   │   │
│  │                          │  [High — safe to review] │   │
│  └──────────────────────────┴──────────────────────────┘   │
│                                                             │
│  What this rule means in plain English:                    │
│  "The loan model cannot assign any positive weight to      │
│   PIN code or postal code as a feature."                   │
│                                                             │
│  Z3 structure check: ✓ Valid formula                       │
│                                                             │
│  Does this correctly capture the regulation's intent?      │
│                                                             │
│  [✓ Yes — Approve Rule]    [✗ No — Reject & Re-extract]   │
│   ← 48px height, green     ← 48px height, outlined red    │
└─────────────────────────────────────────────────────────────┘

SCREEN 3B — Validation Result: LOW CONFIDENCE (<50%)
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  Low confidence extraction — manual review required     │
│                                                             │
│  ┌──────────────────────────┬──────────────────────────┐   │
│  │  YOUR REGULATION TEXT    │  EXTRACTED RULE          │   │
│  │                          │  x1 > 0 AND x2 == 0      │   │
│  │                          │                          │   │
│  │                          │  Confidence: 31%  ●○○○   │   │
│  │                          │  [Low — review carefully]│   │
│  └──────────────────────────┴──────────────────────────┘   │
│                                                             │
│  ⚠️  The extracted rule uses generic variable names (x1,    │
│     x2) instead of meaningful terms. This often means      │
│     the AI did not correctly identify the regulated         │
│     feature. Consider re-pasting with more specific text.  │
│                                                             │
│  [Try Again — Paste More Specific Text]                    │
│  [I Understand — Review Anyway]  ← extra friction          │
└─────────────────────────────────────────────────────────────┘

SCREEN 3C — Z3 Structural Rejection
┌─────────────────────────────────────────────────────────────┐
│  ✗ Rule could not be verified — extraction failed           │
│                                                             │
│  The extracted formula contains a logical error:            │
│  "Formula is not well-formed: unexpected token 'AND'"       │
│                                                             │
│  This is an AI extraction error, not a problem with         │
│  your regulation text. Please try again.                    │
│                                                             │
│  [Try Again]                                               │
└─────────────────────────────────────────────────────────────┘

SCREEN 4 — Approval Confirmation (second deliberate action)
┌─────────────────────────────────────────────────────────────┐
│  Confirm rule activation                                    │
├─────────────────────────────────────────────────────────────┤
│  Rule:   pin_code_weight == 0                               │
│  Source: RBI Master Direction §4.1                          │
│  Effect: All future model deployments must satisfy          │
│          this constraint or deployment will be BLOCKED.     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Type "ACTIVATE" to confirm:  [___________]          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Activate Rule]  ← enabled only when "ACTIVATE" typed     │
└─────────────────────────────────────────────────────────────┘
```

**Layout notes:** Single-column, max-width 720px, centered. Each screen is a separate route — browser back button works between screens. The two-pane layout (regulation text LEFT, extracted rule RIGHT) is non-negotiable — CO must see both simultaneously to validate semantic intent. Confidence badge uses the 4-dot indicator (●●●○ = 3/4 = 75%) not a percentage alone — percentage without context is meaningless to a non-technical user. Screen 4 requires typing "ACTIVATE" — this is maximum friction on an irreversible action that blocks future deployments.

**The confidence badge component:**
```tsx
// Confidence displayed as filled dots — not raw percentage
// 0–25%:  ○○○○  red    "Low"
// 25–50%: ●○○○  amber  "Low — review carefully"
// 50–75%: ●●○○  amber  "Medium"
// 75–90%: ●●●○  green  "High — safe to review"
// 90%+:   ●●●●  green  "Very High"
```



### MLE Interface — Pipeline Monitor (primary screen)
```
┌──────────────┬──────────────────────────────────────────────┐
│  Sidebar     │  Pipeline Status                             │
│  (240px)     │  ─────────────────────────────────────      │
│  > Dashboard │  [Ingestion ✓] [CT ✓] [CI ●] [CD —]       │
│  > Pipeline  │  Current gate: Symbolic Check               │
│  > Models    │  Z3 running against 12 active rules...     │
│  > Rules     ├──────────────────────────────────────────────┤
│  > Certs     │  Gate Details (expandable rows)             │
│              │  ✓ Performance regression    12ms           │
│              │  ✓ Fairness check            passed         │
│              │  ● Symbolic check            running        │
│              │  — RegAttack                 queued         │
└──────────────┴──────────────────────────────────────────────┘
```
Layout notes: Full-width, light mode, higher density than CO interface. Fixed sidebar 240px. Main area dense data table. Font base: `body-md`. Monospace for all technical values (timings, hashes, version strings).

### MLE Interface — Violation Report
- Full-width code-block style display for Z3 counterexample
- Rule ID in indigo monospace, prominently
- Plain English explanation directly below technical output
- "Which regulation?" linked to the specific RBI circular section

### Proof Certificate View (shared — both interfaces)
- Card with indigo background (`--color-proof-bg`)
- Model version + regulation version prominently at top
- Z3 proof hash in monospace, full display with copy button
- Download PDF + Copy Hash as the two CTAs
- Timestamp + "Verified by Z3 SMT Solver" as footer

---

## 9. Do Not Guidelines

These are the design anti-patterns for Rego specifically. Violating these breaks the trust aesthetic.

| ❌ Never do this | ✅ Do this instead |
|-----------------|------------------|
| Gradient buttons or gradient backgrounds | Flat color fills, solid borders |
| Rounded-everything (`rounded-full` on cards) | `rounded-lg` max on cards, `rounded-md` on buttons |
| Fun / playful illustrations or icons (Lottie animations, mascots) | Simple, functional iconography (Heroicons or Radix Icons) |
| Vague status indicators (orange dot with no label) | Explicit labeled status badges with both color AND text |
| Showing technical Z3 output to compliance officers | Always translate Z3 output to plain English before display in CO interface |
| Using the same density for both interfaces | CO = spacious, MLE = dense. Never apply MLE density to CO |
| Color as the ONLY compliance differentiator | Always use color + text + icon — never color alone (accessibility) |
| Auto-deploying visual feedback (toast only) | For compliance actions: inline confirmation + summary panel |
| Modal-heavy flows for approval | CO approval is inline — approve/reject in the same card, no modal |
| Blue as the primary action color | Indigo — trust without being generic bank-blue |
| Hiding the regulation version from any view | Regulation version is always visible wherever model version is visible |
| Custom scrollbars, custom cursors | Default browser behavior — this is a tool, not an experience |
| Any dark pattern near the "approve regulation" action | Max friction on approve: label, rule preview, confirm step |
