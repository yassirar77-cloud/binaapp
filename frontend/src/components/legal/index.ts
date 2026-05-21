/**
 * Barrel exports for the legal-document component library.
 *
 * Routes in Step 3f import from `@/components/legal` (this file) rather
 * than reaching into each individual component file — keeps the route
 * pages tidy and gives this module a stable public surface area.
 *
 * The TOCItem type is exported because LegalTOC accepts an array of
 * them; route pages need to build that array from a doc's
 * `sections[]` plus a "Ringkasan" / "Pengenalan" / "Changelog" anchor
 * for the non-numbered sections.
 */

export { LegalDocument } from './LegalDocument';
export { LegalSection } from './LegalSection';
export { LegalMarkdown } from './LegalMarkdown';
export { LegalMetadata } from './LegalMetadata';

export { LegalAIVendorTable } from './LegalAIVendorTable';
export { LegalRetentionTable } from './LegalRetentionTable';
export { LegalTierTable } from './LegalTierTable';
export { LegalAddonTable } from './LegalAddonTable';
export { LegalQuotaTable } from './LegalQuotaTable';
export { LegalThirdPartyTable } from './LegalThirdPartyTable';

export { LegalChangelog } from './LegalChangelog';
export { LegalTOC } from './LegalTOC';
export type { TOCItem } from './LegalTOC';
export { LegalLanguageToggle } from './LegalLanguageToggle';
