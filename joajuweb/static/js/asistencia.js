(() => {
    const form = document.querySelector('#asistencia-form, #lista-inscritos');
    if (!form) return;
    const search = form.querySelector('#buscar-voluntario');
    const rows = Array.from(form.querySelectorAll('[data-voluntario]'));
    const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
    const filter = () => {
        const terms = normalize(search.value).split(/\s+/).filter(Boolean);
        let count = 0;
        rows.forEach(row => {
            row.hidden = !terms.every(term => normalize(row.dataset.busqueda).includes(term));
            if (!row.hidden) count += 1;
        });
        form.querySelector('#sin-coincidencias').hidden = count > 0 || rows.length === 0;
        form.querySelector('#resultados-asistencia').textContent = `${count} de ${rows.length} voluntarios`;
    };
    search.addEventListener('input', filter);
    form.querySelector('#marcar-presentes')?.addEventListener('click', () => {
        rows.forEach(row => { row.querySelector('input[value="presente"]').checked = true; });
    });
    // Revelar radios ocultos inválidos permite enfocarlos antes de guardar.
    form.addEventListener('invalid', event => {
        if (event.target.closest('[data-voluntario]')) {
            search.value = '';
            filter();
        }
    }, true);
    filter();
})();
