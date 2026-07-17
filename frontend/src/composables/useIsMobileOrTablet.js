import { ref } from 'vue'

const BREAKPOINT_PX = 1179

const mediaQuery = typeof window !== 'undefined' ? window.matchMedia(`(max-width: ${BREAKPOINT_PX}px)`) : null

const isMobileOrTablet = ref(mediaQuery ? mediaQuery.matches : false)

mediaQuery?.addEventListener('change', (e) => {
  isMobileOrTablet.value = e.matches
})

export function useIsMobileOrTablet() {
  return { isMobileOrTablet }
}
