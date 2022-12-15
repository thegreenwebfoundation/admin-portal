/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

module.exports = {

    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */
        /*  Templates within theme app (e.g. base.html) */
        '../templates/**/*.html',

        /* Templates in other apps. */
        '../../templates/**/*.html',

        /* project root template dir */
        '../../../templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        // '!../../**/node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        // '../../**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        // '../../**/*.py'
    ],
    theme: {
        extend: {
            colors: {
                "tgwf-green": {
                    900: "#EAF5E0",
                    800: "#D1E9B9",
                    700: "#C3E3A6",
                    600: "#8AC850",
                    500: "#8AC850",
                    400: "#5A8C2C",
                    300: "#476F22",
                    200: "#37561A",
                    100: "#1E320C"
                }
            }
        },
    },
    plugins: [
        /**
         * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
         * for forms. If you don't like it or have own styling for forms,
         * comment the line below to disable '@tailwindcss/forms'.
         */
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/line-clamp'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
