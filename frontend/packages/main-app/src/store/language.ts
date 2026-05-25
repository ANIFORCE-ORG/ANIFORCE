import { computed, ref } from 'vue'

export type Language = 'cn' | 'en'

const language = ref<Language>('cn')

export function useLanguage() {
  const isEnglish = computed(() => language.value === 'en')

  const setLanguage = (value: Language) => {
    language.value = value
  }

  const toggleLanguage = () => {
    language.value = language.value === 'cn' ? 'en' : 'cn'
  }

  return {
    language,
    isEnglish,
    setLanguage,
    toggleLanguage,
  }
}
