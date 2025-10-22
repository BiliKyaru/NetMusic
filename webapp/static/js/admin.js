// static/js/admin.js

let isUploading = false;
let selectedMusicIds = new Set();

document.addEventListener('DOMContentLoaded', () => {
    initAdminInteractions();
});

function initAdminInteractions() {
    const musicListContainer = document.getElementById('music-list-container');
    if (musicListContainer) {
        musicListContainer.addEventListener('click', (event) => {
            const target = event.target;
            if (target.id === 'select-all-music') {
                handleSelectAll(target.checked);
                updateAllUIStates();
            } else if (target.id === 'batch-delete-btn') {
                handleBatchDelete();
            }
        });

        musicListContainer.addEventListener('change', (event) => {
             if (event.target.classList.contains('music-item-checkbox')) {
                const checkbox = event.target;
                const musicId = parseInt(checkbox.value);
                if (checkbox.checked) {
                    selectedMusicIds.add(musicId);
                } else {
                    selectedMusicIds.delete(musicId);
                }
                updateAllUIStates();
            }
        });

        musicListContainer.addEventListener('listUpdated', () => {
            reapplySelections();
            updateAllUIStates();
        });

        function updateAllUIStates() {
            updateSelectAllCheckboxState();
            updateBatchDeleteButtonState();
        }
        reapplySelections();
        updateAllUIStates();
    }

    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) uploadForm.addEventListener('submit', handleAjaxUpload);

    const usernameForm = document.getElementById('username-change-form');
    if (usernameForm) usernameForm.addEventListener('submit', handleAccountFormSubmit);

    const passwordForm = document.getElementById('password-change-form');
    if (passwordForm) passwordForm.addEventListener('submit', handleAccountFormSubmit);

    const accountTabs = document.querySelector('#accountTabs');
    if (accountTabs) {
        const tabTriggers = accountTabs.querySelectorAll('button[data-bs-toggle="tab"]');
        tabTriggers.forEach(tabTrigger => {
            tabTrigger.addEventListener('shown.bs.tab', event => {
                const tabId = event.target.id;
                const tabName = tabId.split('-')[0];

                const url = new URL(window.location);
                url.searchParams.set('tab', tabName);

                history.pushState({}, '', url);
            });
        });
    }

    window.addEventListener('beforeunload', (event) => {
        if (isUploading || hasUnsavedChangesInAccountForms()) {
            event.preventDefault();
            event.returnValue = '';
        }
    });
}

function hasUnsavedChangesInAccountForms() {
    const usernameInput = document.getElementById('new_username_input');
    const passwordInputs = document.querySelectorAll('#password-change-form input.form-control');

    if (usernameInput && usernameInput.value.trim() !== '') {
        return true;
    }

    for (const input of passwordInputs) {
        if (input.value.trim() !== '') {
            return true;
        }
    }

    return false;
}

function reapplySelections() {
    document.querySelectorAll('.music-item-checkbox').forEach(checkbox => {
        const musicId = parseInt(checkbox.value);
        checkbox.checked = selectedMusicIds.has(musicId);
    });
}

function handleAccountFormSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner-border');

    submitBtn.disabled = true;
    const originalBtnText = btnText.textContent;
    btnText.textContent = '正在处理...';
    spinner.style.display = 'inline-block';

    fetch(form.action, { method: 'POST', body: new FormData(form) })
    .then(response => response.json())
    .then(data => {
        data.messages.forEach(msg => showDynamicAlert(msg.message, msg.category));
        if (data.success) {
            form.querySelectorAll('input.form-control').forEach(input => { input.value = ''; });
        }
    })
    .catch(error => {
        console.error('Account update error:', error);
        showDynamicAlert('操作失败，请检查网络连接。', 'danger');
    })
    .finally(() => {
        submitBtn.disabled = false;
        btnText.textContent = originalBtnText;
        spinner.style.display = 'none';
    });
}

function handleAjaxUpload(event) {
    event.preventDefault();
    const form = event.target;
    const submitBtn = document.getElementById('upload-submit-btn');
    const btnText = document.getElementById('upload-btn-text');
    const spinner = document.getElementById('upload-spinner');
    const fileInput = document.getElementById('file');
    if (fileInput.files.length === 0) {
        showDynamicAlert('请先选择要上传的文件。', 'danger');
        return;
    }
    isUploading = true;
    submitBtn.disabled = true;
    btnText.textContent = '正在上传...';
    spinner.style.display = 'inline-block';
    fetch(form.action, { method: 'POST', body: new FormData(form) })
    .then(response => response.json())
    .then(data => {
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach(msg => showDynamicAlert(msg.message, msg.category));
        }
        fileInput.value = '';
    })
    .catch(error => {
        console.error('Upload Error:', error);
        showDynamicAlert('上传失败，请检查网络连接。', 'danger');
    })
    .finally(() => {
        isUploading = false;
        submitBtn.disabled = false;
        btnText.textContent = '开始上传';
        spinner.style.display = 'none';
    });
}

function handleSelectAll(isChecked) {
    const visibleCheckboxes = document.querySelectorAll('.music-item-checkbox');
    visibleCheckboxes.forEach(checkbox => {
        checkbox.checked = isChecked;
        const musicId = parseInt(checkbox.value);
        if (isChecked) {
            selectedMusicIds.add(musicId);
        } else {
            selectedMusicIds.delete(musicId);
        }
    });
}

function updateSelectAllCheckboxState() {
    const selectAllCheckbox = document.getElementById('select-all-music');
    if (!selectAllCheckbox) return;
    const itemCheckboxes = document.querySelectorAll('.music-item-checkbox');
    const totalCount = itemCheckboxes.length;
    const checkedCount = document.querySelectorAll('.music-item-checkbox:checked').length;
    if (totalCount === 0) {
        selectAllCheckbox.checked = false;
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.disabled = true;
    } else {
        selectAllCheckbox.disabled = false;
        const allChecked = totalCount === checkedCount;
        selectAllCheckbox.checked = allChecked;
        selectAllCheckbox.indeterminate = !allChecked && checkedCount > 0;
    }
}

function updateBatchDeleteButtonState() {
    const batchDeleteBtn = document.getElementById('batch-delete-btn');
    if (!batchDeleteBtn) return;
    const totalSelectedCount = selectedMusicIds.size;

    // 按钮的可见性现在只取决于 totalSelectedCount
    if (totalSelectedCount > 0) {
        batchDeleteBtn.style.display = 'inline-block';
        batchDeleteBtn.textContent = `删除选中 (${totalSelectedCount})`;
    } else {
        batchDeleteBtn.style.display = 'none';
    }
}

function handleBatchDelete() {
    const selectedIds = Array.from(selectedMusicIds);
    if (selectedIds.length === 0) return;

    if (confirm(`确定要删除选中的 ${selectedIds.length} 首音乐吗？`)) {
        const currentUrl = new URL(window.location);
        const currentPage = parseInt(currentUrl.searchParams.get('page') || '1');

        const csrfTokenInput = document.querySelector('input[name="csrf_token"]');
        if (!csrfTokenInput) {
            showDynamicAlert('安全令牌丢失，请刷新页面后重试。', 'danger');
            return;
        }

        fetch('/delete/batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfTokenInput.value
            },
            body: JSON.stringify({
                music_ids: selectedIds,
                current_page: currentPage
            })
        })
        .then(response => {
            if (!response.ok && response.status !== 207) {
                throw new Error(`服务器响应错误，状态码: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // 显示准确的操作结果
            showDynamicAlert(data.message, data.success ? 'success' : 'danger');

            // 清除客户端的选择状态
            selectedMusicIds.clear();

            // 安全地调用全局函数刷新列表
            triggerListRefresh(data.redirect_page);
        })
        .catch(error => {
            // 这个 catch 块只在发生真实的网络或服务器内部错误时触发
            console.error('批量删除时发生网络或服务器错误:', error);
            showDynamicAlert('批量删除操作失败，请检查网络或服务器状态。', 'danger');
        });
    }
}