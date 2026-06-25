import { createI18n } from 'vue-i18n'
import ru from './locales/ru.json'
import en from './locales/en.json'

const STORAGE_KEY = 'kangame-locale'
const SUPPORTED_LOCALES = ['ru', 'en']

function getInitialLocale() {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved && SUPPORTED_LOCALES.includes(saved)) return saved
  return 'ru'
}

export const i18n = createI18n({
  legacy: false,
  locale: getInitialLocale(),
  fallbackLocale: 'en',
  messages: { ru, en },
})

export function setLocale(locale) {
  if (!SUPPORTED_LOCALES.includes(locale)) return
  i18n.global.locale.value = locale
  localStorage.setItem(STORAGE_KEY, locale)
  document.documentElement.lang = locale
}

export const availableLocales = [
  { code: 'ru', label: 'Русский' },
  { code: 'en', label: 'English' },
]
