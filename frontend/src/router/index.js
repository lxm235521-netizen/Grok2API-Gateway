import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../layout/MainLayout.vue'
import Login from '../views/Login.vue'
import KeyManagement from '../views/KeyManagement.vue'
import UserManagement from '../views/UserManagement.vue'

import ClusterManagement from '../views/ClusterManagement.vue'
import Dashboard from '../views/Dashboard.vue'

const routes = [
  { path: '/login', component: Login },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: Dashboard },
      { path: 'keys', component: KeyManagement },
      { path: 'users', component: UserManagement },
      { path: 'cluster', component: ClusterManagement }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
