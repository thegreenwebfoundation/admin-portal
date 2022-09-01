# Other Green Web software

While the main admin-portal repository holds the code for serving the main API and administration platform, The Green Web Foundation actively maintains a some other open source software.

Unless otherwise mentioned all the software listed below is open source, and usually released under the [permissive Apache 2.0 license](https://choosealicense.com/licenses/apache-2.0/).

## CO2.js

CO2.js is a javascript library for understanding and managing the carbon emissions from software. It provides APIs for converting observable activity for digital services, like website page loads or data transfer, and returns carbon emissions figures, based on publicly accessible peer reviewed models from academic literature, and open data where the provenance of the number can be traced.

It also provides a convenient API for performing lookups against the Green Web Foundation Greencheck API, as well performing lookups against a local snapshot to avoid needless remote API calls.

For more, please visit [the CO2.js repo on github][co2js-repo], or view the [Calculating Digital Emissions page on Sustainable Web Design website][swd-site].

[co2js-repo]: https://github.com/thegreenwebfoundation/co2.js/
[swd-site]:https://sustainablewebdesign.org/calculating-digital-emissions/

## Grid intensity libraries - golang and javascript

The Green Web grid intensity libraries help developers and designers build digital services, that are _carbon aware_- they respond to  conditions on the underlying electricity grids the internet relies on, to optimise for delivering digital services at a lower carbon intensity.

Because the mix of fuels powering the grid will be different depending when and where you run your code, you can influence the carbon intensity of the code you write by moving it through time and space - either by making it run when the grid is greener, or making it run where it's greener, like a CDN running on green power.

These libraries offer a consistent API to for consuming freely available open data, or remote API services to provide the signals needed to make a responsive system.


- For javascript please see [our grid intensity github repository][grid-intensity-js]
- For golang, please see our [grid-intensity-go][], and [grid-intensity-exporter][] libraries.

[grid-intensity-js]: https://github.com/thegreenwebfoundation/grid-intensity
[grid-intensity-go]: https://github.com/thegreenwebfoundation/grid-intensity-go
[grid-intensity-exporter]: https://github.com/thegreenwebfoundation/grid-intensity-exporter

## Web Extension

The Green Web browser extensions allow you to check the green status of sites as you visit, as well as checking the status of a site _before_ you visit it. The extension is available for Firefox, and Chrome, and Safari on the desktop.

For more, visit [the github repository for the web-extension](https://github.com/thegreenwebfoundation/web-extension/)
