(() => {
    const form = document.querySelector('#selector-jornada-form');
    const select = document.querySelector('#jornada');
    if (!form || !select) return;

    const attendance = document.querySelector('#asistencia-form');
    const radios = Array.from(attendance?.querySelectorAll('input[type="radio"]') || []);
    const marks = () => radios.map(input => input.checked ? '1' : '0').join('');
    const initialMarks = marks();
    const currentDay = select.dataset.jornadaActual || select.value;

    form.addEventListener('submit', event => {
        if (marks() === initialMarks) return;
        const confirmed = window.confirm(
            'Tenés cambios de asistencia sin guardar. Si cambiás de jornada, se perderán. ¿Querés continuar?'
        );
        if (!confirmed) {
            event.preventDefault();
            select.value = currentDay;
        }
    });

    // requestSubmit conserva el envío GET y la protección de cambios sin guardar.
    select.addEventListener('change', () => form.requestSubmit());
})();
