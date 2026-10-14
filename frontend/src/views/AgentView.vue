<template>
  <div class="min-h-screen bg-board-bg relative flex flex-col">
    <div class="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div class="absolute -top-32 -left-32 w-96 h-96 bg-violet-500/15 rounded-full blur-3xl"></div>
      <div class="absolute top-1/3 -right-32 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl"></div>
    </div>

    <header class="flex items-center justify-between px-6 py-4 border-b border-white/5">
      <div class="flex items-center gap-4">
        <router-link to="/" class="text-sm text-slate-400 hover:text-slate-200 transition-colors">{{ t('agent.back') }}</router-link>
        <h1 class="font-display text-2xl font-bold text-white">🤖 {{ t('agent.title') }}</h1>
      </div>
      <LanguageSelector />
    </header>

    <main class="flex-1 grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6 p-6 max-w-[1600px] w-full mx-auto">
      <!-- Left: start form + runs -->
      <section class="space-y-6">
        <p class="text-sm text-slate-400">{{ t('agent.subtitle') }}</p>

        <form @submit.prevent="startRun" class="glass rounded-2xl p-6 space-y-4">
          <h2 class="font-display text-lg font-semibold text-white">{{ t('agent.newRun') }}</h2>
          <label class="block">
            <span class="text-xs text-slate-400">{{ t('agent.name') }}</span>
            <input v-model="form.name" required maxlength="60" :placeholder="t('agent.namePlaceholder')" :class="inputClass" />
          </label>
          <label class="block">
            <span class="text-xs text-slate-400">{{ t('agent.baseUrl') }}</span>
            <input v-model="form.base_url" required type="url" :class="inputClass" />
          </label>
          <label class="block">
            <span class="text-xs text-slate-400">{{ t('agent.model') }}</span>
            <input v-model="form.model" required maxlength="200" :class="inputClass" />
          </label>
          <label class="block">
            <span class="text-xs text-slate-400">{{ t('agent.apiKey') }}</span>
            <input
              v-model="form.api_key"
              :required="!serverKeyUsable"
              type="password"
              autocomplete="off"
              :placeholder="serverKeyUsable ? t('agent.apiKeyServerPlaceholder') : ''"
              :class="inputClass"
            />
            <span class="block text-[11px] text-slate-500 mt-1">
              {{ serverKeyUsable ? t('agent.apiKeyServerHint') : t('agent.apiKeyHint') }}
            </span>
          </label>
          <button
            v-if="config && (form.base_url !== config.default_base_url || form.model !== config.default_model)"
            type="button"
            @click="resetToDefaults"
            class="text-xs text-sky-400 hover:text-sky-300"
          >{{ t('agent.resetDefaults', { model: config.default_model }) }}</button>
          <p v-if="formError" class="text-sm text-red-400">{{ formError }}</p>
          <button type="submit" :disabled="starting || hasActiveRun" class="w-full btn-primary py-2.5 rounded-xl disabled:opacity-50">
            {{ starting ? t('agent.starting') : t('agent.start') }}
          </button>
          <p v-if="hasActiveRun" class="text-xs text-amber-300">{{ t('agent.activeRunExists') }}</p>
        </form>

        <div class="glass rounded-2xl p-4">
          <h2 class="font-display text-lg font-semibold text-white mb-3 px-2">{{ t('agent.runs') }}</h2>
          <p v-if="!runs.length" class="text-sm text-slate-500 px-2 pb-2">{{ t('agent.noRuns') }}</p>
          <button
            v-for="r in runs"
            :key="r.id"
            type="button"
            @click="selectRun(r.id)"
            :class="[
              'w-full text-left rounded-xl px-3 py-3 mb-2 transition-colors',
              selected?.id === r.id ? 'bg-white/10' : 'hover:bg-white/5',
            ]"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="font-semibold text-white truncate">{{ r.name }}</span>
              <span :class="['text-[11px] font-medium px-2 py-0.5 rounded-full shrink-0', statusClass(r.status)]">
                {{ t(`agent.statuses.${r.status}`) }}
              </span>
            </div>
            <div class="flex items-center justify-between text-xs text-slate-400 mt-1">
              <span class="truncate">{{ r.model }}</span>
              <span v-if="r.game">
                {{ t('agent.dayProgress', { current: r.game.current_day, total: r.game.total_days }) }} ·
                <span class="text-emerald-400 font-mono">{{ fmtRub(r.game.total_revenue) }}</span>
              </span>
            </div>
          </button>
        </div>
      </section>

      <!-- Right: selected run -->
      <section class="glass rounded-2xl p-6 min-h-[60vh] flex flex-col">
        <p v-if="!selected" class="text-slate-500 m-auto">{{ t('agent.selectRun') }}</p>
        <template v-else>
          <div class="flex flex-wrap items-start justify-between gap-4 mb-4">
            <div>
              <div class="flex items-center gap-3">
                <h2 class="font-display text-xl font-bold text-white">{{ selected.name }}</h2>
                <span :class="['text-xs font-medium px-2 py-0.5 rounded-full', statusClass(selected.status)]">
                  <span v-if="isActive(selected.status)" class="inline-block w-1.5 h-1.5 rounded-full bg-current animate-pulse mr-1 align-middle"></span>
                  {{ t(`agent.statuses.${selected.status}`) }}
                </span>
              </div>
              <div class="text-xs text-slate-400 mt-1 font-mono">{{ selected.model }} · {{ selected.base_url }}</div>
            </div>
            <div class="flex flex-wrap gap-2">
              <router-link :to="`/game/${selected.game_id}`" class="btn-secondary text-sm py-1.5 px-4">{{ t('agent.openBoard') }}</router-link>
              <a :href="agentApi.logUrl(selected.id)" class="btn-secondary text-sm py-1.5 px-4">{{ t('agent.downloadLog') }}</a>
              <button
                v-if="isActive(selected.status)"
                type="button"
                @click="cancelRun"
                :disabled="cancelling"
                class="btn-danger text-sm py-1.5 px-4 disabled:opacity-50"
              >{{ cancelling ? t('agent.cancelling') : t('agent.cancel') }}</button>
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div class="rounded-xl bg-white/5 px-4 py-3">
              <div class="text-[11px] text-slate-400 uppercase">{{ t('agent.dayLabel') }}</div>
              <div class="text-lg font-bold text-white">{{ selected.game?.current_day }} / {{ selected.game?.total_days }}</div>
            </div>
            <div class="rounded-xl bg-white/5 px-4 py-3">
              <div class="text-[11px] text-slate-400 uppercase">{{ t('agent.revenue') }}</div>
              <div class="text-lg font-bold text-emerald-400 font-mono">{{ fmtRub(selected.game?.total_revenue) }}</div>
            </div>
            <div class="rounded-xl bg-white/5 px-4 py-3">
              <div class="text-[11px] text-slate-400 uppercase">{{ t('agent.toolCalls') }}</div>
              <div class="text-lg font-bold text-white">{{ selected.tool_calls }}</div>
            </div>
            <div class="rounded-xl bg-white/5 px-4 py-3">
              <div class="text-[11px] text-slate-400 uppercase">{{ t('agent.tokens') }}</div>
              <div class="text-lg font-bold text-white">{{ (selected.input_tokens + selected.output_tokens).toLocaleString() }}</div>
            </div>
          </div>

          <p v-if="selected.error" class="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2 mb-4 break-words">
            {{ t('agent.error') }}: {{ selected.error }}
          </p>

          <!-- Action feed: newest day first, actions within a day in order -->
          <div class="flex-1 overflow-y-auto space-y-5 pr-1">
            <div v-for="group in dayGroups" :key="group.day">
              <div class="sticky top-0 bg-board-bg/90 backdrop-blur text-xs font-semibold text-sky-300 uppercase tracking-wide py-1 mb-2">
                {{ t('agent.day', { day: group.day }) }}
              </div>
              <ul class="space-y-1.5">
                <li
                  v-for="a in group.actions"
                  :key="a.id"
                  :class="[
                    'rounded-lg px-3 py-2 text-sm',
                    a.action === 'day_summary' ? 'bg-violet-500/10 border border-violet-500/30' : 'bg-white/[0.03]',
                  ]"
                >
                  <div class="flex items-baseline gap-2">
                    <span class="text-[10px] font-mono text-slate-500 w-8 shrink-0">#{{ a.seq }}</span>
                    <span :class="['text-[10px] uppercase font-semibold shrink-0', actorClass(a.actor)]">{{ t(`agent.actors.${a.actor}`) }}</span>
                    <span class="font-medium text-slate-200 shrink-0">{{ t(`agent.actions.${a.action}`) }}</span>
                    <span :class="['truncate', a.result?.ok === false ? 'text-red-400' : 'text-slate-400']">{{ describe(a) }}</span>
                  </div>
                  <div v-if="a.reason" :class="['mt-1 pl-10', a.action === 'day_summary' ? 'text-violet-200' : 'italic text-slate-400']">
                    {{ a.reason }}
                  </div>
                  <ul v-if="a.action === 'start_work' && a.result?.log?.length" class="mt-1 pl-10 text-xs text-slate-500 font-mono space-y-0.5">
                    <li v-for="(e, i) in a.result.log" :key="i">{{ describeLogEntry(e) }}</li>
                  </ul>
                </li>
              </ul>
            </div>
            <button
              v-if="hasOlder"
              type="button"
              @click="loadOlder"
              class="w-full text-sm text-slate-400 hover:text-slate-200 py-2"
            >{{ t('agent.loadOlder') }}</button>
          </div>
        </template>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { agentApi } from '../services/api.js'
import LanguageSelector from '../components/LanguageSelector.vue'

const { t } = useI18n()

const POLL_MS = 2000
const FORM_STORAGE_KEY = 'kangame.agentForm'
const inputClass =
  'mt-1 w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-sky-500'

const form = reactive({ name: '', base_url: '', model: '', api_key: '' })
const config = ref(null)

// Blank key is allowed only when the server has its own key for the default provider.
const serverKeyUsable = computed(
  () => !!config.value?.has_server_key && trimUrl(form.base_url) === config.value.default_base_url,
)

function trimUrl(url) {
  return (url || '').trim().replace(/\/+$/, '')
}

function resetToDefaults() {
  if (!config.value) return
  form.base_url = config.value.default_base_url
  form.model = config.value.default_model
}

async function loadConfig() {
  try {
    config.value = (await agentApi.config()).data
    resetToDefaults()
  } catch {}
}
const formError = ref('')
const starting = ref(false)
const cancelling = ref(false)
const runs = ref([])
const selected = ref(null)
const actions = ref([])
const hasOlder = ref(false)
let pollTimer = null

const hasActiveRun = computed(() => runs.value.some((r) => isActive(r.status)))

const dayGroups = computed(() => {
  const byDay = new Map()
  for (const a of actions.value) {
    if (!byDay.has(a.day)) byDay.set(a.day, [])
    byDay.get(a.day).push(a)
  }
  return [...byDay.entries()]
    .sort((x, y) => y[0] - x[0])
    .map(([day, list]) => ({ day, actions: list.sort((x, y) => x.seq - y.seq) }))
})

function isActive(status) {
  return status === 'pending' || status === 'running'
}

function fmtRub(n) {
  return Number(n || 0).toLocaleString('ru-RU') + ' ₽'
}

function statusClass(status) {
  return {
    pending: 'bg-slate-700 text-slate-300',
    running: 'bg-sky-900 text-sky-300',
    completed: 'bg-emerald-900 text-emerald-300',
    failed: 'bg-red-900 text-red-300',
    cancelled: 'bg-amber-900 text-amber-300',
  }[status] || 'bg-slate-700 text-slate-300'
}

function actorClass(actor) {
  return { agent: 'text-violet-300', system: 'text-amber-300', human: 'text-sky-300' }[actor] || 'text-slate-400'
}

function errorText(err) {
  const detail = err?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((d) => `${(d.loc || []).slice(-1)[0]}: ${d.msg}`).join('; ')
  return detail || err?.message || 'Error'
}

function describe(a) {
  const args = a.arguments || {}
  const res = a.result || {}
  if (res.ok === false && res.error) return res.error
  switch (a.action) {
    case 'pull_card':
      return `${args.card_key}: ${args.from_col} → ${res.to_col}`
    case 'assign_worker':
      return `${args.worker_id} → ${args.card_key} (${res.outcome}${res.previous_card ? ` ← ${res.previous_card}` : ''})`
    case 'start_work': {
      const idle = args.idle_workers || []
      return `+${fmtRub(res.daily_revenue)} · Σ ${fmtRub(res.total_revenue)}${idle.length ? ` · idle: ${idle.join(', ')}` : ''}`
    }
    case 'end_day': {
      const overdue = (res.overdue || []).map((o) => o.card_key)
      return `${res.event_title || ''}${overdue.length ? ` · overdue: ${overdue.join(', ')}` : ''}`
    }
    case 'day_start':
      return a.state ? `Σ ${fmtRub(a.state.total_revenue)}` : ''
    case 'day_summary':
      return res.tool_calls != null ? `${res.tool_calls} tool calls` : ''
    case 'run_event':
      return [res.event, res.model, res.error].filter(Boolean).join(' · ')
    default:
      return ''
  }
}

function describeLogEntry(e) {
  if (e.type === 'work') return `${e.worker_id} → ${e.card_key} [${e.stage}] ${e.roll} = ${e.work}`
  if (e.type === 'advance') return `${e.card_key} → ${e.to}`
  if (e.type === 'deploy') return `${e.card_key} deployed`
  if (e.amount != null) return `${e.type} ${e.card_key} ${e.amount}`
  return `${e.type} ${e.card_key || ''} ${e.buff || ''}`.trim()
}

function loadSavedForm() {
  try {
    const saved = JSON.parse(localStorage.getItem(FORM_STORAGE_KEY) || '{}')
    for (const k of ['name', 'base_url', 'model']) if (saved[k]) form[k] = saved[k]
  } catch {}
}

function saveForm() {
  try {
    // Never persist the API key.
    localStorage.setItem(FORM_STORAGE_KEY, JSON.stringify({ name: form.name, base_url: form.base_url, model: form.model }))
  } catch {}
}

async function loadRuns() {
  try {
    runs.value = (await agentApi.listRuns()).data
  } catch {}
}

function applyRunMeta(run) {
  const { actions: _ignored, ...meta } = run
  selected.value = meta
  const idx = runs.value.findIndex((r) => r.id === meta.id)
  if (idx >= 0) runs.value[idx] = meta
}

async function selectRun(id) {
  stopPolling()
  actions.value = []
  hasOlder.value = false
  try {
    const run = (await agentApi.getRun(id)).data
    applyRunMeta(run)
    actions.value = run.actions
    hasOlder.value = run.actions.length > 0 && run.actions[0].seq > 1
  } catch {}
  schedulePoll()
}

async function poll() {
  if (!selected.value) return
  const lastSeq = actions.value.reduce((m, a) => Math.max(m, a.seq), 0)
  try {
    const run = (await agentApi.getRun(selected.value.id, { after_seq: lastSeq })).data
    applyRunMeta(run)
    const known = new Set(actions.value.map((a) => a.seq))
    actions.value = [...actions.value, ...run.actions.filter((a) => !known.has(a.seq))]
  } catch {}
  schedulePoll()
}

function schedulePoll() {
  stopPolling()
  if (selected.value && isActive(selected.value.status)) pollTimer = setTimeout(poll, POLL_MS)
}

function stopPolling() {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = null
}

async function loadOlder() {
  if (!selected.value || !actions.value.length) return
  const minSeq = actions.value.reduce((m, a) => Math.min(m, a.seq), Infinity)
  try {
    const older = (await agentApi.getActions(selected.value.id, { before_seq: minSeq, limit: 100 })).data
    actions.value = [...older, ...actions.value]
    hasOlder.value = older.length > 0 && older[0].seq > 1
  } catch {}
}

async function startRun() {
  formError.value = ''
  starting.value = true
  try {
    const payload = { name: form.name, base_url: trimUrl(form.base_url), model: form.model.trim() }
    if (form.api_key.trim()) payload.api_key = form.api_key.trim()
    const run = (await agentApi.createRun(payload)).data
    form.api_key = ''
    saveForm()
    runs.value = [run, ...runs.value]
    await selectRun(run.id)
  } catch (err) {
    formError.value = errorText(err)
  } finally {
    starting.value = false
  }
}

async function cancelRun() {
  if (!selected.value) return
  cancelling.value = true
  try {
    applyRunMeta((await agentApi.cancelRun(selected.value.id)).data)
    await poll()
  } catch (err) {
    formError.value = errorText(err)
  } finally {
    cancelling.value = false
  }
}

onMounted(async () => {
  await loadConfig()
  loadSavedForm()
  await loadRuns()
  const active = runs.value.find((r) => isActive(r.status))
  if (active || runs.value.length) await selectRun((active || runs.value[0]).id)
})

onBeforeUnmount(stopPolling)
</script>
