import TomSelect from "tom-select";

// Auto-apply the checkbox_options and remove_button plugins globally so any
// element enhanced with Tom Select gets the same behaviour without needing
// per-page plugin registration.
TomSelect.define("checkbox_options", function (options) {
    var self = this;
    var orig = self.setupTemplates;
    self.setupTemplates = function () {
        orig.call(self);
        var checkbox_options = self.settings.render.option;
        self.settings.render.option = function (data, escape_html) {
            var rendered = checkbox_options.call(self, data, escape_html);
            var checked = data.selected ? " checked" : "";
            return (
                '<div><span class="input-checkbox"><input type="checkbox"' +
                checked +
                '></span>' +
                rendered +
                "</div>"
            );
        };
    };
});

window.TomSelect = TomSelect;

console.log("Compiled app.js");
