<template>
  <div class="dashboard-container">
    <!-- 统计卡片区 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="24" class="mb-15">
        <el-radio-group v-model="statDays" @change="fetchData" size="small">
          <el-radio-button :label="1">今日</el-radio-button>
          <el-radio-button :label="7">近7天</el-radio-button>
          <el-radio-button :label="30">近30天</el-radio-button>
        </el-radio-group>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6" v-for="(item, index) in statItems" :key="index">
        <el-card shadow="hover" class="stat-card-modern" :class="item.type">
          <div class="card-content">
            <div class="stat-info">
              <div class="stat-title">{{ item.title }}</div>
              <div class="stat-value">
                <span v-if="item.key === 'balance' && stats.balance === -1" class="infinite-badge">∞ 无限</span>
                <span v-else>{{ formatValue(stats[item.key]) }}</span>
              </div>
            </div>
            <div class="stat-icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 节点统计区 (仅超管) -->
    <el-card v-if="stats.server_stats?.length > 0" class="modern-card mt-20">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon><Monitor /></el-icon>
            <span>节点今日负载</span>
          </div>
        </div>
      </template>
      <el-table :data="stats.server_stats" style="width: 100%" size="default">
        <el-table-column prop="server" label="服务器地址" min-width="200">
           <template #default="scope"><code class="server-code">{{ scope.row.server }}</code></template>
        </el-table-column>
        <el-table-column prop="total" label="总请求" width="120" align="center" />
        <el-table-column prop="video" label="视频成功" width="120" align="center" />
        <el-table-column prop="fail" label="异常数" width="120" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.fail > 0 ? 'danger' : 'success'" round>{{ scope.row.fail }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 日志列表区 (带分页) -->
    <el-card class="modern-card mt-20">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon><List /></el-icon>
            <span>最近请求流水</span>
          </div>
          <el-button type="primary" size="default" icon="Refresh" @click="fetchData">刷新日志</el-button>
        </div>
      </template>
      <el-table :data="logs" style="width: 100%" size="default" stripe>
        <el-table-column label="API Key" width="150">
          <template #default="scope">
            <el-tooltip :content="scope.row.api_key?.key_value" placement="top">
              <span class="key-preview">{{ scope.row.api_key?.key_value?.substring(0, 12) }}...</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="grok_server" label="目标节点" show-overflow-tooltip min-width="180" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.is_success ? 'success' : 'danger'" size="small" @click="!scope.row.is_success && showDetail(scope.row)" class="status-tag">
              {{ scope.row.is_success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="250" show-overflow-tooltip>
          <template #default="scope">
            <span v-if="!scope.row.is_success" class="error-msg">{{ scope.row.details || '未知错误' }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100" align="center">
          <template #default="scope">{{ scope.row.duration.toFixed(1) }}s</template>
        </el-table-column>
        <el-table-column label="消耗" width="100" align="center">
          <template #default="scope">{{ scope.row.quota_consumed.toFixed(1) }}</template>
        </el-table-column>
        <el-table-column prop="request_time" label="请求时间" width="170" align="center">
          <template #default="scope">{{ formatTime(scope.row.request_time) }}</template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container mt-20">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="totalLogs"
          @size-change="fetchLogs"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>

    <el-dialog v-model="videoVisible" title="视频预览" width="800px" destroy-on-close>
      <div class="video-container"><video :src="currentVideo" controls autoplay class="video-player"></video></div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import request from '../utils/request';
import { ElMessageBox, ElMessage } from 'element-plus';
import { Refresh, Monitor, List, PieChart, VideoCamera, Warning, Wallet } from '@element-plus/icons-vue'

const stats = ref({ total_count: 0, video_count: 0, fail_count: 0, balance: 0, server_stats: [] });
const statDays = ref(1);
const logs = ref([]);
const totalLogs = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const videoVisible = ref(false);
const currentVideo = ref('');

const statItems = [
  { title: '今日总请求', key: 'total_count', type: 'primary', icon: PieChart },
  { title: '视频生成数', key: 'video_count', type: 'success', icon: VideoCamera },
  { title: '异常请求数', key: 'fail_count', type: 'danger', icon: Warning },
  { title: '可用额度', key: 'balance', type: 'warning', icon: Wallet }
];

const fetchData = async () => {
  const sData = await request.get('/admin/dashboard/stats', { params: { days: statDays.value } });
  stats.value = sData;
  fetchLogs();
};

const fetchLogs = async () => {
  const lData = await request.get('/admin/dashboard/logs', { params: { page: currentPage.value, size: pageSize.value } });
  logs.value = lData.items;
  totalLogs.value = lData.total;
};

const formatValue = (val) => typeof val === 'number' ? val.toLocaleString() : val;
const formatTime = (t) => new Date(t).toLocaleString('zh-CN', { hour12: false });

const showDetail = (row) => {
  ElMessageBox.alert(row.details || '无异常明细', '详情', { confirmButtonText: '确定' });
};

const playVideo = (url) => {
  if (!url || !url.startsWith('http')) return ElMessage.warning('链接无效');
  currentVideo.value = url;
  videoVisible.value = true;
};

onMounted(fetchData);
</script>

<style scoped>
/* 保持之前的样式，增加分页容器样式 */
.pagination-container { display: flex; justify-content: flex-end; }
/* ... (其他样式同前) */
.mb-15 { margin-bottom: 15px; }
.dashboard-container { padding: 5px; }
.stat-card-modern { border: none; border-radius: 12px; transition: all 0.3s cubic-bezier(.25,.8,.25,1); overflow: hidden; position: relative; margin-bottom: 15px; }
.stat-card-modern:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.1) !important; }
.card-content { display: flex; justify-content: space-between; align-items: center; padding: 10px 5px; }
.stat-title { font-size: 13px; color: #8492a6; margin-bottom: 8px; font-weight: 500; }
.stat-value { font-size: 26px; font-weight: 700; color: #1f2f3d; }
.stat-icon { font-size: 32px; opacity: 0.15; }
.primary { border-left: 4px solid #409EFF; background: linear-gradient(135deg, #fff 0%, #f0f7ff 100%); }
.success { border-left: 4px solid #67C23A; background: linear-gradient(135deg, #fff 0%, #f0f9eb 100%); }
.danger  { border-left: 4px solid #F56C6C; background: linear-gradient(135deg, #fff 0%, #fef0f0 100%); }
.warning { border-left: 4px solid #E6A23C; background: linear-gradient(135deg, #fff 0%, #fdf6ec 100%); }
.infinite-badge { background: #409EFF; color: #fff; font-size: 14px; padding: 2px 10px; border-radius: 20px; }
.modern-card { border-radius: 12px; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
.card-header { display: flex; justify-content: space-between; align-items: center; border: none; }
.header-title { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 600; color: #303133; }
.server-code { background: #f4f4f5; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #606266; }
.error-msg { color: #F56C6C; font-size: 13px; }
.key-preview { color: #409EFF; font-weight: 500; }
.status-tag { cursor: pointer; transition: opacity 0.2s; }
.quota-value { color: #67C23A; font-weight: 600; }
.video-container { background: #000; border-radius: 8px; overflow: hidden; line-height: 0; }
.video-player { width: 100%; max-height: 70vh; }
.mt-20 { margin-top: 20px; }
</style>
