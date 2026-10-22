(() => {
    const button = document.querySelector('#agregar-jornada');
    if (!button) return;
    button.addEventListener('click', () => {
        const total = document.querySelector('#id_jornadas-TOTAL_FORMS');
        if (Number(total.value) >= 366) return;
        const html = document.querySelector('#jornada-vacia').innerHTML.replace(/__prefix__/g, total.value);
        document.querySelector('#jornadas-lista').insertAdjacentHTML('beforeend', html);
        total.value = String(Number(total.value) + 1);
    });
})();
