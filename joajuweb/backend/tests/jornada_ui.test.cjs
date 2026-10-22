// Ejecutar: node --test joajuweb/backend/tests/jornada_ui.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { runInNewContext } = require('node:vm');

function pantalla({ confirm = true, readonly = false } = {}) {
    const events = {};
    const radios = readonly ? [] : [{ checked: true }, { checked: false }, { checked: false }, { checked: true }];
    const select = { value: '1', dataset: { jornadaActual: '1' }, addEventListener: (name, handler) => { events[name] = handler; } };
    const form = {
        submitted: false,
        addEventListener: (name, handler) => { events[name] = handler; },
        requestSubmit: () => {
            let prevented = false;
            events.submit({ preventDefault: () => { prevented = true; } });
            form.submitted = !prevented;
        },
    };
    let confirmations = 0;
    const elements = { '#selector-jornada-form': form, '#jornada': select, '#asistencia-form': { querySelectorAll: () => radios } };
    runInNewContext(readFileSync(resolve(__dirname, '../../static/js/jornada.js'), 'utf8'), {
        document: { querySelector: selector => elements[selector] },
        window: { confirm: () => { confirmations += 1; return confirm; } },
    });
    return { select, form, radios, change: () => events.change(), confirmations: () => confirmations };
}

test('elegir otra jornada consulta inmediatamente sin esperar al cierre', () => {
    const ui = pantalla({ readonly: true });
    ui.select.value = '2';
    ui.change();
    assert.equal(ui.form.submitted, true);
    assert.equal(ui.confirmations(), 0);
});

test('cancelar conserva las marcas y restaura la jornada realmente mostrada', () => {
    const ui = pantalla({ confirm: false });
    ui.radios[0].checked = false;
    ui.radios[1].checked = true;
    ui.select.value = '2';
    ui.change();
    assert.equal(ui.form.submitted, false);
    assert.equal(ui.select.value, '1');
    assert.equal(ui.radios[1].checked, true);
    assert.equal(ui.confirmations(), 1);
});

test('también detecta marcas masivas hechas sin disparar eventos de input', () => {
    const ui = pantalla({ confirm: false });
    ui.radios[2].checked = true;
    ui.radios[3].checked = false;
    ui.select.value = '2';
    ui.change();
    assert.equal(ui.form.submitted, false);
    assert.equal(ui.confirmations(), 1);
});

test('confirmar permite consultar la nueva jornada sin guardar la asistencia', () => {
    const ui = pantalla();
    ui.radios[0].checked = false;
    ui.radios[1].checked = true;
    ui.select.value = '2';
    ui.change();
    assert.equal(ui.form.submitted, true);
    assert.equal(ui.select.value, '2');
    assert.equal(ui.confirmations(), 1);
});

test('volver a los estados originales no pide confirmación innecesaria', () => {
    const ui = pantalla();
    ui.radios[0].checked = false;
    ui.radios[0].checked = true;
    ui.select.value = '2';
    ui.change();
    assert.equal(ui.form.submitted, true);
    assert.equal(ui.confirmations(), 0);
});

test('Ver jornada mantiene la misma protección de cambios sin guardar', () => {
    const ui = pantalla({ confirm: false });
    ui.radios[1].checked = true;
    ui.form.requestSubmit();
    assert.equal(ui.form.submitted, false);
    assert.equal(ui.confirmations(), 1);
});
