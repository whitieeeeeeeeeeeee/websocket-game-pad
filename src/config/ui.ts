export interface ColorShades {
  50: string
  100: string
  200: string
  300: string
  400: string
  500: string
  600: string
  700: string
  800: string
  900: string
  DEFAULT?: string
  light?: string
  dark?: string
}

export interface UIColors {
  primary: ColorShades
  success: string
  warning: string
  error: string
  recording: string
  playback: string
  info: string
  gray: ColorShades
}

export interface UISpacing {
  xs: string
  sm: string
  md: string
  base: string
  lg: string
  xl: string
  '2xl': string
}

export interface UIRadius {
  sm: string
  md: string
  lg: string
  xl: string
  '2xl': string
  '3xl': string
  full: string
}

export interface UIFontSize {
  xs: string
  sm: string
  base: string
  lg: string
  xl: string
  '2xl': string
  '3xl': string
  '4xl': string
}

export interface UILayout {
  sidebarWidth: string
  sidebarWidthCollapsed: string
  headerHeight: string
  cardPadding: string
  gap: string
  cardRadius: string
  scrollbarWidth: string
}

export interface UIAnimation {
  durationFast: string
  durationNormal: string
  durationSlow: string
  easing: string
}

export interface UIShadows {
  sm: string
  md: string
  lg: string
}

export interface UIBorder {
  color: string
  colorLight: string
}

export interface UIText {
  primary: string
  secondary: string
  muted: string
}

export interface UIBackground {
  page: string
  card: string
}

export interface UIConfig {
  colors: UIColors
  spacing: UISpacing
  radius: UIRadius
  fontSize: UIFontSize
  layout: UILayout
  animation: UIAnimation
  shadows: UIShadows
  border: UIBorder
  text: UIText
  background: UIBackground
}

export const UI_COLORS: UIColors = {
  primary: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
    DEFAULT: '#3b82f6',
    light: '#60a5fa',
    dark: '#2563eb',
  },
  success: '#16a34a',
  warning: '#eab308',
  error: '#dc2626',
  recording: '#ea580c',
  playback: '#7c3aed',
  info: '#3b82f6',
  gray: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
  },
}

export const UI_SPACING: UISpacing = {
  xs: '0.25rem',
  sm: '0.5rem',
  md: '0.75rem',
  base: '1rem',
  lg: '1.25rem',
  xl: '1.5rem',
  '2xl': '2rem',
}

export const UI_RADIUS: UIRadius = {
  sm: '0.25rem',
  md: '0.375rem',
  lg: '0.5rem',
  xl: '0.75rem',
  '2xl': '1rem',
  '3xl': '1.5rem',
  full: '9999px',
}

export const UI_FONT_SIZE: UIFontSize = {
  xs: '0.6875rem',
  sm: '0.75rem',
  base: '0.875rem',
  lg: '1rem',
  xl: '1.125rem',
  '2xl': '1.25rem',
  '3xl': '1.5rem',
  '4xl': '1.875rem',
}

export const UI_LAYOUT: UILayout = {
  sidebarWidth: '220px',
  sidebarWidthCollapsed: '64px',
  headerHeight: '56px',
  cardPadding: '1.25rem',
  gap: '1.25rem',
  cardRadius: '0.75rem',
  scrollbarWidth: '0.5rem',
}

export const UI_ANIMATION: UIAnimation = {
  durationFast: '150ms',
  durationNormal: '200ms',
  durationSlow: '300ms',
  easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
}

export const UI_SHADOWS: UIShadows = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1)',
}

export const UI_BORDER: UIBorder = {
  color: '#e4e4e7',
  colorLight: '#f4f4f5',
}

export const UI_TEXT: UIText = {
  primary: '#18181b',
  secondary: '#52525b',
  muted: '#71717a',
}

export const UI_BACKGROUND: UIBackground = {
  page: '#fafafa',
  card: '#ffffff',
}

export const UI_CONFIG: UIConfig = {
  colors: UI_COLORS,
  spacing: UI_SPACING,
  radius: UI_RADIUS,
  fontSize: UI_FONT_SIZE,
  layout: UI_LAYOUT,
  animation: UI_ANIMATION,
  shadows: UI_SHADOWS,
  border: UI_BORDER,
  text: UI_TEXT,
  background: UI_BACKGROUND,
}

export default UI_CONFIG
