// 页面加载完成后自动加载统计数据
document.addEventListener('DOMContentLoaded', function() {
    loadStatistics();
    setupFullscreenButtons();
});

// 图表引用
let entityChart = null;
let relationChart = null;

// 颜色方案 - 使用农业主题色系
const colors = [
    '#4a7c59', '#7da87b', '#96613d', '#f5e1a4', '#e3f1e4',
    '#608c74', '#a87e5a', '#f0d980', '#c6d8c7', '#3a5f47',
    '#e57373', '#64b5f6', '#ffd54f', '#81c784', '#ba68c8',
    '#ffb74d', '#4dd0e1', '#dce775', '#9575cd', '#a1887f',
    '#90a4ae', '#ff8a65', '#aed581', '#7986cb', '#d4e157',
    '#ffb300', '#43a047', '#00897b', '#c62828', '#ad1457'
];

// 加载统计数据
function loadStatistics() {
    // 显示加载中状态
    document.getElementById('loading-entity').style.display = 'flex';
    document.getElementById('loading-relation').style.display = 'flex';
    
    // 初始化图表实例
    entityChart = echarts.init(document.getElementById('entity-stats'));
    relationChart = echarts.init(document.getElementById('relation-stats'));
    
    // 获取数据
    fetch('/api/knowledge_graph/statistics')
        .then(response => response.json())
        .then(data => {
            // 更新总数统计
            updateOverviewStats(data);
            
            // 更新实体图表和表格
            updateEntityStats(data.entities || data['实体类型分布']);
            
            // 更新关系图表和表格
            updateRelationStats(data.relations || data['关系类型分布']);
            
            // 隐藏加载中状态
            document.getElementById('loading-entity').style.display = 'none';
            document.getElementById('loading-relation').style.display = 'none';
            
            // 窗口大小改变时重绘图表
            window.addEventListener('resize', function() {
                if (entityChart) entityChart.resize();
                if (relationChart) relationChart.resize();
            });
        })
        .catch(error => {
            console.error('获取统计数据失败:', error);
            document.getElementById('loading-entity').innerHTML = '<div class="text-danger"><i class="bi bi-exclamation-triangle"></i> 加载数据失败</div>';
            document.getElementById('loading-relation').innerHTML = '<div class="text-danger"><i class="bi bi-exclamation-triangle"></i> 加载数据失败</div>';
        });
}

// 更新概览统计数据
function updateOverviewStats(data) {
    document.getElementById('total-nodes').textContent = formatNumber(data.total_nodes || data['总实体数'] || 0);
    document.getElementById('total-relations').textContent = formatNumber(data.total_relations || data['总关系数'] || 0);
    document.getElementById('total-categories').textContent = (data.entities ? data.entities.length : 
                                                             (data['实体类型数'] || (data['实体类型分布'] ? Object.keys(data['实体类型分布']).length : 0)));
    document.getElementById('total-relation-types').textContent = (data.relations ? data.relations.length : 
                                                                 (data['关系类型数'] || (data['关系类型分布'] ? Object.keys(data['关系类型分布']).length : 0)));
}

// 更新实体统计数据
function updateEntityStats(entities) {
    if (!entities || (Array.isArray(entities) && entities.length === 0) || 
        (!Array.isArray(entities) && Object.keys(entities).length === 0)) {
        document.getElementById('entity-stats').innerHTML = '<div class="text-center py-5 text-muted">暂无数据</div>';
        return;
    }
    
    // 转换数据格式
    let entityData = [];
    if (Array.isArray(entities)) {
        entityData = entities;
    } else {
        entityData = Object.entries(entities).map(([name, count]) => ({
            name, 
            count
        }));
    }
    
    // 排序实体（按数量降序）
    entityData.sort((a, b) => b.count - a.count);
    
    // 准备饼图数据
    const pieData = entityData.map((entity, index) => ({
        name: entity.name,
        value: entity.count,
        itemStyle: {
            color: colors[index % colors.length]
        }
    }));
    
    // 计算总数用于比例
    const totalEntities = entityData.reduce((sum, entity) => sum + entity.count, 0);
    
    // 饼图配置
    const option = {
        tooltip: {
            trigger: 'item',
            formatter: '{a} <br/>{b}: {c} ({d}%)'
        },
        legend: {
            type: 'plain',
            orient: 'vertical',
            right: 40,
            top: 'middle',
            align: 'left',
            itemWidth: 18,
            itemHeight: 14,
            textStyle: {
                fontSize: 14
            },
            data: entityData.map(entity => entity.name)
        },
        grid: {
            left: '10%',
            right: '30%',
            top: '10%',
            bottom: '10%'
        },
        series: [
            {
                name: '实体类型',
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['30%', '50%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: '16',
                        fontWeight: 'bold'
                    }
                },
                labelLine: {
                    show: false
                },
                data: pieData
            }
        ]
    };
    
    // 设置图表选项
    entityChart.setOption(option);
    
    // 更新表格
    const tableBody = document.getElementById('entity-table-body');
    tableBody.innerHTML = '';
    
    entityData.forEach(entity => {
        const percent = ((entity.count / totalEntities) * 100).toFixed(1);
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>
                <span class="entity-color" style="background-color: ${colors[entityData.indexOf(entity) % colors.length]}"></span>
                ${entity.name}
            </td>
            <td class="text-end">${formatNumber(entity.count)}</td>
            <td class="text-end"><span class="ratio-badge">${percent}%</span></td>
        `;
        
        tableBody.appendChild(row);
    });
}

// 更新关系统计数据
function updateRelationStats(relations) {
    if (!relations || (Array.isArray(relations) && relations.length === 0) || 
        (!Array.isArray(relations) && Object.keys(relations).length === 0)) {
        document.getElementById('relation-stats').innerHTML = '<div class="text-center py-5 text-muted">暂无数据</div>';
        return;
    }
    
    // 转换数据格式
    let relationData = [];
    if (Array.isArray(relations)) {
        relationData = relations;
    } else {
        relationData = Object.entries(relations).map(([name, count]) => ({
            name, 
            count
        }));
    }
    
    // 排序关系（按数量降序）
    relationData.sort((a, b) => b.count - a.count);
    
    // 准备图表数据
    const chartData = relationData.map((relation, index) => ({
        name: relation.name,
        value: relation.count,
        itemStyle: {
            color: colors[(index + 5) % colors.length]
        }
    }));
    
    // 计算总数用于比例
    const totalRelations = relationData.reduce((sum, relation) => sum + relation.count, 0);
    
    // 根据关系数量选择图表类型
    let option;
    if (relationData.length > 10) {
        // 如果关系类型太多，使用条形图
        option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'value'
            },
            yAxis: {
                type: 'category',
                data: relationData.slice(0, 15).map(item => item.name),
                axisLabel: {
                    interval: 0,
                    rotate: 30
                }
            },
            series: [
                {
                    name: '关系数量',
                    type: 'bar',
                    data: relationData.slice(0, 15).map((item, index) => ({
                        value: item.count,
                        itemStyle: {
                            color: colors[(index + 5) % colors.length]
                        }
                    }))
                }
            ]
        };
    } else {
        // 如果关系类型较少，使用饼图
        option = {
            tooltip: {
                trigger: 'item',
                formatter: '{a} <br/>{b}: {c} ({d}%)'
            },
            legend: {
                type: 'plain',
                orient: 'vertical',
                right: 40,
                top: 'middle',
                align: 'left',
                itemWidth: 18,
                itemHeight: 14,
                textStyle: {
                    fontSize: 14
                },
                data: relationData.map(relation => relation.name)
            },
            grid: {
                left: '10%',
                right: '30%',
                top: '10%',
                bottom: '10%'
            },
            series: [
                {
                    name: '关系类型',
                    type: 'pie',
                    radius: ['40%', '70%'],
                    center: ['40%', '50%'],
                    avoidLabelOverlap: true,
                    itemStyle: {
                        borderRadius: 6,
                        borderColor: '#fff',
                        borderWidth: 2
                    },
                    label: {
                        show: false,
                        position: 'center'
                    },
                    emphasis: {
                        label: {
                            show: true,
                            fontSize: '16',
                            fontWeight: 'bold'
                        }
                    },
                    labelLine: {
                        show: false
                    },
                    data: chartData
                }
            ]
        };
    }
    
    // 设置图表选项
    relationChart.setOption(option);
    
    // 更新表格
    const tableBody = document.getElementById('relation-table-body');
    tableBody.innerHTML = '';
    
    relationData.forEach(relation => {
        const percent = ((relation.count / totalRelations) * 100).toFixed(1);
        const row = document.createElement('tr');
        
        row.innerHTML = `
            <td>
                <span class="entity-color" style="background-color: ${colors[(relationData.indexOf(relation) + 5) % colors.length]}"></span>
                ${relation.name}
            </td>
            <td class="text-end">${formatNumber(relation.count)}</td>
            <td class="text-end"><span class="ratio-badge">${percent}%</span></td>
        `;
        
        tableBody.appendChild(row);
    });
}

// 设置全屏按钮
function setupFullscreenButtons() {
    // 实体统计全屏
    document.getElementById('entity-fullscreen').addEventListener('click', function() {
        toggleFullscreen('entity-stats', '实体类型分布');
    });
    
    // 关系统计全屏
    document.getElementById('relation-fullscreen').addEventListener('click', function() {
        toggleFullscreen('relation-stats', '关系类型分布');
    });
}

// 切换全屏显示
function toggleFullscreen(chartId, title) {
    const chartContainer = document.getElementById(chartId);
    
    // 检查是否已经在全屏模式
    const isFullscreen = chartContainer.classList.contains('fullscreen-chart');
    
    if (isFullscreen) {
        // 退出全屏
        chartContainer.classList.remove('fullscreen-chart');
        document.body.style.overflow = 'auto';
        
        // 删除关闭按钮
        const closeBtn = chartContainer.querySelector('.fullscreen-close');
        if (closeBtn) closeBtn.remove();
        
        // 重绘图表
        if (chartId === 'entity-stats' && entityChart) {
            entityChart.resize();
        } else if (chartId === 'relation-stats' && relationChart) {
            relationChart.resize();
        }
    } else {
        // 进入全屏
        chartContainer.classList.add('fullscreen-chart');
        document.body.style.overflow = 'hidden';
        
        // 添加标题和关闭按钮
        const closeBtn = document.createElement('div');
        closeBtn.className = 'fullscreen-close';
        closeBtn.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="mb-0">${title}</h5>
                <button class="btn btn-sm btn-outline-secondary">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `;
        
        chartContainer.insertBefore(closeBtn, chartContainer.firstChild);
        
        // 添加关闭事件
        closeBtn.querySelector('button').addEventListener('click', function() {
            toggleFullscreen(chartId, title);
        });
        
        // 重绘图表
        if (chartId === 'entity-stats' && entityChart) {
            entityChart.resize();
        } else if (chartId === 'relation-stats' && relationChart) {
            relationChart.resize();
        }
    }
}

// 格式化数字（添加千位分隔符）
function formatNumber(num) {
    return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,');
} 