// 应用初始化
document.addEventListener('DOMContentLoaded', () => {
    if (api.isAuthenticated()) {
        showAppPage();
    } else {
        showAuthPage();
    }

    setupDragAndDrop();
    preloadRuleDocuments();
});

// 缓存制度文件列表
let _ruleDocumentsCache = null;

async function preloadRuleDocuments() {
    try {
        _ruleDocumentsCache = await api.get('/api/rules/documents');
    } catch {
        _ruleDocumentsCache = [];
    }
}

function resolveDocumentPath(sourceDocument) {
    if (!sourceDocument || !_ruleDocumentsCache?.length) return null;
    const match = _ruleDocumentsCache.find(f => f.name.startsWith(sourceDocument));
    return match ? match.path : null;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function documentSuffixIcon(suffix) {
    const map = {
        '.pdf': '📄', '.docx': '📘', '.doc': '📘',
        '.xlsx': '📗', '.xls': '📗',
        '.pptx': '📙', '.ppt': '📙',
    };
    return map[suffix] || '📎';
}

// 页面切换
function showAuthPage() {
    document.getElementById('auth-page').classList.add('active');
    document.getElementById('app-page').classList.remove('active');
}

function showAppPage() {
    document.getElementById('auth-page').classList.remove('active');
    document.getElementById('app-page').classList.add('active');

    // 显示用户信息
    document.getElementById('username-display').textContent = api.user.username;
    const roleBadge = document.getElementById('role-badge');
    roleBadge.textContent = api.user.role === 'admin' ? '管理员' : '用户';

    // 显示管理员菜单
    if (api.isAdmin()) {
        document.querySelectorAll('.admin-only').forEach(el => {
            el.style.display = 'block';
        });
    }

    // 加载任务列表
    refreshTasks();
}

// 认证标签切换
function switchAuthTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if ((tab === 'login' && btn.textContent === '登录') || (tab === 'register' && btn.textContent === '注册')) {
            btn.classList.add('active');
        }
    });

    document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
    document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
}

// 处理登录
async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const errorDiv = document.getElementById('login-error');

    try {
        const user = await api.post('/api/auth/login', { username, password });
        api.setUser(user, user.access_token);
        errorDiv.textContent = '';
        showAppPage();
    } catch (error) {
        errorDiv.textContent = error.message;
    }
}

// 处理注册
async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('register-username').value;
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;
    const errorDiv = document.getElementById('register-error');

    if (password !== confirm) {
        errorDiv.textContent = '两次输入的密码不一致';
        return;
    }

    try {
        await api.post('/api/auth/register', { username, password });
        errorDiv.textContent = '注册成功，请登录';
        switchAuthTab('login');
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
        document.querySelectorAll('.tab-btn')[1].classList.remove('active');
    } catch (error) {
        errorDiv.textContent = error.message;
    }
}

// 处理退出登录
function handleLogout() {
    api.logout();
}

// 标签页切换
function switchTab(tabName) {
    // 更新导航菜单
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(tabName)) {
            item.classList.add('active');
        }
    });

    // 切换内容区域
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // 加载对应内容
    switch (tabName) {
        case 'tasks':
            refreshTasks();
            break;
        case 'rules':
            refreshRules();
            break;
        case 'sync':
            refreshSyncStatus();
            break;
    }
}

// 自动刷新定时器
let autoRefreshInterval = null;

// 刷新任务列表
async function refreshTasks() {
    const container = document.getElementById('tasks-list');
    if (!container.classList.contains('active-parent')) {
        container.innerHTML = '<div class="loading">加载中...</div>';
    }

    try {
        const tasks = await api.get('/api/tasks');
        if (tasks.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无任务记录</p></div>';
            return;
        }

        container.innerHTML = tasks.map(task => `
            <div class="task-card" onclick="showTaskDetails(${task.id})">
                <div class="task-header">
                    <span class="task-id">任务 #${task.id}</span>
                    <span class="status-badge status-${task.status}" data-task-id="${task.id}">${getStatusText(task.status)}</span>
                </div>
                <div class="task-info">
                    <div>批次名称: ${task.batch_name}</div>
                    <div>文件数量: ${task.file_count}</div>
                    <div>创建时间: ${formatDateTime(task.created_at)}</div>
                    ${task.completed_at ? `<div>完成时间: ${formatDateTime(task.completed_at)}</div>` : ''}
                    ${task.status === 'parsing' ? '<div style="color: var(--primary-color);">⏳ 正在处理中，请稍候...</div>' : ''}
                    ${task.status === 'failed' && task.error_message ? `<div style="color: var(--danger-color);">❌ ${task.error_message}</div>` : ''}
                </div>
            </div>
        `).join('');

        // 如果有处理中的任务，启动自动刷新
        const hasParsingTask = tasks.some(t => t.status === 'parsing' || t.status === 'pending');
        if (hasParsingTask && !autoRefreshInterval) {
            autoRefreshInterval = setInterval(() => {
                // 只在任务管理标签页时刷新
                if (document.getElementById('tasks-tab').classList.contains('active')) {
                    refreshTasks();
                }
            }, 10000);
        } else if (!hasParsingTask && autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
    } catch (error) {
        container.innerHTML = `<div class="error-message">加载失败: ${error.message}</div>`;
    }
}

// 显示任务详情
async function showTaskDetails(taskId) {
    event.stopPropagation();
    try {
        const task = await api.get(`/api/tasks/${taskId}`);
        const details = document.getElementById('task-details');

        details.innerHTML = `
            <div class="task-info">
                <div><strong>任务ID:</strong> ${task.id}</div>
                <div><strong>批次名称:</strong> ${task.batch_name}</div>
                <div><strong>状态:</strong> <span class="status-badge status-${task.status}">${getStatusText(task.status)}</span></div>
                <div><strong>文件数量:</strong> ${task.file_count}</div>
                <div><strong>创建时间:</strong> ${formatDateTime(task.created_at)}</div>
                <div><strong>完成时间:</strong> ${task.completed_at ? formatDateTime(task.completed_at) : '-'}</div>
                ${task.error_message ? `<div><strong>错误信息:</strong> ${task.error_message}</div>` : ''}
            </div>
            ${task.status === 'completed' ? `
                <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
                    <button class="btn btn-primary" onclick="viewReport(${taskId})">查看报告</button>
                    <button class="btn btn-secondary" onclick="viewFields(${taskId})">查看字段</button>
                    <button class="btn btn-danger" onclick="deleteTask(${taskId})">删除任务</button>
                </div>
            ` : ''}
        `;

        document.getElementById('task-modal').classList.add('active');
    } catch (error) {
        alert('加载任务详情失败: ' + error.message);
    }
}

// 查看报告
async function viewReport(taskId) {
    try {
        const report = await api.get(`/api/tasks/${taskId}/report`);
        const container = document.getElementById('report-container');

        // 简单渲染 Markdown
        const renderedReport = renderMarkdown(report);
        container.innerHTML = `
            <div class="report-actions" style="margin-bottom: 1rem;">
                <button class="btn btn-secondary" onclick="switchTab('tasks')">返回列表</button>
                <button class="btn btn-primary" onclick="downloadReport(${taskId})">下载报告</button>
            </div>
            <div class="report-content">
                ${renderedReport}
            </div>
        `;

        switchTab('reports');
    } catch (error) {
        alert('加载报告失败: ' + error.message);
    }
}

// 查看字段提取结果
async function viewFields(taskId) {
    try {
        const fields = await api.get(`/api/tasks/${taskId}/fields`);
        const container = document.getElementById('report-container');

        let fieldsHtml = '<h3>字段提取结果</h3>';
        fields.forEach(field => {
            fieldsHtml += `
                <div style="margin: 1rem 0; padding: 1rem; background: var(--bg-color); border-radius: 6px;">
                    <strong>${field.filename}</strong>
                    <pre style="margin-top: 0.5rem; white-space: pre-wrap; font-family: monospace; font-size: 0.875rem;">${field.content}</pre>
                </div>
            `;
        });

        container.innerHTML = `
            <div class="report-actions" style="margin-bottom: 1rem;">
                <button class="btn btn-secondary" onclick="switchTab('tasks')">返回列表</button>
            </div>
            ${fieldsHtml}
        `;

        switchTab('reports');
    } catch (error) {
        alert('加载字段数据失败: ' + error.message);
    }
}

// 下载报告
async function downloadReport(taskId) {
    try {
        const report = await api.get(`/api/tasks/${taskId}/report`);
        const blob = new Blob([report], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `审核报告_任务${taskId}.md`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        alert('下载报告失败: ' + error.message);
    }
}

// 删除任务
async function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务吗？')) return;

    try {
        await api.delete(`/api/tasks/${taskId}`);
        closeModal('task-modal');
        refreshTasks();
        alert('任务已删除');
    } catch (error) {
        alert('删除任务失败: ' + error.message);
    }
}

// 拖拽上传
function setupDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    let selectedFiles = [];

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        selectedFiles = Array.from(files);
        updateFileList();
        document.getElementById('upload-btn').disabled = selectedFiles.length === 0;
    }

    function updateFileList() {
        const fileList = document.getElementById('file-list');
        fileList.innerHTML = selectedFiles.map(file => `
            <div class="file-item">
                <span>${file.name}</span>
                <span>${formatFileSize(file.size)}</span>
            </div>
        `).join('');
    }

    window.uploadFiles = async function() {
        if (selectedFiles.length === 0) return;

        const uploadBtn = document.getElementById('upload-btn');
        uploadBtn.disabled = true;
        uploadBtn.textContent = '上传中...';

        // 显示进度提示
        showProgress('上传文件', '正在上传并处理文件，请稍候...');

        try {
            const result = await api.uploadFiles(selectedFiles);
            updateProgress(`上传成功！任务ID: ${result.task_id}`);

            // 开始轮询任务状态
            pollTaskStatus(result.task_id);

            selectedFiles = [];
            updateFileList();
            uploadBtn.disabled = true;
            uploadBtn.textContent = '开始上传';
        } catch (error) {
            hideProgress();
            alert('上传失败: ' + error.message);
            uploadBtn.disabled = false;
            uploadBtn.textContent = '开始上传';
        }
    };
}

// 规则管理
async function refreshRules(filterCategory = null) {
    const container = document.getElementById('rules-list');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        let rules;
        if (filterCategory) {
            rules = await api.get(`/api/rules?category=${encodeURIComponent(filterCategory)}`);
        } else {
            rules = await api.get('/api/rules');
        }

        const categories = await api.get('/api/rules/categories');

        if (rules.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>暂无规则</p></div>';
            return;
        }

        // 按分类分组
        const groupedRules = {};
        rules.forEach(rule => {
            if (!groupedRules[rule.category]) {
                groupedRules[rule.category] = [];
            }
            groupedRules[rule.category].push(rule);
        });

        let html = `
            <div class="rules-summary" style="margin-bottom: 1rem; padding: 1rem; background: var(--bg-color); border-radius: 6px;">
                <strong>审核标准总览</strong>
                <p>共 ${categories.length} 个分类，${rules.length} 条审核规则</p>
            </div>
            <div class="category-filters" style="margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">
                <button class="btn btn-secondary" onclick="refreshRules()" style="padding: 0.5rem 1rem; font-size: 0.875rem;">全部</button>
                ${categories.map(cat => `
                    <button class="btn btn-secondary" onclick="refreshRules('${cat}')" style="padding: 0.5rem 1rem; font-size: 0.875rem;">${cat}</button>
                `).join('')}
            </div>
        `;

        // 显示每个分类的规则
        for (const [category, categoryRules] of Object.entries(groupedRules)) {
            html += `
                <div class="rule-category" style="margin-bottom: 2rem;">
                    <h3 style="margin-bottom: 1rem; color: var(--primary-color);">${category} (${categoryRules.length} 条)</h3>
                    <div class="tasks-container">
                        ${categoryRules.map(rule => `
                            <div class="task-card" onclick="showRuleDetails(${rule.id})">
                                <div class="task-header">
                                    <span class="task-id">${rule.rule_name}</span>
                                    <div style="display: flex; gap: 0.5rem;">
                                        <span class="status-badge ${getLevelBadgeClass(rule.level)}">${rule.level}风险</span>
                                        <span class="status-badge ${rule.enabled ? 'status-completed' : 'status-failed'}">
                                            ${rule.enabled ? '启用' : '禁用'}
                                        </span>
                                    </div>
                                </div>
                                <div class="task-info">
                                    <div>条款引用: ${rule.clause}</div>
                                    <div>规则描述: ${rule.description ? rule.description.substring(0, 100) + (rule.description.length > 100 ? '...' : '') : '无描述'}</div>
                                    <div>来源文档: ${rule.source_document ?
                                        `<a href="javascript:void(0)" onclick="event.stopPropagation(); openRuleDocument('${rule.source_document}')" style="color: var(--primary-color); text-decoration: underline; cursor: pointer;">${rule.source_document}</a>` :
                                        '手动添加'
                                    }</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    } catch (error) {
        container.innerHTML = `<div class="error-message">加载失败: ${error.message}</div>`;
    }
}

function getLevelBadgeClass(level) {
    switch (level) {
        case '高': return 'status-failed';
        case '中': return 'status-pending';
        case '低': return 'status-completed';
        case '提示': return 'status-parsing';
        default: return 'status-pending';
    }
}

// 显示规则详情
async function showRuleDetails(ruleId) {
    event.stopPropagation();
    try {
        const rule = await api.get(`/api/rules/${ruleId}`);
        const details = document.getElementById('task-details');

        let expressionInfo = '无检查表达式';
        if (rule.check_expression) {
            try {
                const expr = JSON.parse(rule.check_expression);
                expressionInfo = `<pre style="background: var(--bg-color); padding: 0.5rem; border-radius: 4px; font-family: monospace; font-size: 0.875rem;">${JSON.stringify(expr, null, 2)}</pre>`;
            } catch {
                expressionInfo = rule.check_expression;
            }
        }

        details.innerHTML = `
            <div class="task-info">
                <div><strong>规则名称:</strong> ${rule.rule_name}</div>
                <div><strong>所属分类:</strong> ${rule.category}</div>
                <div><strong>条款引用:</strong> ${rule.clause}</div>
                <div><strong>风险等级:</strong> <span class="status-badge ${getLevelBadgeClass(rule.level)}">${rule.level}</span></div>
                <div><strong>规则描述:</strong> ${rule.description || '无描述'}</div>
                <div><strong>来源文档:</strong> ${rule.source_document ?
                    `<a href="javascript:void(0)" onclick="openRuleDocument('${rule.source_document}')" style="color: var(--primary-color); text-decoration: underline; cursor: pointer;">${rule.source_document}</a>` :
                    '手动添加'
                }</div>
                <div><strong>检查表达式:</strong><br>${expressionInfo}</div>
                <div><strong>创建时间:</strong> ${formatDateTime(rule.created_at)}</div>
                <div><strong>更新时间:</strong> ${formatDateTime(rule.updated_at)}</div>
            </div>
            ${api.isAdmin() ? `
                <div style="margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <button class="btn btn-primary" onclick="editRule(${ruleId})">编辑规则</button>
                    <button class="btn ${rule.enabled ? 'btn-secondary' : 'btn-success'}" onclick="toggleRuleEnabled(${ruleId}, ${!rule.enabled})">
                        ${rule.enabled ? '禁用规则' : '启用规则'}
                    </button>
                    <button class="btn btn-danger" onclick="deleteRule(${ruleId})">删除规则</button>
                </div>
            ` : ''}
        `;

        document.getElementById('task-modal').classList.add('active');
    } catch (error) {
        alert('加载规则详情失败: ' + error.message);
    }
}

// 打开规则来源文档
function openRuleDocument(sourceDocument) {
    const path = resolveDocumentPath(sourceDocument);
    if (!path) {
        alert(`未找到文档: ${sourceDocument}`);
        return;
    }
    window.open(`/api/rules/documents/${encodeURIComponent(path)}`, '_blank');
}

// 编辑规则
async function editRule(ruleId) {
    closeModal('task-modal');
    const rule = await api.get(`/api/rules/${ruleId}`);

    // 填充表单
    document.getElementById('rule-category').value = rule.category;
    document.getElementById('rule-name').value = rule.rule_name;
    document.getElementById('rule-clause').value = rule.clause;
    document.getElementById('rule-level').value = rule.level;
    document.getElementById('rule-description').value = rule.description || '';

    // 修改表单提交处理
    const form = document.getElementById('rule-form');
    form.onsubmit = async (e) => {
        e.preventDefault();
        try {
            await api.put(`/api/rules/${ruleId}`, {
                category: document.getElementById('rule-category').value,
                rule_name: document.getElementById('rule-name').value,
                clause: document.getElementById('rule-clause').value,
                level: document.getElementById('rule-level').value,
                description: document.getElementById('rule-description').value,
            });
            closeModal('rule-modal');
            refreshRules();
            alert('规则更新成功');
            // 恢复原始表单处理
            form.onsubmit = addRule;
        } catch (error) {
            alert('更新规则失败: ' + error.message);
        }
    };

    document.querySelector('#rule-modal .modal-header h3').textContent = '编辑审核规则';
    document.getElementById('rule-modal').classList.add('active');
}

// 切换规则启用状态
async function toggleRuleEnabled(ruleId, enabled) {
    try {
        await api.put(`/api/rules/${ruleId}`, { enabled });
        refreshRules();
        alert(`规则已${enabled ? '启用' : '禁用'}`);
    } catch (error) {
        alert('操作失败: ' + error.message);
    }
}

// 删除规则
async function deleteRule(ruleId) {
    if (!confirm('确定要删除这条规则吗？')) return;

    try {
        await api.delete(`/api/rules/${ruleId}`);
        closeModal('task-modal');
        refreshRules();
        alert('规则已删除');
    } catch (error) {
        alert('删除规则失败: ' + error.message);
    }
}

// 显示新增规则模态框
function showAddRuleModal() {
    document.getElementById('rule-modal').classList.add('active');
}

// 添加规则
async function addRule(e) {
    e.preventDefault();

    const ruleData = {
        category: document.getElementById('rule-category').value,
        rule_name: document.getElementById('rule-name').value,
        clause: document.getElementById('rule-clause').value,
        level: document.getElementById('rule-level').value,
        description: document.getElementById('rule-description').value,
    };

    try {
        await api.post('/api/rules', ruleData);
        closeModal('rule-modal');
        refreshRules();
        alert('规则添加成功');
        document.getElementById('rule-form').reset();
    } catch (error) {
        alert('添加规则失败: ' + error.message);
    }
}

// 制度同步
async function refreshSyncStatus() {
    const container = document.getElementById('sync-status');
    container.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const status = await api.get('/api/rules/sync/status');
        container.innerHTML = `
            <div class="sync-info" style="padding: 1rem; background: var(--bg-color); border-radius: 6px; margin-bottom: 1rem;">
                <h3>同步状态</h3>
                <p>待处理变更: ${status.pending_changes} 个</p>
            </div>
            <h3>制度文档</h3>
            <div class="tasks-container">
                ${status.documents.map(doc => `
                    <div class="task-card">
                        <div class="task-header">
                            <span class="task-id">${doc.name}</span>
                            <span class="status-badge ${doc.status === 'synced' ? 'status-completed' : 'status-pending'}">
                                ${doc.status}
                            </span>
                        </div>
                        <div class="task-info">
                            <div>上次同步: ${doc.last_sync ? new Date(doc.last_sync).toLocaleString() : '未同步'}</div>
                            ${doc.diff_summary ? `<div>差异摘要: ${doc.diff_summary}</div>` : ''}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        container.innerHTML = `<div class="error-message">加载失败: ${error.message}</div>`;
    }
}

// 手动触发同步
async function triggerSync() {
    if (!confirm('确定要手动触发制度文件同步吗？')) return;

    try {
        const result = await api.post('/api/rules/sync');
        alert(result.detail);
        refreshSyncStatus();
    } catch (error) {
        alert('同步失败: ' + error.message);
    }
}

// 轮询任务状态
let pollInterval = null;

async function pollTaskStatus(taskId) {
    const maxAttempts = 100;
    let attempts = 0;

    pollInterval = setInterval(async () => {
        try {
            const task = await api.get(`/api/tasks/${taskId}`);
            attempts++;

            if (task.status === 'parsing') {
                const elapsed = attempts * 10;
                updateProgress(`正在OCR识别和处理文件，已等待 ${elapsed} 秒...`);
            } else if (task.status === 'completed') {
                clearInterval(pollInterval);
                updateProgress('审核完成！');
                setTimeout(() => {
                    hideProgress();
                    switchTab('tasks');
                    refreshTasks();
                    alert(`任务完成！共处理 ${task.file_count} 个文件`);
                }, 500);
            } else if (task.status === 'failed') {
                clearInterval(pollInterval);
                updateProgress(`处理失败: ${task.error_message || '未知错误'}`);
                setTimeout(() => {
                    hideProgress();
                    switchTab('tasks');
                    refreshTasks();
                }, 1000);
            }

            if (attempts >= maxAttempts) {
                clearInterval(pollInterval);
                hideProgress();
                alert('任务处理时间较长，请在"任务管理"中查看状态');
                switchTab('tasks');
                refreshTasks();
            }
        } catch (error) {
            clearInterval(pollInterval);
            hideProgress();
            alert('查询任务状态失败: ' + error.message);
        }
    }, 10000);
}

// 进度提示
function showProgress(title, message) {
    let progressDiv = document.getElementById('progress-overlay');
    if (!progressDiv) {
        progressDiv = document.createElement('div');
        progressDiv.id = 'progress-overlay';
        progressDiv.innerHTML = `
            <div class="progress-modal">
                <div class="progress-spinner"></div>
                <h3 id="progress-title">${title}</h3>
                <p id="progress-message">${message}</p>
                <div class="progress-bar">
                    <div class="progress-bar-fill"></div>
                </div>
                <button class="btn btn-secondary" onclick="skipWaiting()" style="margin-top: 1rem;">暂不等待，去任务列表</button>
            </div>
        `;
        document.body.appendChild(progressDiv);
    } else {
        document.getElementById('progress-title').textContent = title;
        document.getElementById('progress-message').textContent = message;
    }
    progressDiv.classList.add('active');
}

function skipWaiting() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
    hideProgress();
    switchTab('tasks');
    refreshTasks();
}

function updateProgress(message) {
    const msgEl = document.getElementById('progress-message');
    if (msgEl) msgEl.textContent = message;
}

function hideProgress() {
    const progressDiv = document.getElementById('progress-overlay');
    if (progressDiv) {
        progressDiv.classList.remove('active');
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }
}
function getStatusText(status) {
    const statusMap = {
        'pending': '等待处理',
        'parsing': '识别中',
        'completed': '已完成',
        'failed': '失败',
    };
    return statusMap[status] || status;
}

function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return '-';
    try {
        const date = new Date(dateTimeStr);
        return date.toLocaleString('zh-CN');
    } catch {
        return dateTimeStr;
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function renderMarkdown(text) {
    // 简单的 Markdown 渲染
    return text
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// 点击模态框外部关闭
window.onclick = function(event) {
    if (event.target.classList.contains('modal') && event.target === event.currentTarget) {
        event.target.classList.remove('active');
    }
}

// 阻止模态框内容区域的点击穿透
document.addEventListener('click', function(e) {
    if (e.target.closest('.modal-content')) {
        e.stopPropagation();
    }
});
