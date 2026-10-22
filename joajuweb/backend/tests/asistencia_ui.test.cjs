// Sin paquetes adicionales. Ejecutar: node --test joajuweb/backend/tests/asistencia_ui.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');

function pantalla() {
    const search = { value: '', addEventListener: (_, fn) => { search.input = fn; } };
    const button = { addEventListener: (_, fn) => { button.click = fn; } };
    const empty = { hidden: true };
    const status = { textContent: '' };
    const rows = ['Ana Pérez ana ana@example.com', 'Luis Gómez luis luis@example.com'].map(busqueda => {
        const radios = ['presente', 'ausente'].map(value => ({ value, checked: false }));
        return { dataset: { busqueda }, hidden: false, radios,
            querySelector: selector => radios.find(item => selector.includes(`"${item.value}"`)),
        };
    });
    const elements = { '#buscar-voluntario': search, '#marcar-presentes': button, '#sin-coincidencias': empty, '#resultados-asistencia': status };
    const form = {
        querySelector: selector => elements[selector], querySelectorAll: () => rows,
        addEventListener: (_, fn) => { form.invalid = fn; },
    };
    runInNewContext(readFileSync(resolve(__dirname, '../../static/js/asistencia.js'), 'utf8'), { document: { querySelector: () => form } });
    return { rows, search, button, empty, status, form };
}

test('filtra por nombre, apellido con tildes, usuario y correo', () => {
    const ui = pantalla();
    for (const texto of ['ana', 'PEREZ', 'pérez Ana', 'ana@example.com']) {
        ui.search.value = texto;
        ui.search.input();
        assert.equal(ui.rows[0].hidden, false);
        assert.equal(ui.rows[1].hidden, true);
    }
    assert.equal(ui.status.textContent, '1 de 2 voluntarios');
});

test('marcar todos incluye filas ocultas y permite corregir ausentes', () => {
    const ui = pantalla();
    ui.search.value = 'ana';
    ui.search.input();
    ui.button.click();
    assert.ok(ui.rows.every(row => row.radios[0].checked));
    ui.rows[0].radios[0].checked = false;
    ui.rows[0].radios[1].checked = true;
    ui.search.value = 'luis';
    ui.search.input();
    ui.search.value = '';
    ui.search.input();
    assert.ok(ui.rows[0].radios[1].checked);
    assert.ok(ui.rows[1].radios[0].checked);
    assert.ok(ui.rows.every(row => !row.hidden));
});

test('sin coincidencias muestra un mensaje y conserva estados', () => {
    const ui = pantalla();
    ui.button.click();
    ui.search.value = 'inexistente';
    ui.search.input();
    assert.equal(ui.empty.hidden, false);
    assert.equal(ui.status.textContent, '0 de 2 voluntarios');
    assert.ok(ui.rows.every(row => row.radios[0].checked));
});

test('revela campos pendientes ocultos al validar', () => {
    const ui = pantalla();
    ui.search.value = 'ana';
    ui.search.input();
    ui.form.invalid({ target: { closest: () => ui.rows[1] } });
    assert.equal(ui.search.value, '');
    assert.ok(ui.rows.every(row => !row.hidden));
});
