document.addEventListener('DOMContentLoaded', function() {
    const confirmModalElement = document.getElementById('confirmChangesModal');
    if (!confirmModalElement) return;

    const confirmModal = new bootstrap.Modal(confirmModalElement);
    const modalConfirmButton = document.getElementById('modalConfirmButton');

    let actionToPerform = null;

    document.body.addEventListener('click', function(event) {
        const submitBtn = event.target.closest('.confirm-submit-btn');
        if (submitBtn) {
            event.preventDefault();
            actionToPerform = { button: submitBtn };

            const modalTitle = submitBtn.dataset.modalTitle || 'Confirmar Cambios';
            const modalBody = submitBtn.dataset.modalBody || '¿Confirma que desea realizar estos cambios?';
            
            document.getElementById('confirmChangesModalLabel').textContent = modalTitle;
            document.querySelector('#confirmChangesModal .modal-body').textContent = modalBody;

            confirmModal.show();
        }
    });

    if (modalConfirmButton) {
        modalConfirmButton.addEventListener('click', function() {
            if (!actionToPerform || !actionToPerform.button) return;

            const button = actionToPerform.button;
            confirmModal.hide();

            if (button.classList.contains('submit-via-dynamic-form')) {
                const url = button.dataset.url;
                const token = button.dataset.token;
                if (!url || !token) {
                    console.error('Dynamic form submission requires data-url and data-token attributes.');
                    return;
                }

                const form = document.createElement('form');
                form.method = 'POST';
                form.action = url;
                const csrfInput = document.createElement('input');
                csrfInput.type = 'hidden';
                csrfInput.name = 'csrf_token';
                csrfInput.value = token;
                form.appendChild(csrfInput);
                document.body.appendChild(form);
                form.submit();

            } else {
                const form = button.closest('form');
                if (form) {
                    const tempButton = document.createElement('button');
                    tempButton.style.display = 'none';
                    tempButton.type = 'submit';
                    form.appendChild(tempButton);
                    tempButton.click();
                    setTimeout(() => {
                        if (tempButton.parentNode === form) {
                            form.removeChild(tempButton);
                        }
                    }, 100);
                }
            }
            
            actionToPerform = null;

            setTimeout(() => {
                document.getElementById('confirmChangesModalLabel').textContent = 'Confirmar Cambios';
                document.querySelector('#confirmChangesModal .modal-body').textContent = '¿Confirma que desea realizar estos cambios?';
            }, 500);
        });
    }
});