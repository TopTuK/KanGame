<template>
  <div ref="root" class="relative">
    <button
      @click.stop="open = !open"
      class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
             bg-slate-800/80 border border-slate-600/50 text-slate-300
             hover:bg-slate-700/80 hover:text-white transition-colors"
      :title="t('language.select')"
    >
      <span>🌐</span>
      <span>{{ currentLabel }}</span>
      <span class="text-xs opacity-60">{{ open ? '▲' : '▼' }}</span>
    </button>

    <div
      v-if="open"
      class="absolute right-0 mt-1 min-w-[8rem] rounded-lg bg-slate-800 border border-slate-600/50
             shadow-xl z-50 overflow-hidden"
    >
      <button
        v-for="loc in availableLocales"
        :key="loc.code"
        @click="selectLocale(loc.code)"
        :class="[
          'w-full px-4 py-2 text-sm text-left transition-colors',
          locale === loc.code
            ? 'bg-sky-900/60 text-sky-300 font-medium'
            : 'text-slate-300 hover:bg-slate-700/60 hover:text-white',
        ]"
      >
        {{ loc.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { availableLocales, setLocale } from '../i18n/index.js'

const { t, locale } = useI18n()
const open = ref(false)
const root = ref(null)

const currentLabel = computed(() =>
  availableLocales.find(l => l.code === locale.value)?.label || locale.value
)

function selectLocale(code) {
  setLocale(code)
  open.value = false
}

function onClickOutside(e) {
  if (root.value && !root.value.contains(e.target)) open.value = false
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>
