// flash_handler.js
document.addEventListener('DOMContentLoaded', function() {
    var flashMessages = document.getElementById('flash-messages');
    if (flashMessages) {
        setTimeout(function() {
            flashMessages.style.opacity = '0';
            setTimeout(function() {
                flashMessages.remove();
            }, 500);
        }, 5000);
    }
});