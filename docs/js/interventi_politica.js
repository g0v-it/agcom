var dom = document.getElementById('interventi_solo_politica');
var myChartSoloPolitica = echarts.init(dom, null, {
    renderer: 'canvas',
    useDirtyRect: false
});
var optionSoloPolitica;

myChartSoloPolitica.showLoading();
$.get('agcom/data/interventi_solo_politica.json', function(soloPoliticaData) {
    myChartSoloPolitica.hideLoading();
    optionSoloPolitica = {
        title: {
            text: soloPoliticaData.titolo
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        legend: {},
        grid: {
            left: '10%',
            right: '10%',
            //bottom: '3%',
            //containLabel: true
        },
        xAxis: {
            type: 'value',
            //boundaryGap: [0, 0.01]
        },
        yAxis: {
            type: 'category',
            data: soloPoliticaData.categorie
        },
        series: [{
            name: soloPoliticaData,
            type: 'bar',
            data: soloPoliticaData.valori
        }]
    };


    if (optionSoloPolitica && typeof optionSoloPolitica === 'object') {
        myChartSoloPolitica.setOption(optionSoloPolitica);
    }
});
window.addEventListener('resize', myChartSoloPolitica.resize);
