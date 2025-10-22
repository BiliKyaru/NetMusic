// static/js/login.js

document.addEventListener('DOMContentLoaded', function() {
    const lockoutEndIsoString = loginData.lockoutEnd;
    const loginForm = document.getElementById('login-form');
    const countdownMessage = document.getElementById('countdown-message');
    let timer;

    if (lockoutEndIsoString) {
        const lockoutEndDate = new Date(lockoutEndIsoString);

        if (!isNaN(lockoutEndDate)) {
            Array.from(loginForm.elements).forEach(el => el.disabled = true);

            function updateCountdown() {
                const now = new Date();
                const distance = lockoutEndDate.getTime() - now.getTime();

                if (distance < 0) {
                    clearInterval(timer);
                    const alertContainer = document.getElementById('alert-container');
                    if (alertContainer) {
                        alertContainer.innerHTML = `<div class="alert alert-success" role="alert">锁定已解除，请刷新页面重试。</div>`;
                    }
                    setTimeout(() => window.location.reload(), 1500);
                    return;
                }

                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                if (countdownMessage) {
                    countdownMessage.textContent = `登录尝试过多，请在 ${minutes}分 ${seconds}秒 后重试。`;
                }
            }

            updateCountdown();
            timer = setInterval(updateCountdown, 1000);
        } else {
            if (countdownMessage) {
                countdownMessage.textContent = '无法解析锁定时间，请稍后刷新。';
            }
        }
    }
});