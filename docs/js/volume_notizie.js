var dom = document.getElementById('volume');
var myChartVolume = echarts.init(dom, 'walden', {
    renderer: 'canvas',
    useDirtyRect: false
});
var optionVolume;
myChartVolume.showLoading();
$.get('data/volume_notizie.json', function(volumeData) {
    myChartVolume.hideLoading();
    optionVolume = {
        title: {
            text: volumeData.titolo,
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'line',
                lineStyle: {
                    color: 'rgba(0,0,0,0.2)',
                    width: 1,
                    type: 'solid'
                }
            }
        },
        toolbox: {
            feature: {
                dataZoom: {
                    yAxisIndex: 'none'
                },
                restore: {},
                saveAsImage: {}
            }
        },
        dataZoom: [{
            type: 'slider'
        }, {
            type: 'inside'
        }],
        legend: {
            data: volumeData.legenda
        },
        singleAxis: {
            top: 50,
            bottom: 50,
            axisTick: {},
            axisLabel: {},
            type: 'time',
            axisPointer: {
                animation: true,
                label: {
                    show: true
                }
            },
            splitLine: {
                show: true,
                lineStyle: {
                    type: 'dashed',
                    opacity: 0.2
                }
            }
        },
        series: [{
            type: 'themeRiver',
            emphasis: {
                disabled: true
            },
            data: volumeData.dati
        }]
    };
    if (optionVolume && typeof optionVolume === 'object') {
        myChartVolume.setOption(optionVolume);
    }
});

window.addEventListener('resize', myChartVolume.resize);
