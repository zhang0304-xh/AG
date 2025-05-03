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

// 页面加载后初始化图谱
document.addEventListener('DOMContentLoaded', function() {
    initKnowledgeGraph();

    document.getElementById('zoom-in').addEventListener('click', function() {
        if (myChart) {
            myChart.dispatchAction({
                type: 'dataZoom',
                start: 0,
                end: 50
            });
        }
    });

    document.getElementById('zoom-out').addEventListener('click', function() {
        if (myChart) {
            myChart.dispatchAction({
                type: 'dataZoom',
                start: 0,
                end: 100
            });
        }
    });

    document.getElementById('reset-graph').addEventListener('click', resetGraph);

    let resizeTimeout;
    window.addEventListener('resize', function() {
        if (myChart) {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                myChart.resize();
                renderGraph();
            }, 200);
        }
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
            show: true,
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
                color: '#fff'
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
                repulsion: 500,
                edgeLength: 150,
                gravity: 0.2,
                friction: 0.8,
                layoutAnimation: true
            },
            label: {
                show: true,
                position: 'right',
                formatter: '{b}',
                fontSize: 14,
                fontWeight: 'bold',
                color: '#333'
            },
            lineStyle: {
                color: '#666',
                width: 2,
                curveness: 0.3,
                opacity: 0.8
            },
            emphasis: {
                scale: true,
                focus: 'adjacency',
                lineStyle: {
                    width: 4,
                    color: '#333'
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
                fontSize: 12,
                backgroundColor: 'rgba(255,255,255,0.7)',
                padding: [2, 4],
                borderRadius: 2
            },
            itemStyle: {
                borderWidth: 2,
                borderColor: '#fff',
                shadowBlur: 5,
                shadowColor: 'rgba(0, 0, 0, 0.3)'
            }
        }]
    };

    myChart.setOption(defaultOption);

    myChart.on('click', function(params) {
        if (params.dataType === 'node') {
            updateNodesToShowLabels(params.data.id);
            showNodeInfo(params.data);
            renderGraph();
        } else {
            params.event.event.stopPropagation();
            params.event.event.preventDefault();
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

    const processedNodes = data.nodes.map(node => ({
        ...node,
        name: node.name || '未命名节点', // 确保节点有默认名称
        symbolSize: node.name === centralNodeName ? 50 : 30, // 中心节点更大
        id: String(node.id) // 确保 ID 为字符串
    }));

    const processedLinks = data.links.map(link => ({
        ...link,
        value: link.value || '关系', // 确保关系有默认值
        source: String(link.source), // 确保 source 为字符串
        target: String(link.target) // 确保 target 为字符串
    }));

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

    let apiUrl = '/api/knowledge_graph/visualization';
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

    const nodePositions = {};
    graphData.nodes.forEach(node => {
        if (node.x !== undefined && node.y !== undefined) {
            nodePositions[node.id] = { x: node.x, y: node.y };
        }
    });

    const processedNodes = graphData.nodes.map((node, index) => {
        const isCentralNode = node.name === '桃树';
        const position = nodePositions[node.id] || {};
        const shouldShowLabel = nodesToShowLabels.has(node.id);
        console.log(`节点 ${node.name} (ID: ${node.id}) 是否显示标签: ${shouldShowLabel}`);
        const processedNode = {
            ...node,
            symbolSize: isCentralNode ? 50 : 30,
            itemStyle: {
                color: getColorForNode(node, index),
                borderWidth: isCentralNode ? 4 : 2
            },
            label: {
                show: shouldShowLabel,
                position: 'right',
                formatter: '{b}',
                fontSize: 14,
                fontWeight: 'bold',
                color: '#333'
            },
            x: isCentralNode ? myChart.getWidth() / 2 : position.x || undefined,
            y: isCentralNode ? myChart.getHeight() / 2 : position.y || undefined,
            fixed: isCentralNode
        };
        return processedNode;
    });

    const option = {
        series: [{
            type: 'graph',
            layout: 'force',
            data: processedNodes,
            links: graphData.links.map(link => ({
                ...link,
                lineStyle: {
                    width: 2,
                    curveness: 0.3,
                    opacity: 0.8
                },
                label: {
                    show: true,
                    formatter: link.value,
                    backgroundColor: 'rgba(255,255,255,0.7)',
                    padding: [2, 4],
                    borderRadius: 2
                }
            })),
            categories: [],
            roam: true,
            draggable: true,
            focusNodeAdjacency: true,
            force: {
                repulsion: 500,
                edgeLength: 200,
                gravity: 0.2,
                friction: 0.8,
                layoutAnimation: true
            }
        }]
    };

    myChart.setOption(option, true);

    myChart.dispatchAction({
        type: 'forceLayout',
        animation: {
            duration: 1000,
            easing: 'cubicOut'
        }
    });

    myChart.resize();

    setTimeout(() => {
        myChart.dispatchAction({
            type: 'graphRoam',
            zoom: 1.2,
            offsetX: myChart.getWidth() / 2,
            offsetY: myChart.getHeight() / 2
        });
    }, 100);

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
 * 显示节点信息
 * @param {Object} node 节点数据
 */
function showNodeInfo(node) {
    if (!node) {
        return;
    }

    const infoContent = document.getElementById('info-content');
    if (!infoContent) {
        return;
    }

    let html = `
        <div class="node-info">
            <h5 class="mb-3 text-primary">${node.name || '未命名节点'}</h5>
            <div class="node-properties">
    `;

    if (node.properties && Object.keys(node.properties).length > 0) {
        for (const [key, value] of Object.entries(node.properties)) {
            if (value && key !== 'name') {
                html += `
                    <div class="node-property">
                        <strong>${key}:</strong> ${value}
                    </div>
                `;
            }
        }
    } else {
        html += `<div class="text-muted">没有可用的属性信息</div>`;
    }

    if (node.description) {
        html += `
            <div class="node-property mt-2">
                <strong>描述:</strong> ${node.description}
            </div>
        `;
    }

    html += `
            </div>
            <div class="mt-3 alert alert-info">
                <small>右键点击节点展开关联节点</small>
            </div>
        </div>
    `;

    infoContent.innerHTML = html;
    selectedNode = node;
    highlightNode(node.id);
}

/**
 * 重置图谱
 */
function resetGraph() {
    graphData = {
        nodes: [],
        links: []
    };
    nodesToShowLabels.clear();
    console.log("重置图谱，重新加载默认数据...");

    loadGraphData();

    const infoContent = document.getElementById('info-content');
    if (infoContent) {
        infoContent.innerHTML = '<div class="text-muted text-center py-3">点击图谱中的节点查看详细信息</div>';
    }

    selectedNode = null;
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
 * 获取节点颜色
 * @param {Object} node 节点数据
 * @param {number} index 节点索引
 * @returns {string} 颜色值
 */
function getColorForNode(node, index) {
    if (node.name === '桃树') {
        return '#ff7875';
    }

    const colors = [
        '#1890ff', '#52c41a', '#faad14', '#f5222d',
        '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16'
    ];

    let colorIndex = 0;
    if (node.category !== undefined) {
        colorIndex = typeof node.category === 'number' ? node.category : 0;
    } else {
        const id = String(node.id);
        let hash = 0;
        for (let i = 0; i < id.length; i++) {
            hash = (hash << 5) - hash + id.charCodeAt(i);
            hash |= 0;
        }
        colorIndex = Math.abs(hash);
    }

    if (index !== undefined) {
        colorIndex = (colorIndex + index) % colors.length;
    }

    return colors[colorIndex % colors.length];
}