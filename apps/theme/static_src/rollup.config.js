import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import { terser } from 'rollup-plugin-terser';


const browserBuild = {
  input: 'src/app.js',
  output: {
    file: '../static/js/dist/app.bundle.js',
    format: 'iife',
    name: "app"
  },
  plugins: [
    resolve(),
  ]
}

const browserBuildMin = {
  input: 'src/app.js',
  output: {
    file: '../static/js/dist/app.bundle.min.js'
  },
  plugins: [
    resolve(),
    terser()
  ]
}


export default [
  browserBuild,
  browserBuildMin,
];
