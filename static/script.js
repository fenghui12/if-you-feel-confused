document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatWindow = document.getElementById('chat-window');
    const modeSelector = document.getElementById('chat-mode');

    // 弹窗相关元素
    const modal = document.getElementById('persona-modal');
    
    // 提问流程视图
    const modalQuestionView = document.getElementById('modal-question-view');
    const modalQuestionText = document.getElementById('modal-question-text');
    const personaForm = document.getElementById('persona-form');
    const personaInput = document.getElementById('persona-input');
    
    // 提炼确认视图
    const modalConfirmationView = document.getElementById('modal-confirmation-view');
    const processedTextContent = document.getElementById('processed-text-content');
    const modalRetryButton = document.getElementById('modal-retry');
    const modalConfirmUpdateButton = document.getElementById('modal-confirm-update');

    // 建议流程视图
    const modalSuggestionView = document.getElementById('modal-suggestion-view');
    const suggestionTextContent = document.getElementById('suggestion-text-content');
    const modalConfirmSuggestionButton = document.getElementById('modal-confirm-suggestion');

    const modalCancelButtons = document.querySelectorAll('.modal-cancel');

    // 设置弹窗相关元素
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const settingsCancelBtn = document.getElementById('settings-cancel-btn');
    const settingsSaveBtn = document.getElementById('settings-save-btn');
    const personaSettingInput = document.getElementById('persona-setting-input');
    const expertsList = document.getElementById('experts-list');
    const addExpertBtn = document.getElementById('add-expert-btn');

    // 清空历史弹窗相关元素
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    const clearHistoryModal = document.getElementById('clear-history-modal');
    const clearCancelBtn = document.getElementById('clear-cancel-btn');
    const clearConfirmBtn = document.getElementById('clear-confirm-btn');

    // --- 状态变量 ---
    let processedPersonaText = ''; // 用于在提炼和确认步骤之间传递文本
    let suggestedPersonaText = ''; // 用于在建议和确认步骤之间传递文本

    // --- 事件监听 ---
    chatForm.addEventListener('submit', handleFormSubmit);
    modeSelector.addEventListener('change', (e) => loadHistoryForMode(e.target.value));
    
    // 提问流程事件
    personaForm.addEventListener('submit', handleInitialPersonaSubmit); // 步骤1: 提交回答
    modalRetryButton.addEventListener('click', showQuestionView); // 返回上一步
    modalConfirmUpdateButton.addEventListener('click', () => handleConfirmPersonaUpdate(processedPersonaText)); // 步骤2: 确认提炼结果
    
    // 建议流程事件
    modalConfirmSuggestionButton.addEventListener('click', () => handleConfirmPersonaUpdate(suggestedPersonaText)); // 直接确认建议

    modalCancelButtons.forEach(btn => btn.addEventListener('click', () => {
        modal.style.display = 'none';
        // 重置状态
        processedPersonaText = '';
        suggestedPersonaText = '';
    }));

    // 设置弹窗事件
    settingsBtn.addEventListener('click', openSettingsModal);
    settingsCancelBtn.addEventListener('click', () => settingsModal.style.display = 'none');
    settingsSaveBtn.addEventListener('click', saveSettings);
    addExpertBtn.addEventListener('click', addNewExpertEditor);
    // 使用事件委托处理动态添加的删除按钮
    expertsList.addEventListener('click', (e) => {
        if (e.target.classList.contains('btn-delete')) {
            e.target.closest('.expert-editor').remove();
        }
    });

    // 清空历史弹窗事件
    clearHistoryBtn.addEventListener('click', () => clearHistoryModal.style.display = 'flex');
    clearCancelBtn.addEventListener('click', () => clearHistoryModal.style.display = 'none');
    clearConfirmBtn.addEventListener('click', handleClearHistory);

    // --- 初始化 ---
    initializeApp(); // 启动应用的唯一入口


    // --- 核心函数 ---

    /**
     * 初始化应用
     * 1. 获取最新配置来构建专家下拉菜单
     * 2. 加载默认专家的历史记录
     */
    async function initializeApp() {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) {
                // 如果配置加载失败，显示错误并停止
                await handleApiError(response, '初始化应用配置失败');
                return;
            }
            const config = await response.json();
            // 使用最新配置更新下拉菜单，这个函数会自动加载历史记录
            updateModeSelector(config.experts);
        } catch (error) {
            console.error('Initialization error:', error);
            appendMessage({ content: '应用初始化失败，请检查网络并刷新页面。', role: 'assistant' }, true);
        }
    }

    /**
     * 处理聊天表单提交
     */
    async function handleFormSubmit(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        const selectedMode = modeSelector.value;
        appendMessage({ content: message, role: 'user' });
        messageInput.value = '';
        const loadingMessage = showLoadingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, mode: selectedMode }),
            });
            
            removeLoadingIndicator(loadingMessage);

            if (!response.ok) {
                await handleApiError(response);
                return;
            }

            const data = await response.json();
            
            // 如果AI有纯文本回复，先显示它
            if (data.reply) {
                appendMessage({ content: data.reply, role: 'assistant' });
            }

            // 根据类型处理人设更新请求
            if (data.update_type === 'question') {
                showQuestionModal(data.update_info);
            } else if (data.update_type === 'suggestion') {
                showSuggestionModal(data.update_info);
            }

        } catch (error) {
            removeLoadingIndicator(loadingMessage);
            console.error('Error:', error);
            appendMessage({ content: '无法连接到服务器，请检查你的网络连接。', role: 'assistant' }, true);
        }
    }

    /**
     * 第一步(提问流程): 处理人设补全表单的初始提交 (提炼)
     */
    async function handleInitialPersonaSubmit(e) {
        e.preventDefault();
        const rawInfo = personaInput.value.trim();
        if (!rawInfo) return;

        // 可选：添加加载指示
        try {
            const response = await fetch('/api/process_persona_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ raw_info: rawInfo }),
            });

            if (!response.ok) {
                await handleApiError(response, '提炼信息时出错');
                return;
            }

            const data = await response.json();
            processedPersonaText = data.processed_text; // 保存提炼后的文本
            showConfirmationView(processedPersonaText); // 显示确认视图

        } catch (error) {
            console.error('Error processing persona info:', error);
            appendMessage({ content: '处理您的人设信息时遇到网络问题。', role: 'assistant' }, true);
        }
    }

    /**
     * 最终步骤: 处理人设更新 (适用于两种流程)
     * @param {string} textToAdd - 要添加到人设的最终文本
     */
    async function handleConfirmPersonaUpdate(textToAdd) {
        if (!textToAdd) return;

        try {
            // 1. 获取当前最新配置
            const configResponse = await fetch('/api/config');
            if (!configResponse.ok) {
                await handleApiError(configResponse, '获取当前配置失败，无法更新人设');
                return;
            }
            const currentConfig = await configResponse.json();

            // 2. 在现有配置上追加新的人设信息
            currentConfig.base_persona += `\n- ${textToAdd}`;

            // 3. 将更新后的完整配置保存回去
            const updateResponse = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentConfig)
            });

            if (!updateResponse.ok) {
                await handleApiError(updateResponse, '保存更新后的人设失败');
                return;
            }

            modal.style.display = 'none';
            // 重置所有相关状态
            personaInput.value = '';
            processedPersonaText = '';
            suggestedPersonaText = '';
            
            appendMessage({ content: '谢谢你！你的信息已更新，现在我更了解你了。', role: 'assistant' });

        } catch (error) {
            console.error('Error updating persona:', error);
            appendMessage({ content: '更新人设时遇到网络问题，请稍后再试。', role: 'assistant' }, true);
        }
    }

    /**
     * 加载并显示指定模式的聊天记录
     * @param {string} mode - 要加载的模式 (e.g., 'casual_chat')
     */
    async function loadHistoryForMode(mode) {
        clearChatWindow();
        const loadingMessage = showLoadingIndicator();
        try {
            const response = await fetch(`/api/history/${mode}`);
            removeLoadingIndicator(loadingMessage);

            if (!response.ok) {
                await handleApiError(response);
                return;
            }

            const data = await response.json();
            if (data.history && data.history.length > 0) {
                data.history.forEach(message => appendMessage(message));
            } else {
                // 如果没有历史记录，显示一个与模式匹配的欢迎语
                const expertName = modeSelector.querySelector(`option[value="${mode}"]`).textContent;
                appendMessage({ content: `你好！我是${expertName}，开始我们的对话吧。`, role: 'assistant' });
            }
        } catch (error) {
            removeLoadingIndicator(loadingMessage);
            console.error('Error loading history:', error);
            appendMessage({ content: '加载历史记录失败。', role: 'assistant' }, true);
        }
    }

    /**
     * 处理API返回的错误
     * @param {Response} response - fetch 返回的 response 对象
     * @param {string} defaultMessage - 默认的错误提示信息
     */
    async function handleApiError(response, defaultMessage = '抱歉，服务出错了，请稍后再试。') {
        let errorMessage = defaultMessage;
        try {
            const errorData = await response.json();
            errorMessage = errorData.detail || defaultMessage;
        } catch (e) {
            // 如果解析json失败，使用默认信息
        }
        appendMessage({ content: errorMessage, role: 'assistant' }, true);
    }

    /**
     * 处理清空历史记录的确认操作
     */
    async function handleClearHistory() {
        const selectedMode = modeSelector.value;
        if (!selectedMode) {
            alert("没有选中的模式，无法清空。");
            return;
        }

        try {
            const response = await fetch(`/api/history/${selectedMode}`, {
                method: 'DELETE',
            });

            clearHistoryModal.style.display = 'none';

            if (!response.ok) {
                // 使用通用的错误处理函数
                await handleApiError(response, '清空历史记录失败。');
                return;
            }

            // 成功后，重新加载当前模式的"历史记录"（此时应为空），
            // 这会自动清空并显示欢迎语
            await loadHistoryForMode(selectedMode);
            
            // 可以选择性地给一个更明确的提示
            // appendMessage({ content: '当前聊天记录已清空。', role: 'assistant' });

        } catch (error) {
            clearHistoryModal.style.display = 'none';
            console.error('Error clearing history:', error);
            appendMessage({ content: '清空历史记录时遇到网络问题。', role: 'assistant' }, true);
        }
    }

    // --- 辅助函数 ---

    function appendMessage(message, isError = false) {
        const sender = message.role === 'user' ? 'user' : 'assistant';
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', sender);

        if (isError) {
            messageElement.style.backgroundColor = '#ff4d4d';
            messageElement.style.color = 'white';
        }
        
        const p = document.createElement('p');
        p.textContent = message.content;
        messageElement.appendChild(p);

        chatWindow.appendChild(messageElement);
        scrollToBottom();
    }

    function clearChatWindow() {
        chatWindow.innerHTML = '';
    }

    function showLoadingIndicator() {
        const loadingElement = document.createElement('div');
        loadingElement.classList.add('message', 'assistant', 'loading');
        
        const p = document.createElement('p');
        p.textContent = '正在思考中';

        const animation = document.createElement('div');
        animation.classList.add('dot-flashing');
        
        p.appendChild(animation);
        loadingElement.appendChild(p);
        chatWindow.appendChild(loadingElement);
        scrollToBottom();
        return loadingElement;
    }

    function removeLoadingIndicator(loadingElement) {
        if (loadingElement) {
            loadingElement.remove();
        }
    }

    function scrollToBottom() {
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // --- 弹窗视图管理 ---

    /**
     * 显示提问弹窗 (用于 'question' 类型)
     * @param {string} question - AI提出的问题
     */
    function showQuestionModal(question) {
        modalQuestionText.textContent = question;
        showQuestionView(); // 确保显示的是初始提问视图
        modal.style.display = 'flex';
        personaInput.focus();
    }

    /**
     * 显示建议弹窗 (用于 'suggestion' 类型)
     * @param {string} suggestion - AI提出的建议文本
     */
    function showSuggestionModal(suggestion) {
        // 从建议文本中提取出要添加的具体人设
        // 例如，从 "我发现您...是否将"感情状况：恋爱中"...？" 提取 "感情状况：恋爱中"
        const match = suggestion.match(/"([^"]+)"/);
        suggestedPersonaText = match ? match[1] : suggestion; // 如果匹配失败，就用整个建议作为后备

        suggestionTextContent.textContent = suggestedPersonaText;
        showSuggestionView();
        modal.style.display = 'flex';
    }
    
    /**
     * 切换到提问视图
     */
    function showQuestionView() {
        modalQuestionView.style.display = 'block';
        modalConfirmationView.style.display = 'none';
        modalSuggestionView.style.display = 'none';
        personaInput.focus();
    }

    /**
     * 切换到提炼确认视图
     * @param {string} text - 提炼后的文本
     */
    function showConfirmationView(text) {
        processedTextContent.textContent = text;
        modalQuestionView.style.display = 'none';
        modalConfirmationView.style.display = 'block';
        modalSuggestionView.style.display = 'none';
    }
    
    /**
     * 切换到建议确认视图
     */
    function showSuggestionView() {
        modalQuestionView.style.display = 'none';
        modalConfirmationView.style.display = 'none';
        modalSuggestionView.style.display = 'block';
    }

    // --- 设置弹窗相关函数 ---

    /**
     * 打开设置弹窗并加载配置
     */
    async function openSettingsModal() {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) {
                await handleApiError(response, '加载配置失败');
                return;
            }
            const config = await response.json();
            personaSettingInput.value = config.base_persona;
            renderExpertsList(config.experts);
            settingsModal.style.display = 'flex';
        } catch (error) {
            console.error('Error fetching config:', error);
            // 这里可以在聊天窗口显示错误，或者在设置弹窗内显示
        }
    }
    
    /**
     * 渲染专家列表以供编辑
     * @param {object} experts - 从后端获取的专家对象
     */
    function renderExpertsList(experts) {
        expertsList.innerHTML = '';
        for (const key in experts) {
            const expert = experts[key];
            const editorHTML = `
                <div class="expert-editor" data-key="${key}">
                    <div class="expert-editor-fields">
                        <label>专家名称:</label>
                        <input type="text" class="expert-name-input" value="${expert.name}">
                        <label>专家唯一标识 (不可修改):</label>
                        <input type="text" class="expert-key-input" value="${key}" disabled>
                    </div>
                    <div class="expert-editor-fields">
                        <label>核心提示词:</label>
                        <textarea class="expert-prompt-input" rows="4">${expert.prompt}</textarea>
                    </div>
                    <div class="expert-editor-actions">
                         <button type="button" class="btn-delete">删除</button>
                    </div>
                </div>
            `;
            expertsList.insertAdjacentHTML('beforeend', editorHTML);
        }
    }

    /**
     * 在UI上添加一个新的专家编辑器
     */
    function addNewExpertEditor() {
        const newKey = `expert_${Date.now()}`; // 用时间戳确保key的唯一性
        const editorHTML = `
            <div class="expert-editor" data-key="${newKey}">
                 <div class="expert-editor-fields">
                    <label>专家名称:</label>
                    <input type="text" class="expert-name-input" value="新专家">
                    <label>专家唯一标识 (不可修改):</label>
                    <input type="text" class="expert-key-input" value="${newKey}" disabled>
                </div>
                <div class="expert-editor-fields">
                    <label>核心提示词:</label>
                    <textarea class="expert-prompt-input" rows="4">你是一个全新的专家...</textarea>
                </div>
                <div class="expert-editor-actions">
                     <button type="button" class="btn-delete">删除</button>
                </div>
            </div>
        `;
        expertsList.insertAdjacentHTML('beforeend', editorHTML);
    }
    
    /**
     * 收集并保存所有设置
     */
    async function saveSettings() {
        // 1. 先从服务器获取最新的配置，以确保我们拥有最新的聊天记录
        let currentConfig;
        try {
            const response = await fetch('/api/config');
            if (!response.ok) {
                await handleApiError(response, '无法获取当前配置，保存失败。');
                return;
            }
            currentConfig = await response.json();
        } catch (error) {
            console.error('Error fetching config before saving:', error);
            alert('网络错误：无法获取当前配置，保存操作已取消。');
            return;
        }

        const newExpertsData = {};
        const expertEditors = expertsList.querySelectorAll('.expert-editor');
        
        // 2. 遍历UI上的每一个专家编辑器，构建新的专家对象
        expertEditors.forEach(editor => {
            const key = editor.dataset.key;
            const name = editor.querySelector('.expert-name-input').value;
            const prompt = editor.querySelector('.expert-prompt-input').value;
            
            // 关键修复：如果旧配置中存在该专家，则继承其聊天记录；否则视其为新专家，历史为空数组
            const existingHistory = (currentConfig.experts && currentConfig.experts[key]) 
                                    ? currentConfig.experts[key].history 
                                    : [];
            
            newExpertsData[key] = { name, prompt, history: existingHistory }; 
        });

        // 3. 构建最终要发送到后端的完整配置对象
        const newConfigPayload = {
            base_persona: personaSettingInput.value,
            experts: newExpertsData
        };

        // 4. 发送更新后的完整配置到后端
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newConfigPayload)
            });

            if (!response.ok) {
                await handleApiError(response, '保存配置失败');
                return;
            }
            
            settingsModal.style.display = 'none';
            updateModeSelector(newExpertsData);
            alert('配置已成功保存！');

        } catch (error) {
             console.error('Error saving config:', error);
             alert('网络错误：保存配置失败。');
        }
    }

    /**
     * 更新主聊天页面的模式选择器
     * @param {object} experts - 最新的专家对象
     */
    function updateModeSelector(experts) {
        modeSelector.innerHTML = '';
        for (const key in experts) {
            const option = document.createElement('option');
            option.value = key;
            option.textContent = experts[key].name;
            modeSelector.appendChild(option);
        }
        // 重新加载当前选中模式的历史
        if (modeSelector.value) {
            loadHistoryForMode(modeSelector.value);
        } else {
            // 如果没有专家了，清空聊天窗口
            clearChatWindow();
            appendMessage({ content: '没有可用的专家。请在设置中添加一个。', role: 'assistant' }, true);
        }
    }
}); 