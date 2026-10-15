<template>
  <div class="min-h-screen bg-board-bg relative overflow-hidden flex flex-col">
    <div class="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div class="absolute -top-32 -left-32 w-96 h-96 bg-sky-500/15 rounded-full blur-3xl"></div>
      <div class="absolute top-1/3 -right-32 w-96 h-96 bg-violet-500/10 rounded-full blur-3xl"></div>
    </div>

    <div class="fixed top-4 right-4 z-50">
      <LanguageSelector />
    </div>

    <main class="flex-1 w-full max-w-4xl mx-auto px-4 py-12 sm:py-16">
      <router-link to="/" class="text-sm text-slate-400 hover:text-slate-200 transition-colors">{{ t('rules.back') }}</router-link>

      <header class="text-center mt-6 mb-10 animate-fade-in">
        <div class="text-5xl mb-3">📜</div>
        <h1 class="font-display text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-3">{{ t('rules.title') }}</h1>
        <p class="text-slate-400 max-w-2xl mx-auto">{{ t('rules.subtitle') }}</p>
        <p v-if="loading" class="text-sm text-slate-500 mt-4">{{ t('rules.loading') }}</p>
        <p v-else-if="error" class="text-sm text-amber-300 mt-4">{{ t('rules.error') }}</p>
      </header>

      <nav class="glass rounded-2xl p-5 mb-8">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">{{ t('rules.contents') }}</h2>
        <ol class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-sm">
          <li v-for="s in sections" :key="s">
            <a :href="`#${s}`" class="text-sky-300 hover:text-sky-200">{{ t(`rules.${s}.title`) }}</a>
          </li>
        </ol>
      </nav>

      <div class="space-y-8 text-slate-300 leading-relaxed">
        <!-- 1. Goal -->
        <section id="goal" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.goal.title') }}</h2>
          <p class="mb-3">{{ t('rules.goal.p1', { start: startDay, end: totalDays }) }}</p>
          <p class="text-emerald-300 font-medium">{{ t('rules.goal.p2') }}</p>
        </section>

        <!-- 2. Board -->
        <section id="board" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.board.title') }}</h2>
          <p class="mb-3">{{ t('rules.board.p1') }}</p>
          <div class="flex flex-wrap items-center gap-1.5 mb-4 text-xs">
            <template v-for="(col, i) in laneColumns" :key="col">
              <span :class="['px-2 py-1 rounded-md font-medium', columnClass(col)]">{{ t(`rules.columns.${col}`) }}</span>
              <span v-if="i < laneColumns.length - 1" class="text-slate-500">→</span>
            </template>
          </div>
          <p class="mb-3">{{ t('rules.board.p2') }}</p>
          <p class="mb-3">{{ t('rules.board.p3') }}</p>
          <p>{{ t('rules.board.p4') }}</p>
        </section>

        <!-- 3. Your day -->
        <section id="turn" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.turn.title') }}</h2>
          <p class="mb-4">{{ t('rules.turn.intro') }}</p>
          <ol class="space-y-3">
            <li v-for="n in 8" :key="n" class="flex gap-3">
              <span class="shrink-0 w-7 h-7 rounded-full bg-sky-500/20 text-sky-300 text-sm font-bold flex items-center justify-center">{{ n }}</span>
              <div>
                <div class="font-semibold text-white">{{ t(`rules.turn.s${n}t`) }}</div>
                <div class="text-sm text-slate-400">{{ t(`rules.turn.s${n}`) }}</div>
              </div>
            </li>
          </ol>
        </section>

        <!-- 4. WIP -->
        <section id="wip" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.wip.title') }}</h2>
          <p class="mb-3">{{ t('rules.wip.p1') }}</p>
          <div v-if="rules" class="overflow-x-auto mb-3">
            <table :class="table">
              <thead>
                <tr :class="thead">
                  <th :class="th">{{ t('rules.wip.stage') }}</th>
                  <th :class="th">{{ t('rules.wip.limit') }}</th>
                  <th :class="th">{{ t('rules.wip.counts') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(limit, key) in rules.initial_wip" :key="key" :class="tr">
                  <td :class="td">{{ t(`rules.stages.${key}`) }}</td>
                  <td :class="[td, 'font-mono text-white']">{{ limit }}</td>
                  <td :class="[td, 'text-slate-400']">{{ wipColumns(key) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="mb-3">{{ t('rules.wip.p2') }}</p>
          <p>{{ t('rules.wip.p3') }}</p>
        </section>

        <!-- 5. Card types -->
        <section id="cards" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.cards.title') }}</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div v-for="ct in cardTypes" :key="ct.key" :class="['rounded-xl border p-4', ct.box]">
              <div :class="['font-semibold mb-1', ct.text]">{{ t(`rules.cards.${ct.key}Name`) }}</div>
              <div class="text-sm text-slate-300">{{ t(`rules.cards.${ct.key}`) }}</div>
            </div>
          </div>
          <p class="text-sm text-amber-200 bg-amber-500/10 rounded-lg px-3 py-2">{{ t('rules.cards.overdue') }}</p>
        </section>

        <!-- 6. Catalog -->
        <section id="catalog" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.catalog.title') }}</h2>
          <p class="mb-4">{{ t('rules.catalog.intro') }}</p>
          <template v-if="rules">
            <div class="flex flex-wrap gap-2 mb-3">
              <button
                v-for="f in catalogFilters"
                :key="f"
                type="button"
                @click="catalogFilter = f"
                :class="[
                  'text-xs px-3 py-1 rounded-full transition-colors',
                  catalogFilter === f ? 'bg-sky-500/30 text-sky-200' : 'bg-white/5 text-slate-400 hover:bg-white/10',
                ]"
              >{{ f === 'all' ? t('rules.catalog.all') : t(`rules.catalog.types.${f}`) }}</button>
            </div>
            <div class="overflow-x-auto max-h-[28rem] overflow-y-auto rounded-lg">
              <table :class="table">
                <thead class="sticky top-0 bg-slate-900">
                  <tr :class="thead">
                    <th v-for="col in catalogColumns" :key="col.key" :class="[th, col.num ? 'text-right' : '']">
                      <button v-if="col.sort" type="button" @click="sortBy(col.key)" class="uppercase tracking-wide hover:text-white">
                        {{ t(`rules.catalog.${col.key}`) }}{{ sortKey === col.key ? (sortAsc ? ' ↑' : ' ↓') : '' }}
                      </button>
                      <span v-else>{{ t(`rules.catalog.${col.key}`) }}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="c in catalog" :key="c.key" :class="tr">
                    <td :class="[td, 'font-mono font-semibold', typeText(c.type)]">{{ c.key }}</td>
                    <td :class="[td, 'text-slate-400 whitespace-nowrap']">{{ t(`rules.catalog.types.${c.type}`) }}</td>
                    <td :class="[td, 'text-right font-mono whitespace-nowrap', c.value < 0 ? 'text-red-400' : 'text-emerald-400']">
                      {{ c.value ? fmtNum(c.value) : '—' }}<span v-if="c.type === 'standard'" class="text-slate-500">{{ t('rules.catalog.perDay') }}</span>
                    </td>
                    <td :class="[td, 'text-right font-mono']">{{ c.analysis }}</td>
                    <td :class="[td, 'text-right font-mono']">{{ c.development }}</td>
                    <td :class="[td, 'text-right font-mono']">{{ c.test }}</td>
                    <td :class="[td, 'text-slate-400 whitespace-nowrap']">{{ t(`rules.columns.${c.start_column}`) }}</td>
                    <td :class="[td, 'text-slate-400 whitespace-nowrap']">{{ cardTerms(c) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </section>

        <!-- 7. Team -->
        <section id="team" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.team.title') }}</h2>
          <p class="mb-3">{{ t('rules.team.p1') }}</p>
          <div v-if="rules" class="overflow-x-auto mb-4">
            <table :class="table">
              <thead>
                <tr :class="thead">
                  <th :class="th">{{ t('rules.team.role') }}</th>
                  <th :class="th">{{ t('rules.team.workers') }}</th>
                  <th :class="th">{{ t('rules.team.activeAtStart') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="role in roles" :key="role" :class="tr">
                  <td :class="td">{{ t(`rules.roles.${role}`) }}</td>
                  <td :class="[td, 'font-mono text-slate-400']">{{ workersOf(role).map((w) => w.id).join(', ') }}</td>
                  <td :class="[td, 'font-mono text-white']">{{ workersOf(role).filter((w) => w.active_at_start).map((w) => w.id).join(', ') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="mb-3">{{ t('rules.team.p2') }}</p>
          <div v-if="rules" class="overflow-x-auto mb-4">
            <table :class="table">
              <thead>
                <tr :class="thead">
                  <th :class="th">{{ t('rules.team.stage') }}</th>
                  <th v-for="stage in stages" :key="stage" :class="th">{{ t(`rules.stages.${stage}`) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="role in roles" :key="role" :class="tr">
                  <td :class="td">{{ t(`rules.roles.${role}`) }}</td>
                  <td
                    v-for="stage in stages"
                    :key="stage"
                    :class="[td, 'font-mono whitespace-nowrap', SPECIALIST[stage] === role ? 'text-emerald-300 font-semibold' : 'text-slate-400']"
                  >
                    {{ range(stage, role).join('–') }}
                    <span class="text-xs text-slate-500">· {{ t('rules.team.avg', { avg: avg(stage, role) }) }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-if="rules" class="mb-3 text-sky-200">{{ t('rules.team.capacity', capacity) }}</p>
          <ul class="list-disc pl-5 space-y-2 text-sm">
            <li>{{ t('rules.team.estimate') }}</li>
            <li>{{ t('rules.team.rules') }}</li>
            <li>{{ t('rules.team.blockers') }}</li>
            <li>{{ t('rules.team.buffs') }}</li>
          </ul>
        </section>

        <!-- 8. Events -->
        <section id="events" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.events.title') }}</h2>
          <p class="mb-3">{{ t('rules.events.p1') }}</p>
          <ul class="list-disc pl-5 space-y-1 text-sm">
            <li v-for="k in ['people', 'blockers', 'wip', 'expedite']" :key="k">{{ t(`rules.events.${k}`) }}</li>
          </ul>
        </section>

        <!-- 9. Scoring -->
        <section id="scoring" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.scoring.title') }}</h2>
          <p class="mb-3">{{ t('rules.scoring.p1', { end: totalDays }) }}</p>
          <ul v-if="rules" class="space-y-1.5">
            <li v-for="(r, i) in rules.ranks" :key="r.rank" class="flex items-center justify-between rounded-lg bg-white/5 px-4 py-2">
              <span class="font-semibold text-white">{{ t(RANK_LABELS[r.rank]) }}</span>
              <span class="font-mono text-emerald-400 text-sm">
                {{ r.min_revenue > 0
                  ? t('rules.scoring.from', { amount: fmtRub(r.min_revenue) })
                  : t('rules.scoring.below', { amount: fmtRub(rules.ranks[i - 1]?.min_revenue) }) }}
              </span>
            </li>
          </ul>
        </section>

        <!-- 10. Tips -->
        <section id="tips" class="glass rounded-2xl p-6 scroll-mt-6">
          <h2 :class="h2">{{ t('rules.tips.title') }}</h2>
          <ul class="space-y-2">
            <li v-for="n in 7" :key="n" class="flex gap-2"><span class="text-sky-400">✓</span><span>{{ t(`rules.tips.t${n}`) }}</span></li>
          </ul>
          <p class="mt-4 text-sm text-violet-300">🤖 {{ t('rules.agentNote') }}</p>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { rulesApi } from '../services/api.js'
import LanguageSelector from '../components/LanguageSelector.vue'

const { t } = useI18n()

const sections = ['goal', 'board', 'turn', 'wip', 'cards', 'catalog', 'team', 'events', 'scoring', 'tips']
const laneColumns = ['backlog', 'ready', 'analysis', 'analysis_done', 'development', 'dev_done', 'test', 'test_done', 'deployed']
const roles = ['analyst', 'developer', 'tester']
const stages = ['analysis', 'development', 'test']
const SPECIALIST = { analysis: 'analyst', development: 'developer', test: 'tester' }
const RANK_LABELS = {
  master: 'score.rankMaster',
  expert: 'score.rankExpert',
  practitioner: 'score.rankPractitioner',
  starter: 'score.rankStarter',
  learning: 'score.rankLearning',
}
const cardTypes = [
  { key: 'standard', box: 'border-sky-500/30 bg-sky-500/5', text: 'text-sky-300' },
  { key: 'fixed', box: 'border-yellow-500/30 bg-yellow-500/5', text: 'text-yellow-300' },
  { key: 'expedite', box: 'border-red-500/30 bg-red-500/5', text: 'text-red-300' },
  { key: 'intangible', box: 'border-slate-500/40 bg-slate-500/5', text: 'text-slate-300' },
]
const catalogFilters = ['all', 'standard', 'fixed_date', 'intangible']
const catalogColumns = [
  { key: 'key', sort: true },
  { key: 'type', sort: false },
  { key: 'value', sort: true, num: true },
  { key: 'analysis', sort: true, num: true },
  { key: 'development', sort: true, num: true },
  { key: 'test', sort: true, num: true },
  { key: 'start', sort: false },
  { key: 'terms', sort: false },
]

// Table styling shared by every table on the page.
const h2 = 'font-display text-xl font-bold text-white mb-3'
const table = 'w-full text-sm text-left border-collapse'
const thead = 'text-xs uppercase tracking-wide text-slate-400 border-b border-white/10'
const th = 'px-3 py-2 font-semibold'
const tr = 'border-b border-white/5'
const td = 'px-3 py-2'

const rules = ref(null)
const loading = ref(true)
const error = ref(false)
const catalogFilter = ref('all')
const sortKey = ref('key')
const sortAsc = ref(true)

const startDay = computed(() => rules.value?.start_day ?? 9)
const totalDays = computed(() => rules.value?.total_days ?? 35)

function fmtNum(n) {
  return Number(n || 0).toLocaleString('ru-RU')
}

function fmtRub(n) {
  return fmtNum(n) + ' ₽'
}

function columnClass(col) {
  if (['analysis', 'development', 'test'].includes(col)) return 'bg-sky-500/20 text-sky-200'
  if (col === 'deployed') return 'bg-emerald-500/20 text-emerald-200'
  return 'bg-white/5 text-slate-300'
}

function typeText(type) {
  return { standard: 'text-sky-300', fixed_date: 'text-yellow-300', intangible: 'text-slate-300' }[type] || 'text-white'
}

function wipColumns(key) {
  return (rules.value?.wip_groups[key] || [key]).map((c) => t(`rules.columns.${c.replace('exp_', '')}`)).join(' + ')
}

function workersOf(role) {
  return (rules.value?.workers || []).filter((w) => w.role === role)
}

function range(stage, role) {
  return rules.value?.work_ranges[stage]?.[role] || []
}

function avg(stage, role) {
  const [lo, hi] = range(stage, role)
  return (lo + hi) / 2
}

const capacity = computed(() => {
  const out = {}
  for (const [short, stage] of [['a', 'analysis'], ['d', 'development'], ['t', 'test']]) {
    const role = SPECIALIST[stage]
    out[short] = workersOf(role).filter((w) => w.active_at_start).length * avg(stage, role)
  }
  return out
})

function cardTerms(c) {
  if (c.type === 'fixed_date') return t('rules.catalog.dueDay', { day: c.due_day })
  if (c.type === 'intangible') return t('rules.catalog.buff', { role: t(`rules.roles.${c.buff}`) })
  return ''
}

function sortBy(key) {
  if (sortKey.value === key) sortAsc.value = !sortAsc.value
  else {
    sortKey.value = key
    sortAsc.value = key === 'key'
  }
}

function keyOrder(key) {
  // S1 < S2 < … < F1 < I1 : type first, then number.
  const order = { S: 0, F: 1, I: 2 }
  return (order[key[0]] ?? 9) * 1000 + Number(key.slice(1))
}

const catalog = computed(() => {
  const cards = (rules.value?.cards || []).filter((c) => catalogFilter.value === 'all' || c.type === catalogFilter.value)
  const dir = sortAsc.value ? 1 : -1
  const val = (c) => (sortKey.value === 'key' ? keyOrder(c.key) : c[sortKey.value])
  return [...cards].sort((x, y) => (val(x) - val(y)) * dir)
})

onMounted(async () => {
  try {
    rules.value = (await rulesApi.get()).data
  } catch {
    error.value = true
  } finally {
    loading.value = false
  }
})
</script>
