import Chart from 'chart.js/auto';


const statsCharts = {
  render(domId, data) {

    const ctx = domId;

    console.log({ data })

    const myChart = new Chart(ctx, {
      type: 'bar',
      labels: data.green.map(function (elem) { return elem.y }),
      data: {
        labels: data.green.map(function (elem) { return elem.x }),
        datasets: [{
          label: "Green",
          data: data.green.map(function (elem) { return elem.y }),
          // backgroundColor: "#1E320C"
          backgroundColor: "#8AC850"
        }, {
          label: "Grey",
          data: data.grey.map(function (elem) { return elem.y }),
          backgroundColor: "#777"
        }],
      },

      options: {
        scales: {
          y: {
            beginAtZero: true,
            stacked: true
          },
          x: {
            stacked: true
          }
        }
      }
    })
  }
}


export default statsCharts

