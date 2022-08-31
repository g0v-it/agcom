var dom = document.getElementById('presenza_movimenti');
var myChartPresenzaMovimenti = echarts.init(dom, 'walden', {
    renderer: 'canvas',
    useDirtyRect: false
});
var optionPresenzaMovimenti;
myChartPresenzaMovimenti.showLoading();
$.get('agcom/data/presenza_movimenti.json', function(presenzaMovimentiData) {
    myChartPresenzaMovimenti.hideLoading();
    optionPresenzaMovimenti = {
        title: {
            text: 'Volume di presenza dei soggetti politici',
            textStyle: {
                fontSize: 14,
                align: 'center'
            }
        },
        series: {
            name: "Volume di presenza",
            type: 'treemap',
            data: presenzaMovimentiData.dati
        }
    };

    if (optionPresenzaMovimenti && typeof optionPresenzaMovimenti === 'object') {
        myChartPresenzaMovimenti.setOption(optionPresenzaMovimenti);
    }
});
window.addEventListener('resize', myChartPresenzaMovimenti.resize);
