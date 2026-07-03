<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="bg-slate-900 border border-slate-600 rounded-2xl max-w-3xl w-full shadow-2xl max-h-[85vh] flex flex-col">
      <div class="px-6 py-4 border-b border-slate-700 flex-shrink-0">
        <h2 class="text-xl font-bold text-white">{{ t('metrics.title') }}</h2>
      </div>

      <div class="px-6 py-5 overflow-y-auto grid grid-cols-2 gap-6">
        <MetricsPanel />

        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-2">{{ t('metrics.revenueByDay') }}</div>
          <div v-if="metrics.length" class="space-y-1.5">
            <div
              v-for="m in [...metrics].reverse()"
              :key="m.day"
              class="flex items-center gap-2 text-xs"
            >
              <span class="text-slate-500 w-8 flex-shrink-0">D{{ m.day }}</span>
              <div class="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-emerald-500 rounded-full transition-all"
                  :style="{ width: maxRevenue ? (m.daily_revenue / maxRevenue * 100) + '%' : '0%' }"
                ></div>
              </div>
              <span class="text-emerald-400 w-20 text-right font-mono text-[10px]">{{ fmtRub(m.daily_revenue) }}</span>
            </div>
          </div>
          <div v-else class="text-xs text-slate-600 text-center py-4">
            {{ t('metrics.noMetrics') }}
          </div>
        </div>
      </div>

      <div class="px-6 py-4 border-t border-slate-700 flex justify-end flex-shrink-0">
        <button @click="$emit('close')" class="btn-primary px-6 py-2">{{ t('workLog.close') }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import MetricsPanel from './MetricsPanel.vue'

defineEmits(['close'])
const { t } = useI18n()
const store = useGameStore()

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}

const metrics = computed(() => store.game?.metrics || [])
const maxRevenue = computed(() => Math.max(1, ...metrics.value.map(m => m.daily_revenue)))
</script>
