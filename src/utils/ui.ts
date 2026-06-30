import {
  UI_CONFIG,
  UI_COLORS,
  UI_SPACING,
  UI_RADIUS,
  UI_FONT_SIZE,
  UI_LAYOUT,
  UI_ANIMATION,
  UI_SHADOWS,
  type ColorShades,
} from '@/config/ui'

function flattenObject(
  obj: unknown,
  prefix = '',
  result: Record<string, string> = {}
): Record<string, string> {
  if (typeof obj !== 'object' || obj === null) {
    return result
  }
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    const cssKey = prefix ? `${prefix}-${key}` : key
    if (typeof value === 'object' && value !== null) {
      flattenObject(value, cssKey, result)
    } else if (typeof value === 'string') {
      result[cssKey] = value
    }
  }
  return result
}

export function applyUiVariables(): void {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  const flatConfig = flattenObject(UI_CONFIG, 'ui')

  for (const [key, value] of Object.entries(flatConfig)) {
    const cssVarName = `--${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`
    root.style.setProperty(cssVarName, value)
  }
}

export function getColor(colorName: keyof typeof UI_COLORS): string | ColorShades
export function getColor(colorName: string): string | ColorShades | undefined
export function getColor(colorName: string): string | ColorShades | undefined {
  const colors = UI_COLORS as unknown as Record<string, string | ColorShades>
  return colors[colorName]
}

export function getColorShade(
  colorName: keyof typeof UI_COLORS,
  shade: keyof ColorShades
): string | undefined {
  const color = getColor(colorName)
  if (typeof color === 'object' && color !== null) {
    return color[shade] as string
  }
  return undefined
}

export function getSpacing(size: keyof typeof UI_SPACING): string
export function getSpacing(size: string): string | undefined
export function getSpacing(size: string): string | undefined {
  return UI_SPACING[size as keyof typeof UI_SPACING]
}

export function getRadius(size: keyof typeof UI_RADIUS): string
export function getRadius(size: string): string | undefined
export function getRadius(size: string): string | undefined {
  return UI_RADIUS[size as keyof typeof UI_RADIUS]
}

export function getFontSize(size: keyof typeof UI_FONT_SIZE): string
export function getFontSize(size: string): string | undefined
export function getFontSize(size: string): string | undefined {
  return UI_FONT_SIZE[size as keyof typeof UI_FONT_SIZE]
}

export function getLayout(key: keyof typeof UI_LAYOUT): string {
  return UI_LAYOUT[key]
}

export function getAnimation(key: keyof typeof UI_ANIMATION): string {
  return UI_ANIMATION[key]
}

export function getShadow(size: keyof typeof UI_SHADOWS): string {
  return UI_SHADOWS[size]
}

export {
  UI_CONFIG,
  UI_COLORS,
  UI_SPACING,
  UI_RADIUS,
  UI_FONT_SIZE,
  UI_LAYOUT,
  UI_ANIMATION,
  UI_SHADOWS,
}
