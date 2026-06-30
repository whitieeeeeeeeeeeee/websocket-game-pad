export const APP_VERSION = '1.7.1'
export const APP_NAME = 'WiFi-SPI Controller'

export function getVersion(): string {
  return APP_VERSION
}

export function getAppName(): string {
  return APP_NAME
}

export function getFullVersionInfo(): string {
  return `${APP_NAME} v${APP_VERSION}`
}
