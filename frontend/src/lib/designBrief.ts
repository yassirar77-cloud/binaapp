/**
 * Senior Designer mode — client-side helpers for the create page.
 *
 * The merchant can hand the AI designer a free-text DESIGN BRIEF ("gelap &
 * mewah, aksen emas, ala hotel butik") and pick how much freedom the AI
 * gets. Both travel to the backend as `design_brief` / `design_freedom`
 * (see backend/app/services/design_director.py for what they do there).
 *
 * The example chips are written in the merchant's language but the text
 * they insert is kept short and concrete, because the backend forwards it
 * verbatim to the model as the highest-priority design input.
 */

export const DESIGN_BRIEF_MAX = 1500;

export type DesignFreedom = 'designer' | 'guided';

export interface FreedomOption {
  key: DesignFreedom;
  label: string;
  hint: string;
}

export const FREEDOM_OPTIONS: readonly FreedomOption[] = [
  {
    key: 'designer',
    label: 'Designer bebas',
    hint: 'AI reka concept sendiri · disyorkan',
  },
  {
    key: 'guided',
    label: 'Ikut sistem',
    hint: 'Layout & warna standard BinaApp',
  },
] as const;

export interface BriefExample {
  /** Stable id used for keys + tests. */
  id: string;
  /** Short chip label in the UI. */
  label: string;
  /** Sentence inserted into the brief textarea. */
  text: string;
}

export const BRIEF_EXAMPLES: Record<'ms' | 'en', readonly BriefExample[]> = {
  ms: [
    { id: 'dark-luxe', label: 'Gelap & mewah', text: 'Gelap dan mewah, satu aksen emas, ala hotel butik.' },
    { id: 'editorial', label: 'Ala majalah', text: 'Gaya majalah editorial: heading serif besar, banyak ruang putih, gambar bleed penuh.' },
    { id: 'pastel-fun', label: 'Ceria pastel', text: 'Ceria dengan warna pastel, bentuk bulat, banyak gambar, mesra keluarga.' },
    { id: 'minimal-one', label: 'Minimal satu warna', text: 'Minimal putih bersih, satu warna sahaja untuk butang, tiada hiasan.' },
    { id: 'retro-kopitiam', label: 'Retro kopitiam', text: 'Retro kopitiam 80-an: hijau tua & krim, jubin, tipografi vintage.' },
    { id: 'bold-street', label: 'Berani street', text: 'Berani dan street: heading gergasi huruf besar, kontras tinggi, warna terang.' },
  ],
  en: [
    { id: 'dark-luxe', label: 'Dark & luxe', text: 'Dark and luxurious, a single gold accent, boutique-hotel feel.' },
    { id: 'editorial', label: 'Editorial', text: 'Editorial magazine style: large serif headings, generous white space, full-bleed photos.' },
    { id: 'pastel-fun', label: 'Playful pastel', text: 'Playful pastel colours, rounded shapes, lots of photos, family friendly.' },
    { id: 'minimal-one', label: 'Minimal one colour', text: 'Clean minimal white, one colour only for buttons, no decoration.' },
    { id: 'retro-kopitiam', label: 'Retro kopitiam', text: '80s retro kopitiam: dark green and cream, tiles, vintage typography.' },
    { id: 'bold-street', label: 'Bold street', text: 'Bold and street: giant uppercase headings, high contrast, bright colour.' },
  ],
};

/**
 * Trim, collapse runs of spaces, cap at DESIGN_BRIEF_MAX. Returns undefined
 * for an empty brief so it can be spread straight into a JSON payload
 * (undefined keys are dropped by JSON.stringify).
 */
export function normalizeDesignBrief(raw: string | null | undefined): string | undefined {
  if (!raw) return undefined;
  const text = raw
    .replace(/[ \t\r\f\v]+/g, ' ')
    .replace(/ *\n */g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  if (!text) return undefined;
  return text.slice(0, DESIGN_BRIEF_MAX).trimEnd();
}

/**
 * Append an example sentence to the current brief. Idempotent: an example
 * already present is not added twice. Keeps the result within the cap.
 */
export function appendBriefExample(current: string, example: string): string {
  const base = (current || '').trimEnd();
  const addition = example.trim();
  if (!addition) return base;
  if (base.toLowerCase().includes(addition.toLowerCase())) return base;
  const joined = base ? `${base}${/[.!?]$/.test(base) ? '' : '.'} ${addition}` : addition;
  return joined.slice(0, DESIGN_BRIEF_MAX);
}

export function isDesignFreedom(value: unknown): value is DesignFreedom {
  return value === 'designer' || value === 'guided';
}

export interface DesignPayloadInput {
  designBrief?: string | null;
  designFreedom?: string | null;
  designStyle?: string | null;
}

export interface DesignPayload {
  design_brief?: string;
  design_freedom: DesignFreedom;
  design_style?: string;
}

/** The design-related keys of the generate/regenerate request body. */
export function buildDesignPayload(input: DesignPayloadInput): DesignPayload {
  const payload: DesignPayload = {
    design_freedom: isDesignFreedom(input.designFreedom) ? input.designFreedom : 'designer',
  };
  const brief = normalizeDesignBrief(input.designBrief);
  if (brief) payload.design_brief = brief;
  if (input.designStyle) payload.design_style = input.designStyle;
  return payload;
}

/** Human label for the summary panel. */
export function freedomLabel(value: string | null | undefined): string {
  const option = FREEDOM_OPTIONS.find((o) => o.key === value);
  return option ? option.label : FREEDOM_OPTIONS[0].label;
}
