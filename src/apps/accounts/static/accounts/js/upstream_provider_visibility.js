/**
 * Upstream Provider Visibility Widget
 *
 * Syncs the Select2 multi-select (for choosing upstream providers) with
 * a list of visibility checkboxes, so each provider can be individually
 * marked as "show in public directory" or "hidden".
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
        var visibilityFieldset = document.getElementById(fieldId + "_visibility");
        var announcer = document.getElementById(fieldId + "_announcer");

        if (!visibilityFieldset) return;

        var rowsContainer = visibilityFieldset.querySelector(
            ".upstream-visibility-rows"
        );
        if (!rowsContainer) {
            rowsContainer = document.createElement("div");
            rowsContainer.className = "upstream-visibility-rows";
            visibilityFieldset.appendChild(rowsContainer);
        }

        var fieldName = selectElement.getAttribute("name") || fieldId;

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
            // Fall back to reading the option text from the select element
            var option = selectElement.querySelector(
                'option[value="' + id + '"]'
            );
            return option ? option.textContent : "Provider #" + id;
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

            label.appendChild(nameSpan);
            label.appendChild(
                document.createTextNode(" — show in public directory")
            );

            row.appendChild(checkbox);
            row.appendChild(label);

            return row;
        }

        function addRow(providerId) {
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
                    selectElement.focus();
                }
            }
        }

        function showFieldset() {
            visibilityFieldset.removeAttribute("hidden");
        }

        function hideFieldset() {
            visibilityFieldset.setAttribute("hidden", "");
        }

        function announce(message) {
            if (!announcer) return;
            announcer.textContent = message;
        }

        // --- Select2 event integration ---
        //
        // Select2 fires `select2:select` / `select2:unselect` as jQuery
        // events, so we listen via jQuery. The selected/unselected item's ID
        // is in `e.params.data.id`.

        var $select = (window.jQuery || window.jq)(selectElement);
        $select.on("select2:select", function (e) {
            var id = (e.params && e.params.data && e.params.data.id) || null;
            if (id !== null) {
                addRow(id);
            }
        });
        $select.on("select2:unselect", function (e) {
            var id = (e.params && e.params.data && e.params.data.id) || null;
            if (id !== null) {
                removeRow(id);
            }
        });

        // Show/hide based on initial state
        if (rowsContainer.children.length > 0) {
            showFieldset();
        } else {
            hideFieldset();
        }
    }

    // Find all upstream provider Select2 widgets on the page
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
