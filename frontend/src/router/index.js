import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import GameView from '../views/GameView.vue'
import DemoGameView from '../views/DemoGameView.vue'
import LeaderboardView from '../views/LeaderboardView.vue'
import { useAuthStore } from '../stores/authStore.js'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/game/:id', name: 'game', component: GameView, meta: { requiresAuth: true } },
  { path: '/demo', name: 'demo', component: DemoGameView },
  { path: '/leaderboard', name: 'leaderboard', component: LeaderboardView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  if (!to.meta.requiresAuth) return true

  const authStore = useAuthStore()
  if (!authStore.checked) {
    await authStore.fetchMe()
  }
  if (!authStore.isAuthenticated) {
    return '/'
  }
  return true
})

export default router
