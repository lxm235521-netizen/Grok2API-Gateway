<template>
  <el-container class="layout-container">
    <el-aside width="200px">
      <el-menu :router="true" :default-active="$route.path" class="el-menu-vertical">
        <el-menu-item index="/dashboard">
          <el-icon><DataLine /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/users" v-if="userRole === 'super_admin'">
          <el-icon><User /></el-icon>
          <span>用户管理</span>
        </el-menu-item>
        <el-menu-item index="/cluster" v-if="userRole === 'super_admin'">
          <el-icon><Connection /></el-icon>
          <span>集群管理</span>
        </el-menu-item>
        <el-menu-item index="/keys">
          <el-icon><Key /></el-icon>
          <span>密钥管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-left">Grok2API 管理网关</div>
        <div class="header-right">
          <span>{{ username }} ({{ userRole === 'super_admin' ? '超管' : '管理员' }})</span>
          <el-button type="text" @click="logout">退出</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const username = ref(localStorage.getItem('username') || 'User');
const userRole = ref(localStorage.getItem('role') || 'admin');

const logout = () => {
  localStorage.clear();
  router.push('/login');
};
</script>

<style scoped>
.layout-container { height: 100vh; }
.el-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #ddd; }
.header-right { display: flex; align-items: center; gap: 20px; }
</style>
