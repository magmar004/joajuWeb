document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-report-picker]').forEach(function (picker) {
        const input = picker.querySelector('[data-report-search]');
        const options = Array.from(picker.querySelectorAll('[data-report-option]'));
        const emptyMessage = picker.querySelector('[data-report-empty]');

        if (!input || !options.length) return;

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
