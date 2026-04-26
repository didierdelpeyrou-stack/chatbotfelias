// Markdown → HTML safe (marked + DOMPurify)
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({
  gfm: true,
  breaks: true,
});

// Liens : ouverture nouvel onglet + rel sécurisé
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

export function renderMarkdown(md: string): string {
  if (!md) return '';
  // marked.parse retourne string en mode synchrone par défaut
  const html = marked.parse(md, { async: false }) as string;
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ['target', 'rel'],
  });
}
