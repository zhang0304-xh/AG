/**
 * 知识图谱可视化
 * 基于ECharts的知识图谱可视化，具有以下功能：
 * 1. 从API加载知识图谱数据（默认显示"桃树"节点及关联的10个节点）
 * 2. 单击节点显示右侧信息，右键点击展开相关节点
 * 3. 支持缩放、重置和稳定布局
 * 4. 修复窗口调整或右键检查时节点聚集问题
 * 5. 显示最近操作的节点及其相关节点的名称，首次进入默认全显示
 */

// 全局变量
let myChart = null;
let graphData = {
    nodes: [],
    links: []
};
let selectedNode = null;
let nodesToShowLabels = new Set();
let legendStatus = {};  // 格式: {类别名称: true/false} - true表示显示，false表示隐藏

// 页面加载后初始化图谱
document.addEventListener('DOMContentLoaded', function() {
    initKnowledgeGraph();

    document.getElementById('reset-graph').addEventListener('click', resetGraph);
    
    // 添加搜索功能
    document.getElementById('search-btn').addEventListener('click', function() {
        performSearch();
    });

    // 按回车键搜索
    document.getElementById('search-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });

    // 优化窗口调整时的图谱渲染
    let resizeTimeout;
    window.addEventListener('resize', function() {
        if (myChart) {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                // 调整图谱容器大小
                let graphContainer = document.getElementById('graph-container');
                if (graphContainer) {
                    // 确保图谱容器填满整个视图区域
                    let graphPanel = document.querySelector('.graph-panel');
                    if (graphPanel) {
                        graphContainer.style.width = graphPanel.clientWidth + 'px';
                        graphContainer.style.height = graphPanel.clientHeight + 'px';
                    }
                }
                myChart.resize();
                renderGraph();
            }, 200);
        }
    });
    
    // 初始调整容器大小
    setTimeout(() => {
        let graphContainer = document.getElementById('graph-container');
        let graphPanel = document.querySelector('.graph-panel');
        if (graphContainer && graphPanel) {
            graphContainer.style.width = graphPanel.clientWidth + 'px';
            graphContainer.style.height = graphPanel.clientHeight + 'px';
            if (myChart) {
                myChart.resize();
            }
        }
    }, 100);
    
    // 确保鼠标悬停在控制面板上时，仍能够滚动控制面板
    document.querySelector('.floating-control-panel').addEventListener('wheel', function(e) {
        // 阻止事件冒泡，防止影响图谱的缩放
        e.stopPropagation();
    });
});

/**
 * 初始化知识图谱
 */
function initKnowledgeGraph() {
    const container = document.getElementById('graph-container');
    if (!container) {
        console.error('找不到图谱容器');
        return;
    }

    myChart = echarts.init(container);

    const defaultOption = {
        title: {
            show: false
        },
        tooltip: {
            show: false, // 禁用悬停提示
            formatter: function(params) {
                if (params.dataType === 'node') {
                    return `<strong>${params.data.name}</strong>`;
                } else if (params.dataType === 'edge') {
                    return params.data.value || '关系';
                }
            },
            backgroundColor: 'rgba(50,50,50,0.9)',
            borderColor: '#333',
            textStyle: {
                color: '#ffffff'
            }
        },
        legend: {
            show: false
        },
        animation: true,
        series: [{
            type: 'graph',
            layout: 'force',
            data: [],
            links: [],
            categories: [],
            roam: true,
            draggable: true,
            focusNodeAdjacency: true,
            force: {
                repulsion: 200,
                edgeLength: 120,
                gravity: 0.1,
                friction: 0.6,
                layoutAnimation: true
            },
            label: {
                show: true,
                position: 'right',
                formatter: function(params) {
                    // 限制名称最多显示5个字符
                    const name = params.name || '';
                    return name.length > 5 ? name.substring(0, 5) + '...' : name;
                },
                fontSize: 12,
                color: '#333',
                backgroundColor: 'rgb(255,255,255)',
                padding: [3, 5],
                borderRadius: 3
            },
            lineStyle: {
                color: '#999',
                width: 1.5,
                curveness: 0.2,
                opacity: 0.7
            },
            emphasis: {
                scale: true,
                focus: 'adjacency',
                lineStyle: {
                    width: 2,
                    color: '#3a86ff'
                },
                itemStyle: {
                    borderWidth: 2,
                    shadowBlur: 10,
                    shadowColor: 'rgba(0, 0, 0, 0.3)'
                }
            },
            edgeLabel: {
                show: true,
                formatter: '{c}',
                fontSize: 11,
                backgroundColor: 'rgba(255,255,255,0.7)',
                padding: [2, 4],
                borderRadius: 2
            },
            itemStyle: {
                borderWidth: 1,
                borderColor: '#fff',
                shadowBlur: 2,
                shadowColor: 'rgba(0, 0, 0, 0.2)'
            }
        }]
    };

    myChart.setOption(defaultOption);

    myChart.on('click', function(params) {
        if (params.dataType === 'node') {
            updateNodesToShowLabels(params.data.id);
            showNodeInfo(params.data);
            renderGraph();
        }
    });

    myChart.on('contextmenu', function(params) {
        if (params.dataType === 'node') {
            updateNodesToShowLabels(params.data.id);
            expandNode(params.data);
            params.event.event.preventDefault();
        }
    });

    loadGraphData();
}

/**
 * 处理从 API 获取的图谱数据
 * @param {Object} data API 返回的原始数据
 * @param {string} centralNodeName 中心节点名称，用于设置特殊样式
 * @returns {Object} 处理后的图谱数据 { nodes, links }
 */
function processGraphData(data, centralNodeName = '桃树') {
    if (!data || !data.nodes || !data.links) {
        return { nodes: [], links: [] };
    }

    const processedNodes = data.nodes.map(node => {
        // 提取和保存节点的category属性
        let category = node.category;
        
        // 如果没有category但有properties中的类型信息，使用它
        if (!category && node.properties) {
            // 尝试从properties中提取类别信息
            if (node.properties.type) {
                category = node.properties.type;
            } else if (node.properties.category) {
                category = node.properties.category;
            }
        }
        
        return {
            ...node,
            name: node.name || '未命名节点', // 确保节点有默认名称
            symbolSize: node.name === centralNodeName ? 40 : 35, // 节点大小
            id: String(node.id), // 确保 ID 为字符串
            category: category   // 保留或设置category属性
        };
    });

    const processedLinks = data.links.map(link => ({
        ...link,
        value: link.value || '关系', // 确保关系有默认值
        source: String(link.source), // 确保 source 为字符串
        target: String(link.target) // 确保 target 为字符串
    }));

    console.log("处理后的节点数据(带类别):", processedNodes);
    return { nodes: processedNodes, links: processedLinks };
}

/**
 * 从 API 获取图谱数据
 * @param {string} url API 请求的 URL
 * @param {string} centralNodeName 中心节点名称
 * @param {Function} onSuccess 成功回调
 * @param {Function} onError 错误回调
 */
function fetchGraphData(url, centralNodeName, onSuccess, onError) {
    showLoading();
    console.log("请求API URL:", url);

    fetch(url)
        .then(response => {
            console.log("API响应状态:", response.status);
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log("API返回原始数据:", data);

            if (data.error) {
                throw new Error(data.error);
            }

            if (data && data.nodes && data.nodes.length > 0) {
                const processedData = processGraphData(data, centralNodeName);
                console.log("处理后的图谱数据:", processedData);
                onSuccess(processedData);
            } else {
                console.warn("API返回的数据为空");
                onError("获取知识图谱数据失败：返回的数据为空");
            }
            hideLoading();
        })
        .catch(error => {
            console.error('获取图谱数据出错:', error);
            onError(`获取图谱数据失败: ${error.message}`);
            hideLoading();
        });
}

/**
 * 更新需要显示标签的节点集合
 * @param {string} nodeId 最近操作的节点ID
 */
function updateNodesToShowLabels(nodeId) {
    nodesToShowLabels.clear();
    nodesToShowLabels.add(nodeId);

    graphData.links.forEach(link => {
        if (link.source === nodeId) {
            nodesToShowLabels.add(link.target);
        } else if (link.target === nodeId) {
            nodesToShowLabels.add(link.source);
        }
    });
}

/**
 * 加载图谱数据
 * @param {string} entityName 可选，指定加载特定实体及其邻居
 */
function loadGraphData(entityName = '桃树') {
    console.log(`正在加载实体 "${entityName}" 的知识图谱数据...`);

    let apiUrl = '/api/knowledge_graph/search_node_by_name';
    if (entityName) {
        apiUrl += `?entity_name=${encodeURIComponent(entityName)}`;
    }

    fetchGraphData(
        apiUrl,
        entityName,
        (processedData) => {
            // 清空现有数据，重新加载
            graphData = { nodes: [], links: [] };
            const newNodes = mergeGraphData(processedData, entityName);
            console.log(`成功加载实体 "${entityName}" 的图谱数据，添加了 ${newNodes} 个新节点`);

            // 默认显示所有节点的标签
            nodesToShowLabels.clear();
            graphData.nodes.forEach(node => nodesToShowLabels.add(node.id));

            renderGraph();
        },
        (error) => {
            showError(error);
        }
    );
}

/**
 * 渲染图谱
 */
function renderGraph() {
    if (!myChart || !graphData.nodes || graphData.nodes.length === 0) {
        console.error("无法渲染图谱：图表对象未初始化或数据为空");
        return;
    }

    console.log("正在渲染图谱，节点数量:", graphData.nodes.length);
    console.log("需要显示标签的节点:", Array.from(nodesToShowLabels));

    // 保存现有节点位置
    const nodePositions = {};
    graphData.nodes.forEach(node => {
        if (node.x !== undefined && node.y !== undefined) {
            nodePositions[node.id] = { x: node.x, y: node.y };
        }
    });
    
    // 收集所有可能的节点类别用于图例
    const categories = [];
    const categorySet = new Set();
    
    graphData.nodes.forEach(node => {
        if (node.category && !categorySet.has(node.category)) {
            categorySet.add(node.category);
            categories.push({
                name: node.category,
                itemStyle: {
                    color: getColorForNode({ category: node.category })
                }
            });
        }
    });
    
    // 更新右侧面板中的图例
    updateLegendPanel(categories);

    // 处理节点数据 - 多彩风格
    const processedNodes = graphData.nodes.map((node, index) => {
        const isCentralNode = node.name === '桃树'; // 中心节点
        const position = nodePositions[node.id] || {};
        const shouldShowLabel = nodesToShowLabels.has(node.id);
        
        // 获取基于category的颜色
        const nodeColor = getColorForNode(node, index);
        
        console.log(`节点 ${node.name} (ID: ${node.id}) 类别: ${node.category || '无'}, 颜色: ${nodeColor}`);
        
        // 生成节点样式 - 多彩风格
        const processedNode = {
            ...node,
            symbolSize: isCentralNode ? 40 : 35,
            symbol: 'circle',
            itemStyle: {
                color: nodeColor,
                borderWidth: 0,
                shadowBlur: 0
            },
            label: {
                show: shouldShowLabel,
                position: 'inside',
                formatter: function(params) {
                    // 限制名称最多显示5个字符
                    const name = params.name || '';
                    return name.length > 5 ? name.substring(0, 5) + '...' : name;
                },
                fontSize: 12,
                color: '#000',
                backgroundColor: 'transparent',
                padding: [0, 0]
            },
            // 固定位置，保持布局稳定
            x: isCentralNode ? myChart.getWidth() / 2 : position.x || undefined,
            y: isCentralNode ? myChart.getHeight() / 2 : position.y || undefined,
            fixed: isCentralNode
        };
        return processedNode;
    });

    // 处理连线数据
    const processedLinks = graphData.links.map(link => ({
        ...link,
        lineStyle: {
            width: 1,
            curveness: 0.15,
            opacity: 0.9,
            color: '#ccc'
        },
        label: {
            show: true,
            formatter: link.value,
            fontSize: 12,
            backgroundColor: 'transparent',
            color: '#666',
            padding: [0, 0]
        },
        emphasis: {
            lineStyle: {
                width: 1.5,
                color: '#aaa',
                opacity: 1
            }
        }
    }));

    // 设置图表配置
    const option = {
        tooltip: {
            show: false,
            formatter: function(params) {
                if (params.dataType === 'node') {
                    let tooltipContent = `<strong>${params.data.name}</strong>`;
                    
                    // 添加类别信息
                    if (params.data.category) {
                        tooltipContent += `<br/>类别: ${params.data.category}`;
                    }
                    
                    // 添加属性信息
                    if (params.data.properties) {
                        const relevantProps = Object.entries(params.data.properties)
                            .filter(([key, value]) => 
                                value && typeof value === 'string' && 
                                key !== 'name' && key !== 'id' && key !== 'category'
                            );
                        
                        if (relevantProps.length > 0) {
                            tooltipContent += '<br/><hr style="margin: 5px 0"/>';
                            relevantProps.slice(0, 3).forEach(([key, value]) => {
                                // 限制值的长度
                                const shortValue = value.length > 20 ? value.substring(0, 20) + '...' : value;
                                tooltipContent += `<br/>${key}: ${shortValue}`;
                            });
                            
                            if (relevantProps.length > 3) {
                                tooltipContent += `<br/>...等${relevantProps.length - 3}个属性`;
                            }
                        }
                    }
                    
                    return tooltipContent;
                } else if (params.dataType === 'edge') {
                    return params.data.value || '关系';
                }
            },
            backgroundColor: 'rgba(50,50,50,0.9)',
            borderColor: '#333',
            textStyle: {
                color: '#fff'
            }
        },
        legend: {
            show: false // 关闭内置图例，使用我们自定义的图例
        },
        series: [{
            type: 'graph',
            layout: 'force',
            data: processedNodes,
            links: processedLinks,
            categories: categories,
            roam: true,
            draggable: true,
            focusNodeAdjacency: true,
            force: {
                repulsion: 1000,
                edgeLength: 100,
                gravity: 0.1,
                friction: 0.6,
                layoutAnimation: true
            },
            // 启用平滑缩放
            zoomAnimation: true
        }]
    };

    myChart.setOption(option, true);

    // 设置初始动画
    myChart.dispatchAction({
        type: 'forceLayout',
        animation: {
            duration: 1000,
            easing: 'linear'
        }
    });

    // 调整视图
    myChart.resize();

    // 初始化视图为略微缩放状态
    setTimeout(() => {
        myChart.dispatchAction({
            type: 'graphRoam',
            zoom: 1,
            offsetX: 0,
            offsetY: 0
        });
        
        // 根据图例状态更新节点可见性
        updateNodesVisibility();
    }, 100);

    // 监听布局结束，保存节点位置
    myChart.on('finished', function() {
        const updatedNodes = myChart.getOption().series[0].data;
        updatedNodes.forEach((node, index) => {
            if (node.x !== undefined && node.y !== undefined) {
                graphData.nodes[index].x = node.x;
                graphData.nodes[index].y = node.y;
            }
        });
    });
}

/**
 * 更新右侧面板中的图例
 * @param {Array} categories 节点类别数组
 */
function updateLegendPanel(categories) {
    const legendContainer = document.querySelector('.legend-container');
    if (!legendContainer) return;
    
    // 清空现有图例
    legendContainer.innerHTML = '';
    
    // 初始化图例状态（如果不存在）
    if (Object.keys(legendStatus).length === 0) {
        // 默认所有类别都显示
        legendStatus = {'中心节点': true, '关联节点': true};
        categories.forEach(category => {
            if (category.name) {
                legendStatus[category.name] = true;
            }
        });
    }
    
    // 添加各类别节点的图例
    categories.forEach(category => {
        if (!category.name) return;
        
        // 初始化该类别状态（如果不存在）
        if (legendStatus[category.name] === undefined) {
            legendStatus[category.name] = true;
        }
        
        const categoryItem = document.createElement('div');
        categoryItem.className = 'legend-item' + (legendStatus[category.name] ? '' : ' legend-item-disabled');
        const color = category.itemStyle ? category.itemStyle.color : '#999';
        const displayName = category.name.length > 8 ? category.name.substring(0, 7) + '...' : category.name;
        
        categoryItem.innerHTML = `
            <span class="legend-color" style="background-color: ${color};"></span>
            <span class="legend-label">${displayName}</span>
        `;
        
        // 添加数据属性和点击事件
        categoryItem.setAttribute('data-category', category.name);
        categoryItem.addEventListener('click', function() {
            toggleLegendItem(category.name);
        });
        
        legendContainer.appendChild(categoryItem);
    });
}

/**
 * 切换图例项目的显示/隐藏状态
 * @param {string} categoryName 类别名称
 */
function toggleLegendItem(categoryName) {
    // 切换状态
    legendStatus[categoryName] = !legendStatus[categoryName];
    
    // 更新图例项目的视觉样式
    const legendItems = document.querySelectorAll('.legend-item');
    legendItems.forEach(item => {
        if (item.getAttribute('data-category') === categoryName) {
            if (legendStatus[categoryName]) {
                item.classList.remove('legend-item-disabled');
            } else {
                item.classList.add('legend-item-disabled');
            }
        }
    });
    
    // 更新图表中节点的显示/隐藏
    updateNodesVisibility();
}

/**
 * 根据图例状态更新节点的显示/隐藏
 */
function updateNodesVisibility() {
    if (!myChart) return;
    
    const option = myChart.getOption();
    if (!option.series || !option.series[0].data) return;
    
    const seriesData = option.series[0].data;
    
    // 更新节点可见性
    seriesData.forEach((node, index) => {
        let isVisible = true;
        
        // 根据节点类别判断是否显示
        if (node.category && legendStatus[node.category] !== undefined) {
            isVisible = legendStatus[node.category];
        } else { // 默认为关联节点
            isVisible = legendStatus['关联节点'];
        }
        
        // 设置节点可见性
        seriesData[index].itemStyle = {
            ...seriesData[index].itemStyle,
            opacity: isVisible ? 1 : 0.1
        };
        
        // 同时设置标签可见性
        seriesData[index].label = {
            ...seriesData[index].label,
            show: isVisible && nodesToShowLabels.has(node.id)
        };
    });
    
    // 更新连线可见性（只有当连接的两个节点都可见时，连线才可见）
    const edgeData = option.series[0].links;
    if (edgeData) {
        edgeData.forEach((edge, index) => {
            const sourceNode = seriesData.find(node => node.id === edge.source);
            const targetNode = seriesData.find(node => node.id === edge.target);
            
            const sourceVisible = sourceNode && sourceNode.itemStyle.opacity > 0.5;
            const targetVisible = targetNode && targetNode.itemStyle.opacity > 0.5;
            
            // 只有当源节点和目标节点都可见时，边才完全可见
            const edgeVisible = sourceVisible && targetVisible;
            
            edgeData[index].lineStyle = {
                ...edgeData[index].lineStyle,
                opacity: edgeVisible ? 0.9 : 0.1
            };
            
            edgeData[index].label = {
                ...edgeData[index].label,
                show: edgeVisible
            };
        });
    }
    
    // 更新图表
    myChart.setOption({
        series: [{
            data: seriesData,
            links: edgeData
        }]
    }, false);
    
    // 触发重绘
    myChart.getZr().refresh();
}

/**
 * 展开节点
 * @param {Object} node 要展开的节点
 */
function expandNode(node) {
    if (!node || !node.id) {
        console.error("无法展开节点：节点对象无效或没有ID");
        return;
    }

    console.log(`正在加载实体 "${node.name}" 的知识图谱数据...`);

    const apiUrl = `/api/knowledge_graph/node/${node.id}/expand`;

    fetchGraphData(
        apiUrl,
        node.name,
        (processedData) => {
            const newNodes = mergeGraphData(processedData, node.name);
            console.log(`成功加载实体 "${node.name}" 的图谱数据，添加了 ${newNodes} 个新节点`);

            // 重新计算需要显示标签的节点
            updateNodesToShowLabels(node.id);
            renderGraph();
            highlightNode(node.id);
        },
        (error) => {
            showError(error);
        }
    );
}

/**
 * 高亮显示节点
 * @param {string} nodeId 要高亮的节点ID
 */
function highlightNode(nodeId) {
    if (!myChart) return;

    const nodeIndex = graphData.nodes.findIndex(node => node.id === nodeId);
    if (nodeIndex >= 0) {
        myChart.dispatchAction({
            type: 'highlight',
            seriesIndex: 0,
            dataIndex: nodeIndex
        });
    }
}

/**
 * 合并图谱数据，避免重复
 * @param {Object} newData 新的图谱数据
 * @param {string} centralNodeName 中心节点名称
 * @returns {number} 添加的新节点数量
 */
function mergeGraphData(newData, centralNodeName) {
    const existingNodeIds = new Set(graphData.nodes.map(node => String(node.id)));
    let addedNodeCount = 0;

    // 合并节点
    newData.nodes.forEach(node => {
        const nodeId = String(node.id);
        if (!existingNodeIds.has(nodeId)) {
            graphData.nodes.push(node);
            existingNodeIds.add(nodeId);
            addedNodeCount++;
        }
    });

    // 合并关系
    const linkExists = (source, target) => {
        return graphData.links.some(link =>
            (link.source === source && link.target === target) ||
            (link.source === target && link.target === source)
        );
    };

    newData.links.forEach(link => {
        if (!linkExists(link.source, link.target)) {
            graphData.links.push(link);
        }
    });

    return addedNodeCount;
}

/**
 * 在右侧面板中显示节点详细信息
 * @param {Object} node 节点数据
 */
function showNodeInfo(node) {
    if (!node) return;
    
    selectedNode = node;
    
    const nodeInfoDetails = document.getElementById('node-info-details');
    if (!nodeInfoDetails) return;
    
    // 生成节点详细信息的HTML
    let htmlContent = '';
    
    // 顶部：节点详情标题和类型同一行，名称在下一行
    htmlContent += `<div style=\"display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;\">\n        <span style='font-size: 16px; font-weight: 600; color: #374151;'>节点详情</span>\n        ${node.category ? `<span style='font-size: 14px; color: #4e8cff; background: #eaf2ff; border-radius: 8px; padding: 2px 10px; margin-left: 10px; vertical-align: top; display: inline-block; line-height: 1.2;'>${node.category}</span>` : ''}\n    </div>`;
    htmlContent += `<div style='font-size: 15px; margin-bottom: 8px; word-break: break-all;'>${node.name || '未知'}</div>`;
    
    // 节点属性部分
    if (node.properties && Object.keys(node.properties).length > 0) {
        // 过滤掉已显示的基本信息
        const filteredProps = {...node.properties};
        if (filteredProps.name) delete filteredProps.name;
        if (filteredProps.id) delete filteredProps.id;
        if (filteredProps.type) delete filteredProps.type;
        if (filteredProps.category) delete filteredProps.category;
        
        if (Object.keys(filteredProps).length > 0) {
            htmlContent += `<div style='margin-bottom: 8px; color: #888;'>详细属性</div>`;
            htmlContent += `<table class="node-info-table">`;
            for (const [key, value] of Object.entries(filteredProps)) {
                const displayKey = key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ');
                htmlContent += `<tr><td style='color:#888;'>${displayKey}</td><td>${value}</td></tr>`;
            }
            htmlContent += `</table>`;
        }
    }
    
    // 添加一些相关操作的按钮
    htmlContent += `<div class="node-actions mt-3">`;
    htmlContent += `<button class="btn btn-sm btn-outline-primary w-100 mb-2" onclick="expandNode(selectedNode)">
                        <i class="bi bi-diagram-3"></i> 展开关联节点
                    </button>`;
    htmlContent += `</div>`;
    
    // 更新内容
    nodeInfoDetails.innerHTML = htmlContent;
    highlightNode(node.id);
}

/**
 * 重置图谱
 */
function resetGraph() {
    // 重新加载初始图谱数据
    nodesToShowLabels.clear();
    loadGraphData();
}

/**
 * 显示加载中状态
 */
function showLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

/**
 * 隐藏加载中状态
 */
function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

/**
 * 显示错误消息
 * @param {string} message 错误消息
 */
function showError(message) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }

    console.error("错误:", message);
}

/**
 * 获取节点颜色 - 根据category属性分配不同颜色
 * @param {Object} node 节点数据
 * @param {number} index 节点索引
 * @returns {string} 颜色值
 */
function getColorForNode(node, index) {
    // 根据category分配颜色
    const categoryColors = {
        '标题': '#4E79A7',       // Soft blue
        '网址': '#A0A0A0',       // Medium gray
        '摘要': '#8C8C8C',       // Darker gray
        '关键字': '#59A14F',     // Leaf green
        '作者': '#EDC948',      // Golden yellow
        '防治方法': '#499894',   // Teal
        '期刊': '#79706E',      // Warm gray
        '症状': '#E15759',      // Coral red
        '发生规律': '#B07AA1',   // Muted purple
        '简介': '#FF9DA7',      // Soft pink
        '别称': '#9C755F',      // Taupe
        '学名': '#F28E2B',      // Orange
        '生产厂家': '#86BCB6',   // Seafoam green
        '病害': '#D37295',      // Dusty pink
        '形态特征': '#B6992D',   // Olive
        '生活习性': '#41AB5D',   // Emerald green
        '虫害': '#D4A6C8',      // Lavender
        '作物': '#8CD17D',      // Light green
        '子类': '#BAB0AC',      // Light gray
        '大类': '#6B6B6B'       // Dark gray
    };
    
    // 默认颜色
    const defaultColors = [
        '#4A90E2', '#67B7A0', '#D46C91', '#FF7B54', '#7E57C2', 
        '#FFB26B', '#26C6DA', '#66BB6A', '#FFA726', '#5C6BC0'
    ];
    
    
    // 2. 检查是否有category属性并匹配预设颜色
    if (node.category && categoryColors[node.category]) {
        return categoryColors[node.category];
    }
    
    // 3. 如果没有category或category没有预设颜色，使用默认颜色数组
    if (index !== undefined) {
        return defaultColors[index % defaultColors.length];
    }
    
    // 4. 如果以上都不适用，返回默认颜色
    return '#D46C91';
}

/**
 * 执行搜索
 */
function performSearch() {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;
    
    const query = searchInput.value.trim();
    if (!query) {
        showError('请输入搜索内容');
        return;
    }
    
    console.log(`正在搜索: "${query}"`);
    
    // 构建搜索API URL
   const apiUrl = `/api/knowledge_graph/search_node_by_name?entity_name=${encodeURIComponent(query)}`;
    
    fetchGraphData(
        apiUrl,
        query,
        (processedData) => {
            if (processedData.nodes.length === 0) {
                showError(`未找到与 "${query}" 相关的实体`);
                return;
            }
            
            // 替换当前图谱数据
            graphData = { nodes: [], links: [] };
            const newNodes = mergeGraphData(processedData, null);
            console.log(`搜索成功，找到 ${newNodes} 个相关节点`);
            
            // 显示所有节点的标签
            nodesToShowLabels.clear();
            graphData.nodes.forEach(node => nodesToShowLabels.add(node.id));
            
            renderGraph();
        },
        (error) => {
            showError(`搜索失败: ${error}`);
        }
    );
}