<template>
  <div class="user-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统用户管理</span>
          <div class="header-actions">
            <el-input 
              v-model="searchQuery" 
              placeholder="搜索用户名" 
              class="search-input" 
              clearable 
              @clear="fetchUsers" 
              @keyup.enter="fetchUsers"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" @click="showAddDialog = true">添加账号</el-button>
          </div>
        </div>
      </template>

      <el-table :data="userList" style="width: 100%">
        <el-table-column prop="username" label="管理账号" />
        <el-table-column label="权限角色">
          <template #default="scope">
            <el-tag :type="scope.row.role === 'super_admin' ? 'danger' : 'success'">
              {{ scope.row.role === 'super_admin' ? '超级管理员' : '普通管理员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="balance" label="账户可用余额">
          <template #default="scope">
            {{ scope.row.balance.toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column label="注册时间">
          <template #default="scope">
            {{ formatTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300">
          <template #default="scope">
            <el-button size="small" @click="handleAdjustBalance(scope.row)">调整额度</el-button>
            <el-button size="small" @click="showUserDetails(scope.row)">详情</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)" :disabled="scope.row.role === 'super_admin'">移除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="totalUsers"
          @size-change="fetchUsers"
          @current-change="fetchUsers"
        />
      </div>
    </el-card>

    <!-- 添加用户对话框 (统一风格) -->
    <el-dialog v-model="showAddDialog" title="新增管理账号" width="500px">
      <el-form :model="addForm" label-width="120px">
        <el-form-item label="用户名"><el-input v-model="addForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="addForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="分配角色">
          <el-select v-model="addForm.role" style="width: 100%">
            <el-option label="普通管理员" value="admin" />
            <el-option label="超级管理员" value="super_admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始余额">
          <el-input-number v-model="addForm.balance" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAddUser" :loading="btnLoading">确认</el-button>
      </template>
    </el-dialog>

    <!-- 额度调整对话框 (统一风格) -->
    <el-dialog v-model="adjustVisible" title="账户额度调整" width="500px">
      <el-form label-width="120px">
        <el-form-item label="目标用户">
          <el-input :value="selectedUser?.username" disabled />
        </el-form-item>
        <el-form-item label="当前余额">
          <el-input :value="selectedUser?.balance.toFixed(1)" disabled />
        </el-form-item>
        <el-form-item label="调整数额">
          <el-input-number v-model="adjustAmount" :precision="1" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAdjust" :loading="btnLoading">确定</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailsVisible" :title="`成员详情: ${selectedUser?.username}`" size="60%">
      <div style="padding: 20px;">
        <h3>名下 API 密钥</h3>
        <el-table :data="userKeys" border>
          <el-table-column prop="key_value" label="API Key" show-overflow-tooltip />
          <el-table-column label="余额" width="120">
            <template #default="scope">{{ scope.row.remaining_quota.toFixed(1) }}</template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '活跃' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import request from '../utils/request';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search } from '@element-plus/icons-vue'

const userList = ref([]);
const totalUsers = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const searchQuery = ref('');
const showAddDialog = ref(false);
const adjustVisible = ref(false);
const detailsVisible = ref(false);
const btnLoading = ref(false);
const selectedUser = ref(null);
const adjustAmount = ref(0);
const userKeys = ref([]);
const addForm = ref({ username: '', password: '', role: 'admin', balance: 0 });

let searchTimer = null;
watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentPage.value = 1;
    fetchUsers();
  }, 300);
});

const fetchUsers = async () => {
  const data = await request.get('/admin/users', { params: { page: currentPage.value, size: pageSize.value, username: searchQuery.value } });
  userList.value = data.items;
  totalUsers.value = data.total;
};

const formatTime = (t) => new Date(t).toLocaleString();

const handleAdjustBalance = (user) => { selectedUser.value = user; adjustAmount.value = 0; adjustVisible.value = true; };
const confirmAdjust = async () => {
  btnLoading.value = true;
  try {
    await request.post('/admin/users/add-balance', { user_id: selectedUser.value.id, amount: adjustAmount.value });
    ElMessage.success('更新成功');
    adjustVisible.value = false;
    fetchUsers();
  } finally { btnLoading.value = false; }
};

const showUserDetails = async (user) => {
  selectedUser.value = user;
  const data = await request.get(`/admin/users/${user.id}/keys`);
  userKeys.value = data;
  detailsVisible.value = true;
};

const confirmAddUser = async () => {
  btnLoading.value = true;
  try {
    await request.post('/admin/users', addForm.value);
    ElMessage.success('添加成功');
    showAddDialog.value = false;
    fetchUsers();
  } finally { btnLoading.value = false; }
};

const handleDelete = (user) => {
  ElMessageBox.confirm(`确定移除用户 ${user.username}？`).then(async () => {
    await request.delete(`/admin/users/${user.id}`);
    fetchUsers();
  });
};

onMounted(fetchUsers);
</script>

<style scoped>
.user-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; gap: 10px; }
.search-input { width: 220px; }
.pagination-container { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>
