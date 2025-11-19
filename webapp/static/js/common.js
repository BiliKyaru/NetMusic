// static/js/common.js

function triggerListRefresh(page = null) {
    handleListInteraction({ isSocketTrigger: true, page: page });
}

function copyLink(text, message) {
    const alertMessage = message || '内容已复制到剪贴板！';
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(() => showDynamicAlert(alertMessage, 'success'))
            .catch(err => showDynamicAlert('复制失败: ' + err, 'danger'));
    } else {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
            showDynamicAlert(alertMessage, 'success');
        } catch (err) {
            showDynamicAlert('复制失败，请手动复制。', 'danger');
        }
        document.body.removeChild(textArea);
    }
}

function showDynamicAlert(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toastId = 'toast-' + Date.now();
    const autoCloseDelay = 3000;
    const toastTypeClass = type === 'success' ? 'toast-success' : 'toast-danger';
    const iconClass = type === 'success' ? 'fa-solid fa-check-circle' : 'fa-solid fa-exclamation-circle';
    const title = type === 'success' ? '操作成功' : '操作失败';
    const toastHtml = `
        <div id="${toastId}" class="toast ${toastTypeClass}" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-icon"><i class="${iconClass}"></i></div>
            <div class="toast-body">
                <div class="toast-content"><strong>${title}</strong><span>${message}</span></div>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            <div class="toast-timer"></div>
        </div>`;
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = toastHtml;
    const toastEl = tempDiv.firstElementChild;
    container.prepend(toastEl);
    const toast = new bootstrap.Toast(toastEl, { autohide: false });
    let closeTimeout, remainingTime = autoCloseDelay, startTime;
    const startTimer = () => {
        startTime = Date.now();
        clearTimeout(closeTimeout);
        closeTimeout = setTimeout(() => toastEl.classList.add('hiding'), remainingTime);
    };
    const pauseTimer = () => {
        clearTimeout(closeTimeout);
        remainingTime -= (Date.now() - startTime);
    };
    toastEl.addEventListener('mouseenter', pauseTimer);
    toastEl.addEventListener('mouseleave', startTimer);
    toastEl.addEventListener('animationend', (e) => e.animationName === 'toast-slide-up' && toast.hide());
    toastEl.addEventListener('hide.bs.toast', (e) => {
        if (!toastEl.classList.contains('hiding')) {
            e.preventDefault();
            clearTimeout(closeTimeout);
            toastEl.classList.add('hiding');
        }
    });
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    toast.show();
    startTimer();
}

function initializeTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        const instance = bootstrap.Tooltip.getInstance(el);
        if (instance) instance.dispose();
    });
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
}

let newMusicIdsToHighlight = [];

document.addEventListener('DOMContentLoaded', () => {
    initializeTooltips();

    const messagesContainer = document.getElementById('flash-messages-data');
    if (messagesContainer) {
        const messages = messagesContainer.querySelectorAll('.flash-message');
        messages.forEach(msg => {
            const message = msg.dataset.message;
            const category = msg.dataset.category;
            if (message && category && typeof showDynamicAlert === 'function') {
                showDynamicAlert(message, category);
            }
        });
        messagesContainer.innerHTML = '';
    }

    if (typeof io !== 'undefined') {
        const socket = io({ transports: ['websocket'] });

        socket.on('music_added', (data) => {
            newMusicIdsToHighlight = data.new_ids;
            triggerListRefresh(1);
        });

        socket.on('upload_status', (data) => {
            if (data.message && data.category) {
                showDynamicAlert(data.message, data.category);
            }
        });

        socket.on('remove_music_items_batch', (data) => {
            const PER_PAGE = 20;
            const currentUrl = new URL(window.location);
            const currentPage = parseInt(currentUrl.searchParams.get('page') || '1');
            const totalPagesAfter = Math.max(1, Math.ceil(data.total_music_count_after / PER_PAGE));

            if (currentPage > totalPagesAfter) {
                triggerListRefresh(totalPagesAfter);
            }
            else {
                 triggerListRefresh(currentPage);
            }
        });
    }

    const musicListContainer = document.getElementById('music-list-container');
    if (musicListContainer) {
        musicListContainer.addEventListener('click', handleListInteraction);
        musicListContainer.addEventListener('submit', handleListInteraction);

        musicListContainer.addEventListener('input', (event) => {
            const searchInput = event.target.closest('input[name="q"]');
            if (searchInput && searchInput.value === '') {
                const searchForm = searchInput.closest('form.search-form-container');
                if (searchForm) {
                    const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
                    searchForm.dispatchEvent(submitEvent);
                }
            }
        });
    }
});

function handleListInteraction(event) {
    const isSocketTrigger = event && event.isSocketTrigger;
    const targetPage = event && event.page;
    const sortLink = !isSocketTrigger && event.target.closest('thead a');
    const searchForm = !isSocketTrigger && event.target.closest('form.search-form-container');
    const pageLink = !isSocketTrigger && event.target.closest('a.page-link');
    const filterLink = !isSocketTrigger && event.target.closest('a.file-type-filter');

    if (!isSocketTrigger && !sortLink && !(event.type === 'submit' && searchForm) && !pageLink && !filterLink) {
        return;
    }

    if (!isSocketTrigger) {
        event.preventDefault();
    }

    let targetUrl;
    const currentUrl = new URL(window.location);

    if (sortLink) {
        targetUrl = sortLink.href;
    } else if (pageLink) {
        targetUrl = pageLink.href;
    } else if (filterLink) {
        targetUrl = filterLink.href;
    } else if (searchForm && event.type === 'submit') {
        const searchInput = searchForm.querySelector('input[name="q"]');

        const typeInput = searchForm.querySelector('input[name="type"]');
        currentUrl.searchParams.set('q', searchInput.value);
        if (typeInput) {
             currentUrl.searchParams.set('type', typeInput.value);
        }

        currentUrl.searchParams.set('page', '1');
        targetUrl = currentUrl.toString();
    } else if (isSocketTrigger) {
        if (targetPage) {
            currentUrl.searchParams.set('page', String(targetPage));
        }
        targetUrl = currentUrl.toString();
    } else {
        return;
    }

    const musicTableBody = document.getElementById('music-list-body');
    if (musicTableBody) {
        musicTableBody.classList.add('fade-out');
    }

    setTimeout(() => {
        fetch(targetUrl, { headers: { 'X-Requested-with': 'XMLHttpRequest' } })
            .then(response => response.ok ? response.text() : Promise.reject('Network error'))

            .then(html => {

                const parser = new DOMParser();
                const newDoc = parser.parseFromString(html, 'text/html');
                const newCard = newDoc.querySelector('.card'); //

                const musicListContainer = document.getElementById('music-list-container');
                const oldCard = musicListContainer ? musicListContainer.querySelector('.card') : null;

                if (newCard && oldCard) {
                    const newHeader = newCard.querySelector('.card-header');
                    const oldHeader = oldCard.querySelector('.card-header');
                    if (newHeader && oldHeader) {
                        oldHeader.innerHTML = newHeader.innerHTML;
                    }

                    const newBody = newCard.querySelector('.card-body');
                    const oldBody = oldCard.querySelector('.card-body');
                    if (newBody && oldBody) {
                        oldBody.innerHTML = newBody.innerHTML;
                    }

                    const newFooter = newCard.querySelector('.card-footer');
                    const oldFooter = oldCard.querySelector('.card-footer');

                    if (newFooter && oldFooter) {
                        oldFooter.innerHTML = newFooter.innerHTML;
                    } else if (newFooter && !oldFooter) {
                        oldCard.appendChild(newFooter);
                    } else if (!newFooter && oldFooter) {
                        oldFooter.remove();
                    }
                } else if (musicListContainer) {
                    musicListContainer.innerHTML = html;
                }

                history.pushState({}, '', targetUrl);
                initializeTooltips();
                document.getElementById('music-list-container').dispatchEvent(new CustomEvent('listUpdated'));

                if (newMusicIdsToHighlight.length > 0) {
                    newMusicIdsToHighlight.forEach(id => {
                        const newRow = document.getElementById(`music-row-${id}`);
                        if (newRow) {
                            newRow.classList.add('new-item-highlight');
                            setTimeout(() => newRow.classList.remove('new-item-highlight'), 2500);
                        }
                    });
                    newMusicIdsToHighlight = [];
                }
            })

            .catch(error => {
                console.error('Error fetching music list:', error);
                showDynamicAlert('无法刷新音乐列表，请检查网络连接。', 'danger');
            })
            .finally(() => {
            });
    }, 300);
}

function previewMusic(url, title) {
    const playerBar = document.getElementById('global-player-bar');
    const audioEl = document.getElementById('global-audio-element');
    const titleEl = document.getElementById('player-song-title');

    if (!playerBar || !audioEl) return;

    playerBar.style.display = 'block';

    titleEl.textContent = title || '正在试听...';

    audioEl.src = url;
    audioEl.play()
        .catch(e => {
            console.error(e);
            showDynamicAlert('播放失败，可能是浏览器不支持该格式。', 'danger');
        });
}

function closePlayer() {
    const playerBar = document.getElementById('global-player-bar');
    const audioEl = document.getElementById('global-audio-element');

    if (audioEl) {
        audioEl.pause();
        audioEl.currentTime = 0; // 重置进度
    }

    if (playerBar) {
        playerBar.style.display = 'none';
    }
}