
import type { ProductDocumentLibraryEntry } from '@/lib/product-api';

export const WORKFLOW_RECOMMENDED_DOCUMENTS = {
  documentReview: ['Master Service Agreement v4.2.pdf', 'Master Service Agreement v4.3.pdf'],
  policyComparison: ['Information Security Policy v3.1.pdf', 'Information Security Policy v3.2.pdf'],
  actionPlan: [
    'Governance Committee Minutes and Action Items.pdf',
    'Internal Audit Checklist - Vendor Controls.pdf',
    'Nonconformance Report - Vendor Access Review.pdf',
    'Remediation Closure Note - Vendor Access Review.pdf',
  ],
  candidateReview: ['Sarah Chen - Senior ML Engineer CV.pdf', 'Senior ML Engineer Role Brief.pdf'],
} as const;

export const ACTION_PLAN_DOCUMENT_LIMIT = 4;

const TOKEN_STOPWORDS = new Set(['and', 'the', 'a', 'an', 'of', 'for']);

function stripExtension(value: string): string {
  return value.replace(/\.(pdf|doc|docx|txt|md)$/i, '');
}

export function normalizeDemoDocumentName(value: string): string {
  return stripExtension(value)
    .toLowerCase()
    .replace(/[_–—-]+/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokensFor(value: string): string[] {
  return normalizeDemoDocumentName(value)
    .split(' ')
    .filter((token) => token.length > 1 && !TOKEN_STOPWORDS.has(token));
}

function isRecommendedNameMatch(documentName: string, recommendedName: string): boolean {
  const normalizedDocument = normalizeDemoDocumentName(documentName);
  const normalizedRecommended = normalizeDemoDocumentName(recommendedName);
  if (!normalizedDocument || !normalizedRecommended) return false;
  if (normalizedDocument === normalizedRecommended) return true;
  if (normalizedDocument.includes(normalizedRecommended) || normalizedRecommended.includes(normalizedDocument)) return true;

  const documentTokens = new Set(tokensFor(documentName));
  const recommendedTokens = tokensFor(recommendedName);
  return recommendedTokens.length > 0 && recommendedTokens.every((token) => documentTokens.has(token));
}

export function findRecommendedDocument(
  documents: ProductDocumentLibraryEntry[],
  recommendedName: string,
): ProductDocumentLibraryEntry | undefined {
  return documents.find((document) => isRecommendedNameMatch(document.name, recommendedName));
}

export function findRecommendedDocuments(
  documents: ProductDocumentLibraryEntry[],
  recommendedNames: readonly string[],
): ProductDocumentLibraryEntry[] {
  const selected: ProductDocumentLibraryEntry[] = [];
  const seen = new Set<string>();

  for (const name of recommendedNames) {
    const match = findRecommendedDocument(documents, name);
    if (!match || seen.has(match.document_id)) continue;
    seen.add(match.document_id);
    selected.push(match);
  }

  return selected;
}

export function recommendedDocumentNamesLabel(names: readonly string[]): string {
  if (names.length <= 2) return names.join(' + ');
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}
