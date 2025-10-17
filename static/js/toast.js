function showToast(title, message, type = 'success') {
    const overlay = document.getElementById('toast-popup-overlay');
    if (!overlay) return;

    const content = document.getElementById('toast-popup-content');
    const toastTitle = document.getElementById('toast-popup-title');
    const toastMessage = document.getElementById('toast-popup-message');

    const iconSuccess = document.getElementById('toast-icon-success');
    const iconError = document.getElementById('toast-icon-error');

    toastTitle.textContent = title;
    toastMessage.textContent = message;

    content.className = 'toast-popup-content';
    content.classList.add(type);

    if (type === 'success') {
        iconSuccess.style.display = 'block';
        iconError.style.display = 'none';
    } else if (type === 'error') {
        iconSuccess.style.display = 'none';
        iconError.style.display = 'block';
    }

    overlay.classList.add('is-visible');

    setTimeout(() => {
        overlay.classList.remove('is-visible');
    }, 3000);
}