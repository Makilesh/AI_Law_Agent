const API_BASE_URL = 'http://localhost:8000';

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
    
    // Refresh stats every 30 seconds
    setInterval(() => {
        loadVectorStoreStats();
    }, 30000);
});
