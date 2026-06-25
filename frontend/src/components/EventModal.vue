<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div class="glass rounded-2xl max-w-lg w-full shadow-2xl animate-slide-up border border-slate-600/50">
        <!-- Day badge -->
        <div class="flex items-center gap-3 px-6 pt-6 pb-4 border-b border-slate-700/50">
          <div class="w-12 h-12 rounded-xl bg-sky-900 border border-sky-700 flex items-center justify-center text-center">
            <div>
              <div class="text-xs text-sky-400 font-medium leading-none">{{ t('eventModal.day') }}</div>
              <div class="text-lg font-bold text-white font-mono leading-none">{{ store.game?.current_day }}</div>
            </div>
          </div>
          <div>
            <div class="text-xs text-slate-500 uppercase tracking-wider mb-0.5">{{ eventTypeLabel(event?.event_type) }}</div>
            <h2 class="text-xl font-bold text-white">{{ eventTitle(event) }}</h2>
          </div>
        </div>

        <!-- Description -->
        <div class="px-6 py-5">
          <div class="text-slate-300 text-sm leading-relaxed whitespace-pre-line">{{ eventDescription(event) }}</div>
        </div>

        <!-- Actions -->
        <div class="px-6 pb-6 flex justify-end">
          <button
            @click="store.resolveEvent()"
            :disabled="store.loading"
            class="btn-primary"
          >
            {{ store.loading ? t('eventModal.loading') : t('eventModal.gotIt', { day: store.game?.current_day }) }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import { useGameContent } from '../composables/useGameContent.js'

const { t } = useI18n()
const { eventTitle, eventDescription, eventTypeLabel } = useGameContent()
const store = useGameStore()

const event = computed(() => store.todayEvent)
</script>
