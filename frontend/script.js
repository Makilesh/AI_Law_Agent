const API_BASE_URL = 'http://localhost:8000';
const WS_BASE_URL = 'ws://localhost:8000';

// Voice chat variables
let voiceWebSocket = null;
let isVoiceActive = false;
let voiceStatusIndicator = null;

// Check server status on load
async function checkServerStatus() {
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (data.status === 'healthy') {
            statusIndicator.classList.add('connected');
            statusText.textContent = 'Connected';
            loadVectorStoreStats();
        } else {
            throw new Error('Server unhealthy');
        }
    } catch (error) {
        statusIndicator.classList.add('disconnected');
        statusText.textContent = 'Disconnected - Check if server is running';
        console.error('Server check failed:', error);
    }
}

// Load vector store statistics
async function loadVectorStoreStats() {
    const statsContent = document.getElementById('statsContent');
    
    try {
        const response = await fetch(`${API_BASE_URL}/vector-store/stats`);
        const data = await response.json();
        
        statsContent.innerHTML = `
            <p><strong>Collection:</strong> ${data.collection_name}</p>
            <p><strong>Total Documents:</strong> ${data.total_documents}</p>
            <p><strong>Total Chunks:</strong> ${data.total_chunks || 'N/A'}</p>
        `;
    } catch (error) {
        statsContent.innerHTML = '<p style="color: #c62828;">Failed to load stats</p>';
        console.error('Stats load failed:', error);
    }
}

// Send chat query
async function sendQuery() {
    const queryInput = document.getElementById('queryInput');
    const language = document.getElementById('language').value;
    const query = queryInput.value.trim();
    
    if (!query) return;
    
    const sendBtn = document.getElementById('sendBtn');
    const sendBtnText = document.getElementById('sendBtnText');
    const sendBtnLoader = document.getElementById('sendBtnLoader');
    
    // Disable input and show loader
    sendBtn.disabled = true;
    sendBtnText.style.display = 'none';
    sendBtnLoader.style.display = 'inline-block';
    queryInput.disabled = true;
    
    // Add user message to chat
    addMessage('user', query);
    queryInput.value = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                language: language
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        addMessage('assistant', data);
        
    } catch (error) {
        console.error('Query failed:', error);
        addMessage('error', 'Failed to get response. Please check if the server is running.');
    } finally {
        // Re-enable input
        sendBtn.disabled = false;
        sendBtnText.style.display = 'inline';
        sendBtnLoader.style.display = 'none';
        queryInput.disabled = false;
        queryInput.focus();
    }
}

// Add message to chat container
function addMessage(type, content) {
    const chatContainer = document.getElementById('chatContainer');
    
    // Remove welcome message if exists
    const welcomeMsg = chatContainer.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    if (type === 'user') {
        messageDiv.textContent = content;
    } else if (type === 'assistant') {
        // Format response text with line breaks
        const responseText = (content.response || content.answer || 'No response').replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = `
            <div class="answer">${responseText}</div>
            <div class="metadata">
                <div><strong>Source:</strong> ${content.source}</div>
                <div><strong>Confidence:</strong> <span class="confidence">${(content.confidence * 100).toFixed(1)}%</span></div>
                <div><strong>Language:</strong> ${content.language}</div>
            </div>
        `;
    } else if (type === 'error') {
        messageDiv.className = 'error-message';
        messageDiv.textContent = content;
    }
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Handle Enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendQuery();
    }
}

// Example query function
function askExample(query) {
    document.getElementById('queryInput').value = query;
    sendQuery();
}

// PDF Upload functionality
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
        uploadPDF(file);
    } else {
        showUploadResult('Please select a valid PDF file', 'error');
    }
}

// Drag and drop for PDF upload
const uploadArea = document.getElementById('uploadArea');

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
        uploadPDF(file);
    } else {
        showUploadResult('Please drop a valid PDF file', 'error');
    }
});

// Upload PDF to server
async function uploadPDF(file) {
    const uploadProgress = document.getElementById('uploadProgress');
    const uploadResult = document.getElementById('uploadResult');
    const progressFill = document.getElementById('progressFill');
    const uploadStatus = document.getElementById('uploadStatus');
    
    // Show progress
    uploadProgress.style.display = 'block';
    uploadResult.style.display = 'none';
    progressFill.style.width = '0%';
    uploadStatus.textContent = 'Uploading...';
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Simulate progress
        progressFill.style.width = '30%';
        
        const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
            method: 'POST',
            body: formData
        });
        
        progressFill.style.width = '70%';
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.status}`);
        }
        
        const data = await response.json();
        progressFill.style.width = '100%';
        uploadStatus.textContent = 'Processing complete!';
        
        setTimeout(() => {
            uploadProgress.style.display = 'none';
            showUploadResult(
                `✅ Successfully uploaded "${data.filename}"<br>
                📄 Pages processed: ${data.pages_processed}<br>
                📦 Chunks created: ${data.chunks_created}`,
                'success'
            );
            loadVectorStoreStats(); // Refresh stats
        }, 500);
        
    } catch (error) {
        console.error('Upload failed:', error);
        uploadProgress.style.display = 'none';
        showUploadResult('❌ Upload failed. Please check if the server is running.', 'error');
    }
}

// Show upload result
function showUploadResult(message, type) {
    const uploadResult = document.getElementById('uploadResult');
    uploadResult.innerHTML = message;
    uploadResult.className = `upload-result ${type}`;
    uploadResult.style.display = 'block';
    
    // Hide after 5 seconds for success
    if (type === 'success') {
        setTimeout(() => {
            uploadResult.style.display = 'none';
        }, 5000);
    }
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    checkServerStatus();
    checkVoiceAvailability();
    
    // Refresh stats every 30 seconds
    setInterval(() => {
        loadVectorStoreStats();
    }, 30000);
});

// ================== VOICE CHAT FUNCTIONALITY ==================

// Check if voice I/O is available
async function checkVoiceAvailability() {
    try {
        const response = await fetch(`${API_BASE_URL}/voice/status`);
        const data = await response.json();
        
        const voiceBtn = document.getElementById('voiceBtn');
        if (data.voice_available) {
            voiceBtn.style.display = 'block';
            voiceBtn.title = 'Voice Chat Available - Click to start';
        } else {
            voiceBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Voice check failed:', error);
        document.getElementById('voiceBtn').style.display = 'none';
    }
}

// Toggle voice chat on/off
function toggleVoiceChat() {
    if (isVoiceActive) {
        stopVoiceChat();
    } else {
        startVoiceChat();
    }
}

// Start voice chat
function startVoiceChat() {
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceBtnIcon = document.getElementById('voiceBtnIcon');
    const voiceStatus = document.getElementById('voiceStatus');
    
    try {
        // Connect WebSocket
        voiceWebSocket = new WebSocket(`${WS_BASE_URL}/ws/voice`);
        
        voiceWebSocket.onopen = () => {
            console.log('Voice WebSocket connected');
            isVoiceActive = true;
            
            // Update UI
            voiceBtn.classList.add('active');
            voiceBtnIcon.textContent = '🔴';
            voiceBtn.title = 'Voice Chat Active - Click to stop';
            voiceStatus.style.display = 'flex';
            updateVoiceStatus('🎤', 'Connected', 'success');
            
            // Show info message
            addVoiceMessage('system', '🎤 Voice chat connected! Speak your legal question...');
        };
        
        voiceWebSocket.onmessage = (event) => {
            handleVoiceMessage(JSON.parse(event.data));
        };
        
        voiceWebSocket.onerror = (error) => {
            console.error('Voice WebSocket error:', error);
            updateVoiceStatus('❌', 'Connection error', 'error');
            stopVoiceChat();
        };
        
        voiceWebSocket.onclose = () => {
            console.log('Voice WebSocket closed');
            if (isVoiceActive) {
                stopVoiceChat();
            }
        };
        
    } catch (error) {
        console.error('Failed to start voice chat:', error);
        alert('Failed to connect to voice service. Please check if the server is running.');
    }
}

// Stop voice chat
function stopVoiceChat() {
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceBtnIcon = document.getElementById('voiceBtnIcon');
    const voiceStatus = document.getElementById('voiceStatus');
    
    if (voiceWebSocket) {
        voiceWebSocket.close();
        voiceWebSocket = null;
    }
    
    isVoiceActive = false;
    
    // Update UI
    voiceBtn.classList.remove('active');
    voiceBtnIcon.textContent = '🎤';
    voiceBtn.title = 'Voice Chat - Click to start';
    voiceStatus.style.display = 'none';
    
    addVoiceMessage('system', '🔴 Voice chat disconnected');
}

// Handle incoming voice messages
function handleVoiceMessage(message) {
    const { type, content, metadata } = message;
    
    switch (type) {
        case 'status':
            handleVoiceStatus(content);
            break;
            
        case 'transcript':
            // Show what user said
            addMessage('user', content);
            updateVoiceStatus('⏳', 'Processing...', 'processing');
            break;
            
        case 'response':
            // Show AI response
            const responseData = {
                response: content,
                confidence: metadata?.confidence || 0.0,
                source: metadata?.source || 'voice',
                language: 'English'
            };
            addMessage('assistant', responseData);
            break;
            
        case 'error':
            updateVoiceStatus('❌', content, 'error');
            addVoiceMessage('error', `Error: ${content}`);
            break;
            
        default:
            console.log('Unknown voice message type:', type);
    }
}

// Handle voice status updates
function handleVoiceStatus(status) {
    switch (status) {
        case 'connected':
            updateVoiceStatus('✅', 'Connected', 'success');
            break;
        case 'listening':
            updateVoiceStatus('🎤', 'Listening...', 'listening');
            break;
        case 'processing':
            updateVoiceStatus('⏳', 'Processing...', 'processing');
            break;
        case 'speaking':
            updateVoiceStatus('🔊', 'Speaking...', 'speaking');
            break;
        case 'ready':
            updateVoiceStatus('✅', 'Ready', 'success');
            break;
    }
}

// Update voice status display
function updateVoiceStatus(icon, text, statusClass) {
    const voiceStatusIcon = document.getElementById('voiceStatusIcon');
    const voiceStatusText = document.getElementById('voiceStatusText');
    const voiceStatus = document.getElementById('voiceStatus');
    
    voiceStatusIcon.textContent = icon;
    voiceStatusText.textContent = text;
    
    // Remove all status classes
    voiceStatus.classList.remove('success', 'error', 'listening', 'processing', 'speaking');
    
    // Add new status class
    if (statusClass) {
        voiceStatus.classList.add(statusClass);
    }
}

// Add voice-specific system message
function addVoiceMessage(type, text) {
    const chatContainer = document.getElementById('chatContainer');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message voice-system-message ${type}`;
    messageDiv.innerHTML = `<em>${text}</em>`;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Send text query via voice WebSocket
function sendVoiceTextQuery(query) {
    if (voiceWebSocket && voiceWebSocket.readyState === WebSocket.OPEN) {
        const language = document.getElementById('language').value;
        voiceWebSocket.send(JSON.stringify({
            type: 'text',
            content: query,
            language: language
        }));
        return true;
    }
    return false;
}
