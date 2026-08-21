import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/login', name: 'login', component: () => import('../pages/LoginPage.vue'), meta: { public: true } },
    { path: '/', redirect: '/bugs' },
    { path: '/bugs', name: 'bugs', component: () => import('../pages/BugsPage.vue') },
    { path: '/bugs/:id', name: 'bug-detail', component: () => import('../pages/BugDetailPage.vue') },
    { path: '/todos', name: 'todos', component: () => import('../pages/TodosPage.vue') },
    { path: '/notifications', name: 'notifications', component: () => import('../pages/NotificationsPage.vue') },
    { path: '/cases', name: 'cases', component: () => import('../pages/CasesPage.vue') },
    { path: '/cases/:id', name: 'case-document', component: () => import('../pages/CaseDocumentPage.vue') },
    { path: '/requirements', name: 'requirements', component: () => import('../pages/RequirementsPage.vue') },
    { path: '/requirements/:id', name: 'requirement-detail', component: () => import('../pages/RequirementDetailPage.vue') },
    { path: '/reports/testing', name: 'reports', component: () => import('../pages/ReportsPage.vue') },
    { path: '/profile', name: 'profile', component: () => import('../pages/ProfilePage.vue') },
    { path: '/admin/:section?', name: 'admin', component: () => import('../pages/AdminPage.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/bugs' },
  ],
})

export default router
