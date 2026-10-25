document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-report-picker]').forEach(function (picker) {
        const input = picker.querySelector('[data-report-search]');
        const options = Array.from(picker.querySelectorAll('[data-report-option]'));
        const emptyMessage = picker.querySelector('[data-report-empty]');

        if (!input || !options.length) return;

        const dashboard = picker.parentElement.querySelector('[data-activity-dashboard]');
        const activityPicker = Boolean(dashboard);
        const pickerLabel = picker.querySelector('[data-report-picker-label]');

        if (activityPicker) {
            const fields = {
                name: dashboard.querySelector('[data-activity-name]'),
                meta: dashboard.querySelector('[data-activity-meta]'),
                state: dashboard.querySelector('[data-activity-state]'),
                registered: dashboard.querySelector('[data-activity-registered]'),
                spots: dashboard.querySelector('[data-activity-spots]'),
                present: dashboard.querySelector('[data-activity-present]'),
                absent: dashboard.querySelector('[data-activity-absent]'),
                occupancyChart: dashboard.querySelector('[data-activity-occupancy-chart]'),
                occupancyPercent: dashboard.querySelector('[data-activity-occupancy-percent]'),
                capacityLabel: dashboard.querySelector('[data-activity-capacity-label]'),
                attendanceChart: dashboard.querySelector('[data-activity-attendance-chart]'),
                attendancePercent: dashboard.querySelector('[data-activity-attendance-percent]'),
                attendanceLabel: dashboard.querySelector('[data-activity-attendance-label]'),
                attendanceTotal: dashboard.querySelector('[data-activity-attendance-total]'),
                attendanceNote: dashboard.querySelector('[data-activity-attendance-note]'),
            };

            function clearSelection() {
                dashboard.hidden = true;
                if (pickerLabel) pickerLabel.textContent = 'Elegir actividad';
                options.forEach(function (option) { option.setAttribute('aria-pressed', 'false'); });
            }

            options.forEach(function (option) {
                option.addEventListener('click', function () {
                    const data = option.dataset;
                    const cupo = Number(data.actividadCupo) || 0;
                    const inscriptos = Number(data.actividadInscriptos) || 0;
                    const presentes = Number(data.actividadPresentes) || 0;
                    const ausentes = Number(data.actividadAusentes) || 0;
                    const disponibles = Math.max(0, cupo - inscriptos);
                    const porcentaje = cupo ? Math.min(100, Math.round((inscriptos / cupo) * 100)) : 0;
                    const totalMarcas = presentes + ausentes;
                    const porcentajeAsistencia = totalMarcas ? Math.round((presentes / totalMarcas) * 100) : 0;

                    fields.name.textContent = data.actividadNombre;
                    fields.meta.textContent = [data.actividadTipo, data.actividadFecha, data.actividadUbicacion].filter(Boolean).join(' · ');
                    fields.state.textContent = data.actividadEstado;
                    fields.registered.textContent = inscriptos;
                    fields.spots.textContent = disponibles;
                    fields.present.textContent = presentes;
                    fields.absent.textContent = ausentes;
                    fields.occupancyPercent.textContent = porcentaje + '%';
                    fields.occupancyChart.style.setProperty('--chart-fill', porcentaje + '%');
                    fields.occupancyChart.setAttribute('aria-label', 'Ocupación: ' + inscriptos + ' de ' + cupo + ' cupos, ' + porcentaje + '%');
                    fields.capacityLabel.textContent = inscriptos + ' de ' + cupo + ' cupos ocupados';
                    fields.attendanceChart.style.setProperty('--chart-fill', porcentajeAsistencia + '%');
                    fields.attendanceChart.setAttribute('aria-label', totalMarcas
                        ? 'Asistencia: ' + presentes + ' presentes y ' + ausentes + ' ausentes por jornada'
                        : 'Sin registros de asistencia');
                    fields.attendancePercent.textContent = totalMarcas ? porcentajeAsistencia + '%' : '—';
                    fields.attendanceLabel.textContent = totalMarcas ? 'presentes' : 'sin datos';
                    fields.attendanceTotal.textContent = totalMarcas ? totalMarcas + ' registros por jornada' : 'Sin registros todavía';
                    fields.attendanceNote.textContent = totalMarcas
                        ? 'Asistencia registrada en ' + totalMarcas + ' marca(s) de jornada.'
                        : 'Todavía no hay registros de asistencia para esta actividad.';
                    dashboard.hidden = false;
                    if (pickerLabel) pickerLabel.textContent = data.actividadNombre;
                    options.forEach(function (item) {
                        item.setAttribute('aria-pressed', item === option ? 'true' : 'false');
                    });
                });
            });

            const clearButton = dashboard.querySelector('[data-activity-clear]');
            if (clearButton) clearButton.addEventListener('click', clearSelection);
        }

        input.addEventListener('input', function () {
            const query = input.value.trim().toLocaleLowerCase();
            let visible = 0;

            options.forEach(function (option) {
                const matches = (option.dataset.searchText || option.textContent)
                    .toLocaleLowerCase()
                    .includes(query);
                option.hidden = !matches;
                if (matches) visible += 1;
            });

            if (emptyMessage) emptyMessage.hidden = visible !== 0;
        });
    });
});
