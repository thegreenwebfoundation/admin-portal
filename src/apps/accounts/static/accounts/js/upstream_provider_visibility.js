/**
 * Upstream Provider Visibility Widget
 *
 * Syncs the TomSelect multi-select (for choosing upstream providers) with
 * a list of visibility checkboxes, so each provider can be individually
 * marked as "show in public directory" or "hidden".
 *
 * When the private_upstream_linking flag is off, the visibility fieldset is
 * not rendered; this script still initialises TomSelect on the plain
 * <select multiple> so the search-as-you-type behaviour is consistent.
 *
 * Accessibility:
 * - All checkboxes are standard <input type="checkbox"> — natively focusable
 *   and toggleable via keyboard (Space).
 * - An aria-live="polite" region announces when providers are added/removed.
 * - Rows are added/removed via DOM API (createElement/appendChild), not
 *   innerHTML, so the browser properly registers them in the accessibility tree.
 * - When the upstream section is collapsed (no reseller basis selected),
 *   the container is hidden via the `hidden` attribute, which removes it
 *   from the tab order and accessibility tree.
 */
(function () {
    "use strict";

    function initUpstreamVisibility(selectId) {
        var selectElement = document.getElementById(selectId);
        if (!selectElement) return;

        var fieldId = selectId;
        var fieldName = selectElement.getAttribute("name") || fieldId;
        var visibilityFieldset = document.getElementById(fieldId + "_visibility");
        var announcer = document.getElementById(fieldId + "_announcer");
        var rowsContainer = null;
        var tom = null;

        if (visibilityFieldset) {
            rowsContainer = visibilityFieldset.querySelector(
                ".upstream-visibility-rows"
            );
            if (!rowsContainer) {
                rowsContainer = document.createElement("div");
                rowsContainer.className = "upstream-visibility-rows";
                visibilityFieldset.appendChild(rowsContainer);
            }
        }

        // Load initial data (provider PKs + names) from the JSON script tag
        var dataSource = document.getElementById(fieldId + "_data");
        var initialData = {};
        if (dataSource) {
            try {
                var parsed = JSON.parse(dataSource.textContent);
                for (var i = 0; i < parsed.length; i++) {
                    initialData[String(parsed[i].provider)] = parsed[i];
                }
            } catch (e) {
                // ignore malformed data
            }
        }

        function getProviderName(id) {
            var item = initialData[id];
            if (item && item.provider_name) {
                return item.provider_name;
            }
            // Try the live TomSelect options (useful for newly-added items)
            if (tom && tom.options[id] && tom.options[id].text) {
                return tom.options[id].text;
            }
            // Fall back to reading the option text from the original select element
            var option = selectElement.querySelector(
                'option[value="' + id + '"]'
            );
            return option ? option.textContent : "Provider #" + id;
        }

        function attachCheckboxHandler(checkbox, row, publicSpan, hiddenSpan, providerId) {
            checkbox.addEventListener("change", function () {
                if (this.checked) {
                    if (publicSpan) publicSpan.removeAttribute("hidden");
                    if (hiddenSpan) hiddenSpan.setAttribute("hidden", "");
                    row.classList.remove("is-hidden-upstream");
                } else {
                    if (publicSpan) publicSpan.setAttribute("hidden", "");
                    if (hiddenSpan) hiddenSpan.removeAttribute("hidden");
                    row.classList.add("is-hidden-upstream");
                }
                announce(
                    getProviderName(providerId) +
                        (this.checked
                            ? " will be shown in the public directory."
                            : " will not be shown in the public directory.")
                );
            });
        }

        function createVisibilityRow(providerId, isPublic) {
            var row = document.createElement("div");
            row.className =
                "upstream-visibility-row flex items-center gap-2 mb-1";
            row.setAttribute("data-provider-id", providerId);

            var checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.name = fieldName + "_visibility_" + providerId;
            checkbox.id = fieldId + "_visibility_" + providerId;
            checkbox.className = "form-checkbox";
            checkbox.checked = isPublic;

            var label = document.createElement("label");
            label.htmlFor = checkbox.id;
            label.className = "text-sm";

            var nameSpan = document.createElement("span");
            nameSpan.className = "upstream-provider-name";
            nameSpan.textContent = getProviderName(providerId);

            var publicSpan = document.createElement("span");
            publicSpan.className = "visibility-label visibility-public";
            publicSpan.textContent = " — show in public directory";
            if (!isPublic) { publicSpan.setAttribute("hidden", ""); }

            var hiddenSpan = document.createElement("span");
            hiddenSpan.className = "visibility-label visibility-hidden";
            hiddenSpan.textContent = " — will not be shown in public directory";
            if (isPublic) { hiddenSpan.setAttribute("hidden", ""); }

            label.appendChild(nameSpan);
            label.appendChild(publicSpan);
            label.appendChild(hiddenSpan);

            row.appendChild(checkbox);
            row.appendChild(label);

            attachCheckboxHandler(checkbox, row, publicSpan, hiddenSpan, providerId);

            // Set initial row class
            if (!isPublic) {
                row.classList.add("is-hidden-upstream");
            }

            return row;
        }

        function addRow(providerId) {
            if (!rowsContainer) return;

            providerId = String(providerId);
            var existing = rowsContainer.querySelector(
                '[data-provider-id="' + providerId + '"]'
            );
            if (existing) return;

            var isPublic = true;
            if (initialData[providerId]) {
                isPublic = initialData[providerId].is_public !== false;
            }

            var row = createVisibilityRow(providerId, isPublic);
            rowsContainer.appendChild(row);

            showFieldset();

            announce(
                getProviderName(providerId) +
                    " added. Use the checkbox to control visibility."
            );
        }

        function removeRow(providerId) {
            if (!rowsContainer) return;

            providerId = String(providerId);
            var row = rowsContainer.querySelector(
                '[data-provider-id="' + providerId + '"]'
            );
            if (!row) return;

            var providerName = getProviderName(providerId);
            var checkbox = row.querySelector("input[type=checkbox]");
            var focusNext = false;
            if (document.activeElement === checkbox) {
                focusNext = true;
            }

            row.remove();
            announce(providerName + " removed.");

            if (rowsContainer.children.length === 0) {
                hideFieldset();
            }

            if (focusNext) {
                var nextCheckbox = rowsContainer.querySelector(
                    "input[type=checkbox]"
                );
                if (nextCheckbox) {
                    nextCheckbox.focus();
                } else {
                    // Focus the TomSelect input if available, otherwise the
                    // (now hidden) original select.
                    var focusTarget = (tom && tom.control_input) || selectElement;
                    focusTarget.focus();
                }
            }
        }

        function showFieldset() {
            if (visibilityFieldset) {
                visibilityFieldset.removeAttribute("hidden");
            }
        }

        function hideFieldset() {
            if (visibilityFieldset) {
                visibilityFieldset.setAttribute("hidden", "");
            }
        }

        function announce(message) {
            if (!announcer) return;
            announcer.textContent = message;
        }

        // --- TomSelect event integration ---
        //
        // The reusable initialiser (in tomselect-widgets.js) creates the
        // TomSelect instance and exposes it on selectElement.tomselect. We
        // pass callbacks for the lifecycle events we care about and let it
        // handle remote autocomplete loading.

        if (typeof window.initTomSelectAutocomplete !== "function") {
            return;
        }

        tom = window.initTomSelectAutocomplete(selectElement, {
            onItemAdd: function (value) {
                addRow(value);
            },
            onItemRemove: function (value) {
                removeRow(value);
            },
            onClear: function () {
                if (!rowsContainer) return;
                var rows = rowsContainer.querySelectorAll(
                    ".upstream-visibility-row"
                );
                for (var i = 0; i < rows.length; i++) {
                    rows[i].remove();
                }
                hideFieldset();
                announce("All providers removed.");
            },
        });

        if (!tom) {
            // TomSelect or the initialiser is unavailable; leave the plain
            // <select multiple> untouched.
            return;
        }

        if (!visibilityFieldset) {
            // Nothing more to do when the visibility fieldset is not rendered.
            return;
        }

        // --- Server-rendered row sync ---
        // Attach change listeners to rows that were rendered server-side
        // (dynamically created rows get their listener in createVisibilityRow).
        var existingRows = rowsContainer.querySelectorAll(
            ".upstream-visibility-row"
        );
        for (var i = 0; i < existingRows.length; i++) {
            (function (row) {
                var cb = row.querySelector("input[type=checkbox]");
                if (!cb) return;
                var publicLabel = row.querySelector(".visibility-public");
                var hiddenLabel = row.querySelector(".visibility-hidden");
                var providerId = row.getAttribute("data-provider-id");

                // Set initial class for CSS opacity
                if (!cb.checked) {
                    row.classList.add("is-hidden-upstream");
                }

                attachCheckboxHandler(cb, row, publicLabel, hiddenLabel, providerId);
            })(existingRows[i]);
        }

        // Show/hide based on initial state
        if (rowsContainer.children.length > 0) {
            showFieldset();
        } else {
            hideFieldset();
        }
    }

    // Find all upstream provider TomSelect widgets on the page
    function initAll() {
        var widgets = document.querySelectorAll(
            "[data-upstream-visibility-widget]"
        );
        for (var i = 0; i < widgets.length; i++) {
            initUpstreamVisibility(widgets[i].id);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAll);
    } else {
        initAll();
    }
})();
