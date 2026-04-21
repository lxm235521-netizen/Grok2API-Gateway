<template>
  <div class="cluster-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Grok2API 集群管理</span>
          <el-button type="primary" @click="isEdit = false; addForm = { name: '', url: '', api_key: '', admin_password: '', is_active: true }; showAddDialog = true">添加节点</el-button>
        </div>
      </template>

      <el-table :data="serverList" style="width: 100%">
        <el-table-column prop="name" label="节点名称" />
        <el-table-column prop="url" label="服务器地址" />
        <el-table-column label="连接状态">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'success' ? 'success' : (scope.row.status === 'error' ? 'danger' : 'info')">
              {{ scope.row.status === 'success' ? '连接成功' : (scope.row.status === 'error' ? '连接失败' : '未检测') }}
            </el-tag>
            <span v-if="scope.row.status === 'success'" class="ml-10">({{ scope.row.token_count }} Token)</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="启用/禁用">
          <template #default="scope">
            <el-switch v-model="scope.row.is_active" @change="handleStatusChange(scope.row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="350">
          <template #default="scope">
            <el-button size="small" @click="checkNode(scope.row)" type="info" plain :loading="scope.row.status === 'checking'">刷新状态</el-button>
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" @click="handleShowTokens(scope.row)" :loading="scope.row.loading">Token 管理</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="showTokenDrawer" :title="`节点 [${selectedServer?.name}] Token 详情`" size="70%">
      <div class="drawer-actions">
        <el-button type="primary" @click="openImportDialog">批量导入</el-button>
        <el-button type="danger" @click="handleClearTokens" :loading="clearLoading">清空所有</el-button>
      </div>
      <el-table :data="tokenList" v-loading="drawerLoading">
        <el-table-column prop="pool" label="池子" width="100" />
        <el-table-column prop="token" label="Token" width="250" show-overflow-tooltip />
        <el-table-column prop="quota" label="额度" width="80" />
        <el-table-column prop="use_count" label="使用次数" width="100" />
        <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
                <el-tag :type="scope.row.status === 'active' ? 'success' : 'warning'">{{ scope.row.status }}</el-tag>
            </template>
        </el-table-column>
        <el-table-column prop="last_used_at" label="最后使用" width="160">
            <template #default="scope">
                {{ scope.row.last_used_at ? new Date(scope.row.last_used_at).toLocaleString() : '-' }}
            </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showImportDialog" title="批量导入 Token" width="500px">
      <el-form label-position="top">
        <el-form-item label="目标池子名称">
          <el-select v-model="importPool" placeholder="请选择或输入池子名称" filterable allow-create>
            <el-option label="ssoSuper (尊享)" value="ssoSuper" />
            <el-option label="ssoBasic (普通)" value="ssoBasic" />
            <el-option label="default (默认)" value="default" />
          </el-select>
          <div class="el-upload__tip">提示：ssoSuper 为高优先级池子</div>
        </el-form-item>
        <el-form-item label="导入方式">
          <el-radio-group v-model="importMode">
            <el-radio label="file">TXT 文件上传</el-radio>
            <el-radio label="json">JSON 文本</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <div v-if="importMode === 'file'" class="file-upload-area">
          <el-upload
            class="upload-demo"
            drag
            action=""
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept=".txt"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">将 TXT 文件拖到此处，或<em>点击上传</em></div>
            <template #tip>
              <div class="el-upload__tip">文件格式：每行一个 Token</div>
            </template>
          </el-upload>
        </div>
        
        <el-form-item v-if="importMode === 'json'" label="JSON 内容">
          <el-input v-model="importJson" type="textarea" :rows="10" placeholder='{"default": ["sso=xxx"]}' />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmImport" :loading="importLoading">确定导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showAddDialog" :title="isEdit ? '编辑集群节点' : '添加集群节点'">
      <el-form :model="addForm" label-width="120px">
        <el-form-item label="节点名称"><el-input v-model="addForm.name" /></el-form-item>
        <el-form-item label="API 地址"><el-input v-model="addForm.url" /></el-form-item>
        <el-form-item label="API Key"><el-input v-model="addForm.api_key" /></el-form-item>
        <el-form-item label="管理密码"><el-input v-model="addForm.admin_password" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import request from '../utils/request';
import { ElMessage, ElMessageBox } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue'

const serverList = ref([]);
const tokenList = ref([]);
const selectedServer = ref(null);
const showAddDialog = ref(false);
const isEdit = ref(false);
const showTokenDrawer = ref(false);
const showImportDialog = ref(false);
const drawerLoading = ref(false);
const clearLoading = ref(false);
const importMode = ref('file');
const importPool = ref('ssoSuper');
const importJson = ref('');
const importFile = ref(null);
const importLoading = ref(false);
const addForm = ref({ name: '', url: '', api_key: '', admin_password: '', is_active: true });

const fetchServers = async () => {
  const data = await request.get('/admin/grok-servers');
  serverList.value = data.map(s => ({ ...s, status: 'idle', loading: false }));
};

const checkNode = async (row) => {
  row.status = 'checking';
  try {
    const res = await request.get(`/admin/grok-servers/${row.id}/check`);
    row.status = res.status;
    row.token_count = res.token_count;
    if (res.status === 'error') ElMessage.error(res.detail);
  } catch (e) {
    row.status = 'error';
  }
};

const handleStatusChange = async (row) => {
  await request.patch(`/admin/grok-servers/${row.id}`, { is_active: row.is_active });
  ElMessage.success('状态更新成功');
};

const handleEdit = (server) => {
  isEdit.value = true;
  selectedServer.value = server;
  addForm.value = { ...server };
  showAddDialog.value = true;
};

const handleShowTokens = async (server) => {
  server.loading = true;
  drawerLoading.value = true;
  selectedServer.value = server;
  try {
    const data = await request.get(`/admin/grok-servers/${server.id}/tokens`);
    const allTokens = [];
    if (data?.tokens) {
      Object.keys(data.tokens).forEach(pool => {
        data.tokens[pool].forEach(t => allTokens.push({ pool, ...t }));
      });
    }
    tokenList.value = allTokens;
    showTokenDrawer.value = true;
  } catch (e) {
    ElMessage.error('获取 Token 失败');
  } finally {
    server.loading = false;
    drawerLoading.value = false;
  }
};

const openImportDialog = () => {
  importJson.value = '';
  importFile.value = null;
  importMode.value = 'file';
  showImportDialog.value = true;
};

const handleFileChange = (file) => {
  importFile.value = file.raw;
};

const confirmImport = async () => {
  importLoading.value = true;
  try {
    let payload = {};
    if (importMode.value === 'file') {
      if (!importFile.value) {
        ElMessage.warning('请先选择文件');
        importLoading.value = false;
        return;
      }
      const text = await importFile.value.text();
      const tokens = text.split('\n').map(line => line.trim()).filter(line => line);
      if (tokens.length === 0) {
        ElMessage.warning('文件内容为空');
        importLoading.value = false;
        return;
      }
      payload[importPool.value] = tokens;
    } else {
      try {
        payload = JSON.parse(importJson.value);
      } catch (e) {
        ElMessage.error('JSON 格式错误');
        importLoading.value = false;
        return;
      }
    }

    await request.post(`/admin/grok-servers/${selectedServer.value.id}/tokens/import`, payload);
    ElMessage.success('导入成功');
    showImportDialog.value = false;
    handleShowTokens(selectedServer.value);
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.message || '未知错误'));
  } finally {
    importLoading.value = false;
  }
};

const handleClearTokens = () => {
  ElMessageBox.confirm('确定清空该节点下所有池子的 Token 吗？此操作不可逆！', '危险操作', { 
    type: 'warning',
    confirmButtonText: '确定清空',
    cancelButtonText: '取消'
  }).then(async () => {
    clearLoading.value = true;
    try {
      await request.post(`/admin/grok-servers/${selectedServer.value.id}/tokens/clear`);
      ElMessage.success('已发送清空指令');
      // 延迟 1s 刷新，给后端处理存储的时间
      setTimeout(() => {
        handleShowTokens(selectedServer.value);
      }, 1000);
    } catch (e) {
      ElMessage.error('清空失败');
    } finally {
      clearLoading.value = false;
    }
  });
};

const confirmAdd = async () => {
  if (isEdit.value) await request.patch(`/admin/grok-servers/${selectedServer.value.id}`, addForm.value);
  else await request.post('/admin/grok-servers', addForm.value);
  showAddDialog.value = false;
  fetchServers();
};

const handleDelete = (server) => {
  ElMessageBox.confirm('移除该节点？').then(async () => {
    await request.delete(`/admin/grok-servers/${server.id}`);
    fetchServers();
  });
};

onMounted(fetchServers);
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.ml-10 { margin-left: 10px; }
.drawer-actions { margin-bottom: 20px; }
.file-upload-area { margin: 10px 0; }
</style>
