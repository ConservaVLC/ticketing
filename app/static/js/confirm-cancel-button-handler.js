document.addEventListener('DOMContentLoaded', function() {
        const confirmModal = new bootstrap.Modal(document.getElementById('confirmChangesModal'));
        const modalConfirmButton = document.getElementById('modalConfirmButton');
        const modalCancelButton = document.getElementById('modalCancelButton'); // Nuevo: botón 'Cancelar' del modal
        
        // Variable para guardar la referencia al botón original de envío o la URL de cancelación
        let actionToPerform = null; 

        // --- Manejo de botones de Envío (ya lo tienes) ---
        const submitButtons = document.querySelectorAll('.confirm-submit-btn');
        submitButtons.forEach(button => {
            button.addEventListener('click', function(event) {
                event.preventDefault(); 
                // Almacenamos el botón de envío original para simular el clic más tarde
                actionToPerform = { type: 'submit', button: this }; 
                
                // Opcional: Si quieres la lógica de 'solo si hay cambios' (la compleja)
                // checkFormChanges(); 
                // if (formHasChanged) { confirmModal.show(); } else { this.closest('form').submit(); }
                
                confirmModal.show(); // Siempre muestra el modal para enviar
            });
        });

        // --- NUEVO: Manejo de botones/enlaces de Cancelar ---
        const cancelButtons = document.querySelectorAll('.confirm-cancel-btn');
        cancelButtons.forEach(button => {
            button.addEventListener('click', function(event) {
                event.preventDefault(); // Detiene la redirección por defecto
                // Almacenamos la URL de redirección del botón de cancelar
                actionToPerform = { type: 'redirect', url: this.href || '#' }; // Usa this.href si es un <a>, o un valor por defecto
                
                // El modal debería preguntar si desea *descartar* los cambios
                // Podrías cambiar dinámicamente el texto del modal aquí si fuera necesario
                document.getElementById('confirmChangesModalLabel').textContent = 'Confirmar Cancelación';
                document.querySelector('#confirmChangesModal .modal-body').textContent = '¿Desea descartar los cambios realizados?';

                confirmModal.show();
            });
        });

        // --- Lógica del botón "Confirmar" dentro del Modal ---
        modalConfirmButton.addEventListener('click', function() {
            confirmModal.hide(); 

            if (actionToPerform) {
                if (actionToPerform.type === 'submit') {
                    // Lógica para enviar el formulario (con tempButton.click())
                    const tempButton = document.createElement('button');
                    tempButton.style.display = 'none';
                    tempButton.type = 'submit';
                    actionToPerform.button.closest('form').appendChild(tempButton);
                    tempButton.click();
                    setTimeout(() => {
                        actionToPerform.button.closest('form').removeChild(tempButton);
                    }, 100);
                } else if (actionToPerform.type === 'redirect' && actionToPerform.url) {
                    window.location.href = actionToPerform.url; // Redirige a la URL almacenada
                }
            }
            // Restaurar texto original del modal para futuras interacciones
            document.getElementById('confirmChangesModalLabel').textContent = 'Confirmar Cambios';
            document.querySelector('#confirmChangesModal .modal-body').textContent = '¿Confirma que desea realizar estos cambios?';
        });
    });