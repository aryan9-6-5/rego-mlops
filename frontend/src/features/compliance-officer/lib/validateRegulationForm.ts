import { MAX_REGULATORY_TEXT_CHARS } from '@/lib/utils/constants';

export interface RegulationFormErrors {
  section?: string;
  content?: string;
}

/** Inline form validation. The API sanitizes again server-side. */
export function validateRegulationForm(
  section: string,
  content: string,
): RegulationFormErrors {
  const errors: RegulationFormErrors = {};
  if (!section.trim()) {
    errors.section = 'Enter the section, for example 4.1.';
  }
  if (!content.trim()) {
    errors.content = 'Paste the regulatory text or drop a text file.';
  } else if (content.length > MAX_REGULATORY_TEXT_CHARS) {
    errors.content = `The text is ${content.length.toLocaleString()} characters. The limit is ${MAX_REGULATORY_TEXT_CHARS.toLocaleString()}.`;
  }
  return errors;
}
