<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
    <div class="bg-slate-900 border border-slate-600 rounded-2xl max-w-lg w-full shadow-2xl">
      <div class="px-6 py-4 border-b border-slate-700">
        <div class="text-xs text-slate-500 uppercase tracking-wider">{{ t('eventModal.day') }} {{ modal.day }}</div>
        <h2 class="text-xl font-bold text-white mt-1">{{ modal.title }}</h2>
      </div>
      <div class="px-6 py-5 text-sm text-slate-300 whitespace-pre-line leading-relaxed max-h-64 overflow-y-auto">
        {{ modal.description }}
      </div>
      <div v-if="modal.overdue?.length" class="px-6 pb-4">
        <p class="text-red-400 font-semibold text-sm mb-2">{{ t('endDay.overdueTitle') }}</p>
        <p v-for="o in modal.overdue" :key="o.card_key" class="text-xs text-slate-400">
          {{ o.card_key }} (Day {{ o.due_day }})
          <span v-if="o.val < 0" class="text-red-400"> — {{ fmtRub(o.val) }}</span>
        </p>
      </div>
      <div class="px-6 py-4 border-t border-slate-700 flex justify-end">
        <button @click="$emit('close')" class="btn-primary px-6 py-2">
          {{ t('eventModal.gotIt') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
defineProps({ modal: Object })
defineEmits(['close'])
const { t } = useI18n()

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}
</script>
