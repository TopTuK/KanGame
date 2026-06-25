<template>
  <div class="px-4 py-3 space-y-3 flex-shrink-0">
    <div class="flex flex-wrap items-start gap-4">
      <!-- Header and capacity bars -->
      <div class="flex-shrink-0 w-72">
        <div class="flex items-center justify-between mb-2">
          <h3 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">{{ t('resources.title') }}</h3>
          <span class="text-xs text-slate-500">{{ t('resources.day', { day: store.game?.current_day }) }}</span>
        </div>
        <div class="grid grid-cols-3 gap-2">
          <div v-for="role in roles" :key="role.key" :class="['rounded-lg p-2', role.bgClass]">
            <div class="flex items-center justify-between gap-1 mb-1">
              <span class="text-sm">{{ role.icon }}</span>
              <span class="text-xs font-mono">
                <span class="text-emerald-400">{{ fmtPts(store.capacityRemaining[role.key]) }}</span>
                <span class="text-slate-500">/{{ store.teamCapacity[role.key] }}</span>
              </span>
            </div>
            <div class="h-1.5 bg-black/30 rounded-full overflow-hidden">
              <div
                :class="['h-full rounded-full transition-all duration-500', role.barClass]"
                :style="{ width: usedPct(role.key) + '%' }"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Member icons -->
      <div class="flex-1 min-w-[360px]">
        <div class="text-xs text-slate-500 uppercase tracking-wider font-semibold flex items-center justify-between mb-2">
          <span>{{ store.game?.phase === 'capacity' ? t('resources.dragHint') : t('resources.assignment') }}</span>
          <span class="text-slate-600">{{ t('resources.assigned', { count: assignedCount, total: store.members.length }) }}</span>
        </div>

        <div v-if="store.game?.phase === 'capacity'" class="flex flex-wrap gap-2">
          <div
            v-for="member in store.members"
            :key="member.id"
            :draggable="true"
            :title="resourceTitle(member)"
            @dragstart="onDragStart($event, member)"
            @dragend="onDragEnd"
            :class="[
              'group flex items-center gap-2 rounded-full pl-1.5 pr-2.5 py-1.5 border transition-all duration-150 select-none',
              chipBg(member),
              chipBorder(member),
              'cursor-grab active:cursor-grabbing hover:brightness-110',
              isAssigned(member.id) ? 'opacity-75' : '',
            ]"
          >
            <div :class="['w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-base', iconBg(member)]">
              {{ member.icon }}
            </div>
            <div class="min-w-0">
              <div class="text-xs font-semibold text-white leading-tight font-mono">{{ member.id }}</div>
              <div v-if="getAssignment(member.id)" class="text-xs text-slate-400 truncate max-w-24">
                <span class="text-slate-500">→</span>
                <span class="text-slate-300 font-mono ml-1">{{ getAssignedCardKey(member.id) }}</span>
                <span :class="['ml-1 font-medium', contributionColor(getAssignment(member.id).contribution)]">
                  +{{ fmtPts(getAssignment(member.id).contribution) }}
                </span>
              </div>
              <div v-else class="text-xs text-slate-500">{{ t('resources.pts', { n: member.capacity }) }}</div>
            </div>
            <button
              v-if="isAssigned(member.id)"
              @click.stop.prevent="store.unassignMember(member.id)"
              class="w-5 h-5 rounded-full flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-950/40 transition-colors text-xs"
              :title="t('resources.removeAssignment')"
            >×</button>
          </div>
        </div>
        <div v-else class="p-2.5 bg-slate-800/40 rounded-lg text-xs text-slate-400 leading-relaxed">
          <template v-if="store.game?.phase === 'event'">
            <span class="text-sky-400 font-medium">{{ t('resources.nextEvent') }}</span> {{ t('resources.nextEventHint') }}
          </template>
          <template v-else-if="store.game?.phase === 'move'">
            <span class="text-sky-400 font-medium">{{ t('resources.now') }}</span> {{ t('resources.moveHint') }}
          </template>
          <template v-else-if="store.game?.phase === 'completed'">
            <span class="text-emerald-400 font-medium">{{ t('resources.done') }}</span> {{ t('resources.gameOver') }}
          </template>
        </div>
      </div>

      <!-- Pending assignments and actions -->
      <div class="w-72 flex-shrink-0">
        <div v-if="store.hasAssignments && store.game?.phase === 'capacity'" class="space-y-2">
          <div class="rounded-lg bg-slate-950/50 border border-slate-700/50 p-2.5">
            <div class="text-xs text-slate-500 uppercase font-semibold tracking-wider mb-1.5">{{ t('resources.pending') }}</div>
            <div class="flex flex-wrap gap-1.5">
              <div
                v-for="(alloc, cardId) in store.pendingAllocations"
                :key="cardId"
                class="rounded-full bg-slate-800/80 border border-slate-700/50 px-2 py-1 text-xs"
              >
                <span class="text-slate-300 font-mono">{{ getCardKey(cardId) }}</span>
                <span class="text-emerald-400 font-medium ml-1">+{{ fmtPts(alloc.points) }} pts</span>
              </div>
            </div>
          </div>
          <button
            @click="store.applyMemberAssignments()"
            :disabled="store.loading"
            class="w-full btn-primary text-sm py-2"
          >
            {{ t('resources.applyAssignments') }}
          </button>
        </div>
        <div v-else class="h-full rounded-lg bg-slate-800/30 border border-slate-700/40 p-2.5 text-xs text-slate-500 leading-relaxed">
          <template v-if="store.game?.phase === 'capacity'">
            {{ t('resources.dropHint') }}
          </template>
          <template v-else>
            {{ t('resources.capacityPhaseOnly') }}
          </template>
        </div>
      </div>
    </div>

    <!-- Cross-skill efficiency guide (collapsible) -->
    <div>
      <button
        @click="showGuide = !showGuide"
        class="flex items-center gap-2 text-xs text-slate-500 hover:text-slate-400 transition-colors"
      >
        <span class="uppercase tracking-wider font-semibold">{{ t('resources.crossSkillRules') }}</span>
        <span>{{ showGuide ? '▲' : '▼' }}</span>
      </button>

      <div v-if="showGuide" class="mt-2 rounded-lg bg-slate-950/50 border border-slate-700/40 p-2.5 max-w-xl">
        <table class="w-full text-xs text-center">
          <thead>
            <tr class="text-slate-500 border-b border-slate-700/50">
              <th class="text-left pb-1.5 font-normal">{{ t('resources.role') }}</th>
              <th class="pb-1.5 font-normal">🔍 {{ t('roles.analysis') }}</th>
              <th class="pb-1.5 font-normal">💻 {{ t('roles.development') }}</th>
              <th class="pb-1.5 font-normal">🧪 {{ t('roles.test') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in capacityRangesTable" :key="row.label" class="border-b border-slate-800/50 last:border-0">
              <td class="text-left py-1 text-slate-400">{{ row.label }}</td>
              <td class="py-1 text-slate-300 font-mono">{{ row.analysis }}</td>
              <td class="py-1 text-slate-300 font-mono">{{ row.development }}</td>
              <td class="py-1 text-slate-300 font-mono">{{ row.test }}</td>
            </tr>
          </tbody>
        </table>
        <p class="text-slate-600 text-xs mt-2 leading-relaxed">
          {{ t('resources.crossSkillNote') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGameStore } from '../stores/gameStore.js'
import { useGameContent } from '../composables/useGameContent.js'

const { t } = useI18n()
const { memberName } = useGameContent()
const store = useGameStore()
const showGuide = ref(false)

const roles = computed(() => [
  { key: 'analysis',    label: t('roles.analysis'),    icon: '🔍', bgClass: 'bg-violet-950/40', barClass: 'bg-violet-500' },
  { key: 'development', label: t('roles.development'), icon: '💻', bgClass: 'bg-sky-950/40',    barClass: 'bg-sky-500' },
  { key: 'test',        label: t('roles.test'),        icon: '🧪', bgClass: 'bg-amber-950/40',  barClass: 'bg-amber-500' },
])

const capacityRangesTable = computed(() => [
  { label: t('resources.analystRow'),   analysis: '0.8–1.3', development: '0.3–0.5', test: '0.4–0.8' },
  { label: t('resources.developerRow'), analysis: '0.3–0.6', development: '0.8–1.5', test: '0.5–0.7' },
  { label: t('resources.testerRow'),    analysis: '0.4–0.6', development: '0.3–0.8', test: '0.8–1.4' },
])

const assignedCount = computed(() => Object.keys(store.memberAssignments).length)

function usedPct(role) {
  const total = store.teamCapacity[role] || 1
  const used = store.game?.day_capacity_used?.[role] || 0
  return Math.min(100, (used / total) * 100)
}

function fmtPts(n) {
  const v = Number(n) || 0
  return v === Math.floor(v) ? v.toFixed(0) : v.toFixed(1)
}

function isAssigned(memberId) {
  return !!store.memberAssignments[memberId]
}

function getAssignment(memberId) {
  return store.memberAssignments[memberId] || null
}

function getAssignedCardKey(memberId) {
  const a = store.memberAssignments[memberId]
  if (!a) return ''
  const card = store.game?.cards?.find(c => c.id === a.cardId)
  return card?.card_key || '?'
}

function resourceTitle(member) {
  const assignment = getAssignment(member.id)
  const name = memberName(member)
  if (!assignment) return `${name} (${member.capacity} pts)`
  return t('resources.assignedTo', {
    name,
    card: getAssignedCardKey(member.id),
    pts: fmtPts(assignment.contribution),
  })
}

function getCardKey(cardId) {
  const card = store.game?.cards?.find(c => c.id === cardId)
  return card?.card_key || cardId.slice(0, 6)
}

function contributionColor(pts) {
  if (pts >= 1.8) return 'text-emerald-400'
  if (pts >= 0.9) return 'text-sky-400'
  return 'text-amber-400'
}

function chipBg(member) {
  const assigned = isAssigned(member.id)
  const map = {
    analyst:   assigned ? 'bg-violet-950/60' : 'bg-violet-950/30',
    developer: assigned ? 'bg-sky-950/60' : 'bg-sky-950/30',
    tester:    assigned ? 'bg-amber-950/60' : 'bg-amber-950/30',
  }
  return map[member.role] || 'bg-slate-800/40'
}

function chipBorder(member) {
  const assigned = isAssigned(member.id)
  const map = {
    analyst:   assigned ? 'border-violet-500/60' : 'border-violet-800/40',
    developer: assigned ? 'border-sky-500/60' : 'border-sky-800/40',
    tester:    assigned ? 'border-amber-500/60' : 'border-amber-800/40',
  }
  return map[member.role] || 'border-slate-700/40'
}

function iconBg(member) {
  const map = {
    analyst:   'bg-violet-800/60',
    developer: 'bg-sky-800/60',
    tester:    'bg-amber-800/60',
  }
  return map[member.role] || 'bg-slate-700/60'
}

function onDragStart(e, member) {
  store.currentDragMember = member
  e.dataTransfer.setData('memberId', member.id)
  e.dataTransfer.effectAllowed = 'copy'
}

function onDragEnd() {
  store.currentDragMember = null
}
</script>
