/**
 * Reusable TomSelect initialisers.
 *
 * These helpers turn plain <select multiple> elements into TomSelect
 * autocomplete multi-selects, using the TomSelect instance already bundled
 * in /static/js/dist/app.bundle.js.
 *
 * They are intentionally dependency-free apart from the global TomSelect
 * object exposed by the bundle.
 */
(function () {
    "use strict";

    /**
     * Build a TomSelect "load" callback that fetches from a JSON autocomplete
     * endpoint and maps Select2-shaped responses to TomSelect options.
     *
     * The existing Django Autocomplete Light endpoints return:
     *   {"results": [{"id": 1, "text": "..."}, ...], "pagination": {...}}
     *
     * TomSelect options expect:
     *   {"value": "1", "text": "..."}
     */
    function buildSelect2LoadCallback(autocompleteUrl) {
        return function (query, callback) {
            var url = autocompleteUrl;
            if (!url) {
                return callback();
            }

            var separator = url.indexOf("?") === -1 ? "?" : "&";
            var requestUrl = url + separator + "q=" + encodeURIComponent(query);

            var xhr = new XMLHttpRequest();
            xhr.open("GET", requestUrl, true);
            xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
            xhr.onload = function () {
                if (xhr.status !== 200) {
                    return callback();
                }
                try {
                    var json = JSON.parse(xhr.responseText);
                    var results = json.results || [];
                    var options = results.map(function (item) {
                        return {
                            value: String(item.id),
                            text: item.text,
                        };
                    });
                    callback(options);
                } catch (e) {
                    callback();
                }
            };
            xhr.onerror = function () {
                callback();
            };
            xhr.send();
        };
    }

    /**
     * Initialise a TomSelect autocomplete multi-select on the given element.
     *
     * The element may define:
     *   - data-placeholder: placeholder text when no items are selected
     *   - data-autocomplete-url: URL for remote search (defaults to the
     *     linked-provider endpoint)
     *
     * Options passed in the second argument are merged into the default config.
     */
    window.initTomSelectAutocomplete = function initTomSelectAutocomplete(
        selectElement,
        options
    ) {
        if (typeof TomSelect === "undefined") {
            return null;
        }
        if (selectElement.tomselect) {
            return selectElement.tomselect;
        }

        var autocompleteUrl =
            selectElement.getAttribute("data-autocomplete-url");
        if (!autocompleteUrl) {
            throw new Error(
                "initTomSelectAutocomplete requires a data-autocomplete-url attribute on the select element."
            );
        }

        var config = Object.assign(
            {
                plugins: ["remove_button", "clear_button"],
                maxItems: null,
                valueField: "value",
                labelField: "text",
                searchField: ["text"],
                placeholder:
                    selectElement.getAttribute("data-placeholder") || "",
                load: buildSelect2LoadCallback(autocompleteUrl),
                loadThrottle: 300,
                preload: false,
            },
            options || {}
        );

        return new TomSelect(selectElement, config);
    };
})();
