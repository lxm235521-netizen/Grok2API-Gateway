<template>
  <div class="login-wrapper">
    <!-- 动态渐变背景 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
    </div>

    <el-card class="login-card" shadow="always">
      <div class="login-header">
        <div class="logo-area">
          <el-icon class="logo-icon"><Platform /></el-icon>
        </div>
        <h1 class="platform-name">黑马API</h1>
        <p class="platform-subtitle">Grok2 网关管理平台</p>
      </div>

      <el-form 
        :model="loginForm" 
        @submit.prevent="handleLogin" 
        class="login-form"
        label-position="top"
      >
        <el-form-item>
          <el-input 
            v-model="loginForm.username" 
            placeholder="请输入管理员账号" 
            :prefix-icon="User"
            size="large"
            class="custom-input"
          />
        </el-form-item>
        <el-form-item>
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入登录密码" 
            :prefix-icon="Lock" 
            show-password 
            size="large"
            class="custom-input"
          />
        </el-form-item>
        
        <div class="form-options">
          <el-checkbox v-model="rememberMe">记住我</el-checkbox>
          <el-link type="primary" :underline="false">忘记密码？</el-link>
        </div>

        <el-form-item>
          <el-button 
            type="primary" 
            class="submit-btn" 
            :loading="loading" 
            @click="handleLogin"
            size="large"
          >
            立即登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <p>© 2026 黑马API-Grok2 网关平台 · 极速分布式路由</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { User, Lock, Platform } from '@element-plus/icons-vue'

const router = useRouter();
const loading = ref(false);
const rememberMe = ref(true);
const loginForm = ref({ username: '', password: '' });

const handleLogin = async () => {
  if (!loginForm.value.username || !loginForm.value.password) {
    ElMessage.warning('请填写完整的账号和密码');
    return;
  }
  
  loading.value = true;
  try {
    const formData = new FormData();
    formData.append('username', loginForm.value.username);
    formData.append('password', loginForm.value.password);
    
    // 保持原有逻辑不变
    const response = await axios.post('/token', formData);
    const token = response.data.access_token;
    localStorage.setItem('token', token);
    localStorage.setItem('username', loginForm.value.username);
    
    // 登录后获取当前登录用户自己的信息
    const userRes = await axios.get('/api/admin/me', {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    localStorage.setItem('role', userRes.data.role);
    ElMessage.success({
      message: '欢迎回来，管理员',
      type: 'success',
      duration: 2000
    });
    router.push('/dashboard');
  } catch (error) {
    ElMessage.error('登录失败：账号或密码验证未通过');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  width: 100vw;
  background-color: #f0f2f5;
  background-image: radial-gradient(at 0% 0%, hsla(210, 100%, 95%, 1) 0, transparent 50%),
                    radial-gradient(at 50% 0%, hsla(220, 100%, 92%, 1) 0, transparent 50%),
                    radial-gradient(at 100% 0%, hsla(230, 100%, 95%, 1) 0, transparent 50%);
  overflow: hidden;
  position: relative;
}

/* 背景装饰 */
.bg-decoration {
  position: absolute;
  width: 100%;
  height: 100%;
  z-index: 0;
}
.circle {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
}
.circle-1 {
  width: 400px;
  height: 400px;
  background: #409EFF;
  top: -100px;
  left: -100px;
}
.circle-2 {
  width: 300px;
  height: 300px;
  background: #67C23A;
  bottom: -50px;
  right: -50px;
}

.login-card {
  width: 420px;
  border-radius: 16px;
  border: none;
  z-index: 1;
  padding: 20px 10px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08) !important;
}

.login-header {
  text-align: center;
  margin-bottom: 35px;
}

.logo-area {
  display: inline-flex;
  padding: 12px;
  background: #f0f7ff;
  border-radius: 12px;
  margin-bottom: 15px;
}
.logo-icon {
  font-size: 32px;
  color: #409EFF;
}

.platform-name {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
  letter-spacing: 1px;
}
.platform-subtitle {
  font-size: 14px;
  color: #909399;
  margin: 8px 0 0;
  letter-spacing: 2px;
}

.login-form {
  margin-top: 20px;
}

.custom-input :deep(.el-input__wrapper) {
  background-color: #f5f7fa;
  box-shadow: none !important;
  border: 1px solid transparent;
  transition: all 0.3s;
  border-radius: 8px;
}
.custom-input :deep(.el-input__wrapper.is-focus) {
  border-color: #409EFF;
  background-color: #fff;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding: 0 4px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  background: linear-gradient(90deg, #409EFF, #3a8ee6);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: all 0.3s;
}
.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.4);
}

.login-footer {
  margin-top: 30px;
  text-align: center;
  font-size: 12px;
  color: #c0c4cc;
}
</style>
