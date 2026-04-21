<template>
  <div class="key-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>密钥资产管理</span>
          <div class="header-actions">
            <el-input 
              v-model="searchQuery" 
              placeholder="搜索 API Key..." 
              class="search-input" 
              clearable 
              @clear="fetchKeys" 
              @keyup.enter="fetchKeys"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-button type="primary" @click="showAddDialog = true">新建密钥</el-button>
          </div>
        </div>
      </template>

      <el-table :data="keyList" style="width: 100%">
        <el-table-column prop="key_value" label="密钥凭证 (API Key)" min-width="280">
          <template #default="scope">
            <code class="key-code-simple">{{ scope.row.key_value }}</code>
            <el-button link type="primary" icon="CopyDocument" @click="copyKey(scope.row.key_value)" style="margin-left: 8px;" />
          </template>
        </el-table-column>
        <el-table-column label="可用 / 初始额度" width="180">
          <template #default="scope">
            <span :class="scope.row.remaining_quota < 1 ? 'text-danger' : 'text-success'" style="font-weight: bold;">
              {{ scope.row.remaining_quota.toFixed(1) }}
            </span>
            <span style="color: #909399;"> / {{ scope.row.initial_quota }}</span>
          </template>
        </el-table-column>
        <el-table-column label="最后活跃时间" width="200">
          <template #default="scope">
            <span v-if="scope.row.last_used_at">{{ formatTime(scope.row.last_used_at) }}</span>
            <el-tag v-else type="info" size="small">从未活跃</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280">
          <template #default="scope">
            <el-button size="small" @click="handleEditQuota(scope.row)">额度</el-button>
            <el-button size="small" @click="showLogs(scope.row)">流水</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="totalKeys"
          @size-change="fetchKeys"
          @current-change="fetchKeys"
        />
      </div>
    </el-card>

    <!-- 新建密钥对话框 (统一风格) -->
    <el-dialog v-model="showAddDialog" title="新建 API 密钥" width="500px">
      <el-form :model="addForm" label-width="120px">
        <el-form-item label="初始额度">
          <el-input-number v-model="addForm.initial_quota" :min="1" style="width: 100%" />
        </el-form-item>
        <div style="margin-left: 120px; color: #909399; font-size: 12px; margin-top: -10px;">
          创建后将从您的管理员余额中扣除对应点数。
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAdd" :loading="btnLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 额度调整对话框 (统一风格) -->
    <el-dialog v-model="showEditDialog" title="密钥额度调整" width="500px">
      <el-form label-width="120px">
        <el-form-item label="当前剩余">
          <el-input :value="selectedKey?.remaining_quota.toFixed(1)" disabled />
        </el-form-item>
        <el-form-item label="调整数额">
          <el-input-number v-model="quotaChange" :precision="1" style="width: 100%" />
        </el-form-item>
        <div style="margin-left: 120px; color: #909399; font-size: 12px; margin-top: -10px;">
          正数为增加（扣除您余额），负数为减少（退回您余额）。
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmEditQuota" :loading="btnLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 密钥日志抽屉 (统一风格) -->
    <el-drawer v-model="showLogsDrawer" :title="`密钥流水 [${selectedKey?.key_value?.substring(0,12)}...]`" size="60%">
      <div style="padding: 20px;">
        <el-table :data="keyLogs" border stripe>
          <el-table-column prop="request_time" label="时间" width="180">
            <template #default="scope">{{ formatTime(scope.row.request_time) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="scope">
              <el-tag :type="scope.row.is_success ? 'success' : 'danger'">{{ scope.row.is_success ? '成功' : '失败' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="quota_consumed" label="消耗" width="80" />
          <el-table-column prop="grok_server" label="服务器" show-overflow-tooltip />
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import request from '../utils/request';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search, CopyDocument } from '@element-plus/icons-vue'

const keyList = ref([]);
const totalKeys = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const searchQuery = ref('');
const showAddDialog = ref(false);
const showEditDialog = ref(false);
const showLogsDrawer = ref(false);
const btnLoading = ref(false);
const selectedKey = ref(null);
const quotaChange = ref(0);
const addForm = ref({ initial_quota: 100 });
const keyLogs = ref([]);

let searchTimer = null;
watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentPage.value = 1;
    fetchKeys();
  }, 300);
});

const fetchKeys = async () => {
  const data = await request.get('/admin/keys', { params: { page: currentPage.value, size: pageSize.value, query: searchQuery.value } });
  keyList.value = data.items;
  totalKeys.value = data.total;
};

const copyKey = (val) => { navigator.clipboard.writeText(val); ElMessage.success('已复制'); };
const formatTime = (t) => new Date(t).toLocaleString();

const confirmAdd = async () => {
  btnLoading.value = true;
  try {
    await request.post('/admin/keys', addForm.value);
    ElMessage.success('创建成功');
    showAddDialog.value = false;
    fetchKeys();
  } finally { btnLoading.value = false; }
};

const handleEditQuota = (row) => {
  selectedKey.value = row;
  quotaChange.value = 0;
  showEditDialog.value = true;
};

const confirmEditQuota = async () => {
  btnLoading.value = true;
  try {
    await request.patch(`/admin/keys/${selectedKey.value.id}`, { quota_change: quotaChange.value });
    ElMessage.success('调整成功');
    showEditDialog.value = false;
    fetchKeys();
  } finally { btnLoading.value = false; }
};

const showLogs = async (row) => {
  selectedKey.value = row;
  const data = await request.get(`/admin/keys/${row.id}/logs`);
  keyLogs.value = data;
  showLogsDrawer.value = true;
};

const handleDelete = (row) => {
  ElMessageBox.confirm('确定移除该密钥？').then(async () => {
    await request.delete(`/admin/keys/${row.id}`);
    fetchKeys();
  });
};

onMounted(fetchKeys);
</script>

<style scoped>
.key-container { padding: 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; gap: 10px; }
.search-input { width: 220px; }
.pagination-container { margin-top: 20px; display: flex; justify-content: flex-end; }
.key-code-simple { background: #f4f4f5; color: #606266; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
.text-success { color: #67C23A; }
.text-danger { color: #F56C6C; }
</style>
