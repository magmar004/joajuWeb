const CIUDADES_CENTRAL = [
    'Areguá',
    'Capiatá',
    'Fernando de la Mora',
    'Guarambaré',
    'Itá',
    'Itauguá',
    'Julián Augusto Saldívar',
    'Lambaré',
    'Limpio',
    'Luque',
    'Mariano Roque Alonso',
    'Nueva Italia',
    'Ñemby',
    'San Antonio',
    'San Lorenzo',
    'Villa Elisa',
    'Villeta',
    'Ypacaraí',
    'Ypané'
];

function normalizar(texto) {
    return (texto || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase().trim();
}

document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-city-department]').forEach(function (group) {
        const departamento = document.getElementById(group.dataset.cityDepartment);
        const campoManual = document.getElementById(group.dataset.cityManual);
        const ciudadCentral = document.getElementById(group.dataset.cityCentral);
        const manualWrapper = group.querySelector('[data-city-manual-wrapper]');
        const centralWrapper = group.querySelector('[data-city-central-wrapper]');
        const etiqueta = group.parentElement.querySelector('label[for="' + group.dataset.cityManual + '"]');

        if (!departamento || !campoManual || !ciudadCentral || !manualWrapper || !centralWrapper) {
            return;
        }

        const ciudadesPresentes = new Set(Array.from(ciudadCentral.options).map(function (opcion) {
            return normalizar(opcion.value);
        }));
        const opcionLegada = ciudadCentral.querySelector('[data-legacy-city="true"]');
        CIUDADES_CENTRAL.forEach(function (nombre) {
            if (ciudadesPresentes.has(normalizar(nombre))) return;
            const opcion = document.createElement('option');
            opcion.value = nombre;
            opcion.textContent = nombre;
            ciudadCentral.insertBefore(opcion, opcionLegada || null);
        });

        const nombreCampo = campoManual.name;
        const requerido = group.dataset.cityRequired === 'true';
        let modoCentralActivo = false;
        let modoAsuncionActivo = false;
        let ciudadManualAnterior = '';

        function buscarOpcion(valor) {
            const clave = normalizar(valor);
            if (!clave) return null;
            return Array.from(ciudadCentral.options).find(function (opcion) {
                return normalizar(opcion.value) === clave;
            }) || null;
        }

        function actualizarCiudad() {
            const esCentral = departamento.value === group.dataset.centralDepartment;
            const esAsuncion = departamento.value === 'asuncion';

            if (esCentral) {
                if (modoAsuncionActivo) {
                    campoManual.value = ciudadManualAnterior;
                    campoManual.readOnly = false;
                    modoAsuncionActivo = false;
                }
                if (!modoCentralActivo) {
                    const opcionActual = buscarOpcion(campoManual.value);
                    ciudadCentral.value = opcionActual ? opcionActual.value : '';
                }
                manualWrapper.hidden = true;
                centralWrapper.hidden = false;
                campoManual.disabled = true;
                campoManual.required = false;
                ciudadCentral.disabled = false;
                ciudadCentral.name = nombreCampo;
                ciudadCentral.required = requerido;
                if (etiqueta) etiqueta.htmlFor = ciudadCentral.id;
            } else {
                if (modoCentralActivo && ciudadCentral.value) {
                    campoManual.value = ciudadCentral.value;
                }
                if (esAsuncion) {
                    if (!modoAsuncionActivo) ciudadManualAnterior = campoManual.value;
                    campoManual.value = 'Asunción';
                    campoManual.readOnly = true;
                    modoAsuncionActivo = true;
                } else if (modoAsuncionActivo) {
                    campoManual.value = ciudadManualAnterior;
                    campoManual.readOnly = false;
                    modoAsuncionActivo = false;
                }
                manualWrapper.hidden = false;
                centralWrapper.hidden = true;
                ciudadCentral.disabled = true;
                ciudadCentral.required = false;
                campoManual.disabled = false;
                campoManual.required = requerido;
                if (etiqueta) etiqueta.htmlFor = campoManual.id;
            }

            modoCentralActivo = esCentral;
        }

        departamento.addEventListener('change', actualizarCiudad);
        actualizarCiudad();
    });
});
