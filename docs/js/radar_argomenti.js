var dom = document.getElementById('radar');
var myChartRadar = echarts.init(dom, 'walden', {
    renderer: 'canvas',
    useDirtyRect: false
});
var optionRadar;
myChartRadar.showLoading();
$.get('data/radar_argomenti.json', function(radarData) {
    myChartRadar.hideLoading();
    optionRadar = {
        title: {
            text: radarData.titolo
        },
        legend: {
            data: radarData.legenda
        },
        radar: {
            indicator: radarData.indicatori,
        },
        series: [{
            name: radarData.titolo_radar,
            type: 'radar',
            data: radarData.dati
        }]
    };


    if (optionRadar && typeof optionRadar === 'object') {
        myChartRadar.setOption(optionRadar);
    }
});

window.addEventListener('resize', myChartRadar.resize);
