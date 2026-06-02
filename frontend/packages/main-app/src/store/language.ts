import { ref, computed } from 'vue'

type Language = 'cn' | 'en'

const language = ref<Language>('cn')

export function useLanguage() {
  const setLanguage = (lang: Language) => {
    language.value = lang
    localStorage.setItem('aniforce-language', lang)
  }

  const toggleLanguage = () => {
    const newLang = language.value === 'cn' ? 'en' : 'cn'
    setLanguage(newLang)
  }

  // Initialize from localStorage
  const savedLang = localStorage.getItem('aniforce-language') as Language
  if (savedLang && (savedLang === 'cn' || savedLang === 'en')) {
    language.value = savedLang
  }

  return {
    language: computed(() => language.value),
    setLanguage,
    toggleLanguage
  }
}
