// 共通ユーティリティ関数

// トースト通知を表示
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ファイルサイズをフォーマット
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// 日時をフォーマット
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// API呼び出しのヘルパー
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'APIエラーが発生しました');
        }

        return await response.json();
    } catch (error) {
        console.error('API呼び出しエラー:', error);
        throw error;
    }
}

// ローディング表示
function showLoading(element) {
    element.disabled = true;
    element.innerHTML = '<span class="loading inline-block">⏳</span> 処理中...';
}

function hideLoading(element, originalText) {
    element.disabled = false;
    element.innerHTML = originalText;
}

// グローバルエラーハンドラー
window.addEventListener('error', (event) => {
    console.error('エラー:', event.error);
});

// グローバルPromiseエラーハンドラー
window.addEventListener('unhandledrejection', (event) => {
    console.error('未処理のPromiseエラー:', event.reason);
});
