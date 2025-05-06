document.addEventListener('DOMContentLoaded', () => {
    // 获取DOM元素
    const questionInput = document.getElementById('question-input');
    const submitBtn = document.getElementById('submit-btn');
    const resultSection = document.getElementById('result-section');
    const loadingElement = document.getElementById('loading');
    const resultContent = document.getElementById('result-content');
    const errorMessage = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    const questionDisplay = document.getElementById('question-display');
    const answerText = document.getElementById('answer-text');
    const questionType = document.getElementById('question-type');
    const coreEntities = document.getElementById('core-entities');
    const queryIntent = document.getElementById('query-intent');
    const kgTriplets = document.getElementById('kg-triplets');
    const exampleLinks = document.querySelectorAll('.example-link');
    
    // 初始化折叠面板
    initCollapsible();
    
    // 添加事件监听器
    submitBtn.addEventListener('click', handleSubmit);
    questionInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSubmit();
        }
    });
    
    // 添加示例问题点击事件
    exampleLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            questionInput.value = link.textContent;
            handleSubmit();
        });
    });
    
    // 处理问题提交
    async function handleSubmit() {
        const question = questionInput.value.trim();
        
        if (!question) {
            showError('请输入您的问题！');
            return;
        }
        
        // 显示加载状态
        resultSection.style.display = 'block';
        loadingElement.style.display = 'flex';
        resultContent.style.display = 'none';
        errorMessage.style.display = 'none';
        
        try {
            // 获取用户ID（如果已登录）
            console.log(localStorage);
            const user_info_str = localStorage.getItem('userInfo');
            const user_info = user_info_str ? JSON.parse(user_info_str) : null;
            const user_id = user_info?.user_id;

            console.log("搜索请求，user_id:", user_id, "类型:", typeof user_id);

            // 发送请求到后端API
            const response = await fetch('qa', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question,
                    user_id: user_id || null  // 明确处理undefined情况
                })
            });
            // 检查响应的内容类型
            const contentType = response.headers.get('content-type');
            
            if (!contentType || !contentType.includes('application/json')) {
                // 如果响应不是JSON，直接显示文本内容
                const textContent = await response.text();
                throw new Error(`服务器返回了非JSON格式的响应: ${textContent.substring(0, 150)}...`);
            }
            
            // 解析JSON响应
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.message || '服务器错误，请稍后再试');
            }
            
            // 处理成功响应
            displayResult(data);
            
        } catch (error) {
            console.error('Error:', error);
            showError(error.message || '请求失败，请检查网络连接');
        } finally {
            // 隐藏加载状态
            loadingElement.style.display = 'none';
        }
    }
    
    // 显示结果
    function displayResult(data) {
        // 显示问题
        questionDisplay.textContent = data.question;
        
        // 显示答案
        answerText.textContent = data.answer;
        
        // 填充分析数据
        const analysis = data.analysis || {};
        questionType.textContent = analysis.question_type || '未识别';
        
        // 处理核心实体
        const entities = analysis.core_entities || [];
        coreEntities.textContent = entities.length > 0 ? entities.join('、') : '无';
        
        // 查询意图
        queryIntent.textContent = analysis.query_intent || '未识别';
        
        // 知识图谱三元组
        const triplets = data.knowledge_graph || [];
        if (triplets.length > 0) {
            kgTriplets.innerHTML = formatTriplets(triplets);
        } else {
            kgTriplets.textContent = '无三元组信息';
        }
        
        // 显示结果内容
        resultContent.style.display = 'block';
    }
    
    // 格式化三元组显示
    function formatTriplets(triplets) {
        let html = '';
        
        triplets.forEach((triplet, index) => {
            const head = triplet.head || '未知';
            const relation = triplet.relation || '未知';
            const tail = triplet.tail || '未知';
            
            html += `<div class="triplet">
                <span class="triplet-index">${index + 1}.</span>
                <span class="triplet-head">${head}</span>
                <span class="triplet-relation">--[${relation}]--></span>
                <span class="triplet-tail">${tail}</span>
            </div>`;
        });
        
        return html;
    }
    
    // 显示错误信息
    function showError(message) {
        resultSection.style.display = 'block';
        loadingElement.style.display = 'none';
        resultContent.style.display = 'none';
        errorMessage.style.display = 'block';
        errorText.textContent = message;
    }
    
    // 初始化折叠面板
    function initCollapsible() {
        const collapsibles = document.querySelectorAll('.collapsible');
        
        collapsibles.forEach(collapsible => {
            const header = collapsible.querySelector('.collapsible-header');
            
            header.addEventListener('click', () => {
                collapsible.classList.toggle('active');
            });
        });
    }
}); 