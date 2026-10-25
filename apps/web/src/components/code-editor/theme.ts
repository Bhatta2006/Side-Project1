import { HighlightStyle } from '@codemirror/language';
import { EditorView } from '@codemirror/view';
import { tags as t } from '@lezer/highlight';

/** Editor chrome and syntax colours tuned to Socrat's tokens; every pair meets WCAG AA. */
type Palette = {
  bg: string; fg: string; gutter: string; gutterFg: string; border: string; selection: string;
  activeLine: string; cursor: string; focus: string; keyword: string; string: string; number: string;
  comment: string; fn: string; type: string; constant: string; operator: string; punctuation: string;
};

const LIGHT: Palette = {
  bg: '#ffffff', fg: '#15161E', gutter: '#ffffff', gutterFg: '#8E8C84', border: '#E4E2DA',
  selection: '#FBF0A6', activeLine: '#F8F7F3', cursor: '#2340E8', focus: '#2340E8',
  keyword: '#2340E8', string: '#2F7A4C', number: '#B0441E', comment: '#6F6D66', fn: '#0E6F80',
  type: '#0E6F80', constant: '#B0441E', operator: '#3B3C46', punctuation: '#5D5C57',
};
const DARK: Palette = {
  bg: '#16171C', fg: '#ECEBE5', gutter: '#16171C', gutterFg: '#6B6A64', border: '#2A2B33',
  selection: '#2A3570', activeLine: '#1A1B21', cursor: '#93A3FF', focus: '#93A3FF',
  keyword: '#9DADFF', string: '#7CCBA0', number: '#E3B57E', comment: '#8A8982', fn: '#5BB8C6',
  type: '#5BB8C6', constant: '#E3B57E', operator: '#CFCEC8', punctuation: '#9C9B94',
};
const CONTRAST: Palette = {
  ...DARK, bg: '#000000', gutter: '#000000', fg: '#ffffff', gutterFg: '#e5e7eb', border: '#ffffff',
  comment: '#d1d5db', focus: '#ffd45c', selection: '#2A3570',
};

function highlight(p: Palette) {
  return HighlightStyle.define([
    { tag: [t.keyword, t.controlKeyword, t.moduleKeyword, t.operatorKeyword, t.definitionKeyword], color: p.keyword },
    { tag: [t.string, t.special(t.string), t.character, t.regexp], color: p.string },
    { tag: [t.number, t.integer, t.float], color: p.number },
    { tag: [t.comment, t.lineComment, t.blockComment, t.docComment], color: p.comment },
    { tag: [t.function(t.variableName), t.function(t.propertyName), t.macroName], color: p.fn },
    { tag: [t.typeName, t.className, t.namespace, t.standard(t.typeName)], color: p.type },
    { tag: [t.bool, t.null, t.atom, t.self, t.constant(t.variableName)], color: p.constant },
    { tag: [t.operator, t.compareOperator, t.arithmeticOperator, t.logicOperator], color: p.operator },
    { tag: [t.punctuation, t.bracket, t.separator], color: p.punctuation },
    { tag: [t.definition(t.variableName), t.variableName, t.propertyName], color: p.fg },
    { tag: t.invalid, color: p.constant, textDecoration: 'underline wavy' },
  ]);
}

export const HIGHLIGHT = { light: highlight(LIGHT), dark: highlight(DARK), 'high-contrast': highlight(CONTRAST) };

export function chrome(theme: 'light' | 'dark' | 'high-contrast', fontSize: number) {
  const p = theme === 'light' ? LIGHT : theme === 'dark' ? DARK : CONTRAST;
  return EditorView.theme(
    {
      '&': { height: '100%', color: p.fg, backgroundColor: p.bg, fontSize: `${fontSize}px` },
      '.cm-scroller': { overflow: 'auto', fontFamily: 'var(--font-mono), Consolas, monospace', lineHeight: '1.6', fontVariantLigatures: 'none' },
      '.cm-content': { minHeight: '100%', caretColor: p.cursor, padding: '10px 0' },
      '.cm-gutters': { color: p.gutterFg, backgroundColor: p.gutter, borderRight: `1px solid ${p.border}` },
      '.cm-activeLine': { backgroundColor: p.activeLine },
      '.cm-activeLineGutter': { backgroundColor: p.activeLine, color: p.fg },
      '&.cm-focused': { outline: `2px solid ${p.focus}`, outlineOffset: '-2px' },
      '.cm-cursor, .cm-dropCursor': { borderLeftColor: p.cursor, borderLeftWidth: '2px' },
      '.cm-selectionBackground, &.cm-focused .cm-selectionBackground, ::selection': { backgroundColor: p.selection },
      '.cm-matchingBracket': { backgroundColor: p.selection, outline: `1px solid ${p.focus}` },
      '.cm-tooltip': { backgroundColor: p.bg, color: p.fg, border: `1px solid ${p.border}`, borderRadius: '12px' },
      '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: p.selection, color: p.fg },
      '.cm-lint-marker': { outline: theme === 'high-contrast' ? '1px solid #fff' : 'none' },
    },
    { dark: theme !== 'light' },
  );
}
