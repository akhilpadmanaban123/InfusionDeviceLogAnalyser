import * as liveLogDisplay from './liveLogDisplay.js';

const POWER_LOG_COLUMNS = [
   // removed due to confidentiality
];

function parseLogLine(line) {
    const parts = line.split(',');
    const parsed = {};
    if (parts.length > 0) {
        parsed[POWER_LOG_COLUMNS[0]] = parts[0]; // Timestamp
        for (let i = 1; i < POWER_LOG_COLUMNS.length; i++) {
            parsed[POWER_LOG_COLUMNS[i]] = parts[i] || ''; // Assign value or empty string
        }
    }
    return parsed;
}

document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const fileInput = document.getElementById('file-input');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');

    // New message file input
    const messageFileInput = document.getElementById('message-file-input');

    // Modal elements
    const summaryModal = document.getElementById('summaryModal');
    const closeButton = document.querySelector('.close-button');
    const modalTableBody = document.getElementById('modalTableBody');
    const modalSearchInput = document.getElementById('modalSearchInput');
    const modalFilterBatteryBtn = document.getElementById('modalFilterBattery');
    const modalFilterPowerBtn = document.getElementById('modalFilterPower');
    const modalClearFiltersBtn = document.getElementById('modalClearFilters');
    const modalExportDataBtn = document.getElementById('modalExportData');
    const modalTotalSessions = document.getElementById('modalTotalSessions');
    const modalTotalRuntime = document.getElementById('modalTotalRuntime');
    const modalBatteryUsage = document.getElementById('modalBatteryUsage');
    const modalPowerEvents = document.getElementById('modalPowerEvents');

    // Battery Flow Modal elements
    const batteryFlowModal = document.getElementById('batteryFlowModal');
    const closeBatteryFlowModalBtn = document.getElementById('closeBatteryFlowModal');
    const batteryHealthStatus = document.getElementById('batteryHealthStatus');
    const batteryFlowChartCanvas = document.getElementById('batteryFlowChartCanvas');
    let batteryChartInstance = null;

    // Message Logs Modal elements
    const messageLogsModal = document.getElementById('messageLogsModal');
    const closeMessageLogsModalBtn = document.getElementById('closeMessageLogsModal');
    const messageLogsHeader = document.getElementById('messageLogsHeader');
    const messageLogsContent = document.getElementById('messageLogsContent');

    // Depth View Modal elements
    const depthViewModal = document.getElementById('depthViewModal');
    const closeDepthViewModalBtn = document.getElementById('closeDepthViewModal');
    const depthViewContainer = document.getElementById('depthViewContainer');
    const depthViewBtn = document.getElementById('depthViewBtn');

    // Live Log Modal elements
    const liveLogModal = document.getElementById('liveLogModal');
    const closeLiveLogModalBtn = document.getElementById('closeLiveLogModal');
    const liveLogHeader = document.getElementById('liveLogHeader');
    const liveLogContainer = document.getElementById('liveLogContainer');

    // Sidebar elements
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mainLayout = document.querySelector('.main-layout');

    // Generate a unique session ID for this user session
    const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

    // Confirmation dialog for page refresh
    window.addEventListener('beforeunload', (event) => {
        const confirmationMessage = 'Confirm refreshing the page? You will lose the past interactions and analyses.';
        event.returnValue = confirmationMessage; // Standard for most browsers
        return confirmationMessage; // For some older browsers
    });

    // Toggle sidebar functionality
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        mainLayout.classList.toggle('sidebar-collapsed');
    });

    // Battery Flow Modal Functions
    function openBatteryFlowModal(chunkId, percValues, sohValues, percTimeSeries, voltValues, currValues, tempValues) {
        console.log(`Opening chart for ChunkID: ${chunkId}`);
        console.log("Received percTimeSeries data:", percTimeSeries);
        batteryFlowModal.style.display = 'block';

        // Determine Battery Health Status
        let sohDisplay = 'N/A';
        let sohNumeric = null;
        if (sohValues !== undefined && sohValues !== null) {
            if (Array.isArray(sohValues)) {
                const filteredSohValues = sohValues.map(Number).filter(n => !isNaN(n));
                if (filteredSohValues.length > 0) {
                    sohNumeric = (filteredSohValues.reduce((a, b) => a + b, 0) / filteredSohValues.length);
                    sohDisplay = sohNumeric.toFixed(0);
                }
            } else {
                sohNumeric = Number(sohValues);
                if (!isNaN(sohNumeric)) {
                    sohDisplay = sohNumeric.toFixed(0);
                }
            }
        }

        let healthIcon = '';
        let healthText = '';
        if (sohNumeric !== null) {
            if (sohNumeric === 0) {
                healthIcon = '<span class="battery-health-icon health-critical">❗</span>';
                healthText = `Critical! SOH: ${sohDisplay}%`;
            } else if (sohNumeric < 50) { // Example threshold for 'weak'
                healthIcon = '<span class="battery-health-icon health-weak">⚠️</span>';
                healthText = `Weak. SOH: ${sohDisplay}%`;
            } else {
                healthIcon = '<span class="battery-health-icon health-normal">🔋</span>';
                healthText = `Good. SOH: ${sohDisplay}%`;
            }
        } else {
            healthText = 'SOH: N/A';
        }
        batteryHealthStatus.innerHTML = `${healthIcon} ${healthText}`;
        
        const voltStats = document.getElementById('volt-stats');
        const currStats = document.getElementById('curr-stats');
        const tempStats = document.getElementById('temp-stats');

        const formatStats = (values, unit) => {
            // Ensure values is always an array
            const valuesArray = Array.isArray(values) ? values : [values];

            if (valuesArray.length > 0) {
                const numericValues = valuesArray.map(Number).filter(n => !isNaN(n));
                if (numericValues.length > 0) {
                    let min = Math.min(...numericValues);
                    let max = Math.max(...numericValues);
                    if (unit === 'V') {
                        min = (min / 1000).toFixed(2);
                        max = (max / 1000).toFixed(2);
                    }
                    return `${min}${unit} - ${max}${unit}`;
                }
            }
            return 'N/A';
        };

        voltStats.textContent = formatStats(voltValues, 'V');
        currStats.textContent = formatStats(currValues, 'mA');
        tempStats.textContent = formatStats(tempValues, '°C');

        // --- Robust Chart Rendering Logic ---
        const canvas = document.getElementById('batteryFlowChartCanvas');
        const noChartMessage = document.getElementById('no-chart-message');

        if (batteryChartInstance) {
            batteryChartInstance.destroy();
            batteryChartInstance = null;
        }

        let chartDataPoints = [];
        let chartLabels = [];
        
        try {
            // 1. Prioritize Perc_Time_Series for its timestamp data
            if (Array.isArray(percTimeSeries) && percTimeSeries.length > 0) {
                const validTimeSeries = percTimeSeries.filter(item => item && typeof item.value !== 'undefined' && item.value !== '' && !isNaN(Number(item.value)));
                if (validTimeSeries.length > 0) {
                    chartLabels = validTimeSeries.map(item => new Date(item.time).toLocaleTimeString());
                    chartDataPoints = validTimeSeries.map(item => Number(item.value));
                }
            }

            // 2. Fallback to percValues if time series is not usable
            if (chartDataPoints.length === 0 && percValues) {
                if (Array.isArray(percValues)) {
                    const validPercValues = percValues.filter(val => val !== '' && !isNaN(Number(val)));
                    if (validPercValues.length > 0) {
                        chartDataPoints = validPercValues.map(Number);
                        chartLabels = chartDataPoints.map((_, index) => `Reading ${index + 1}`);
                    }
                } else if (percValues !== '' && !isNaN(Number(percValues))) {
                    const singleValue = Number(percValues);
                    canvas.style.display = 'none';
                    noChartMessage.style.display = 'block';
                    noChartMessage.textContent = `Battery level was constant at ${singleValue}%`;
                    return; 
                }
            }

            // 3. Render the chart if we have data, otherwise show a "no data" message
            if (chartDataPoints.length > 0) {
                canvas.style.display = 'block';
                noChartMessage.style.display = 'none';

                batteryChartInstance = new Chart(canvas, {
                    type: 'line',
                    data: {
                        labels: chartLabels,
                        datasets: [{
                            label: 'Battery Percentage',
                            data: chartDataPoints,
                            borderColor: '#007bff',
                            backgroundColor: 'rgba(0, 123, 255, 0.2)',
                            fill: true,
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: { title: { display: true, text: 'Time', color: '#e0e0e0' }, ticks: { color: '#e0e0e0' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } },
                            y: { title: { display: true, text: 'Percentage', color: '#e0e0e0' }, min: 0, max: 100, ticks: { color: '#e0e0e0' }, grid: { color: 'rgba(255, 255, 255, 0.1)' } }
                        },
                        plugins: {
                            legend: { display: false },
                            tooltip: { callbacks: { label: (context) => `Battery: ${context.raw}%` } }
                        }
                    }
                });
            } else {
                canvas.style.display = 'none';
                noChartMessage.style.display = 'block';
                noChartMessage.textContent = 'No chart data available for this chunk.';
            }
        } catch (error) {
            console.error("A critical error occurred while rendering the chart:", error);
            canvas.style.display = 'none';
            noChartMessage.style.display = 'block';
            noChartMessage.textContent = 'An error occurred while rendering the chart.';
        }
    }

    function closeBatteryFlowModal() {
        console.log("Attempting to close battery flow modal.");
        batteryFlowModal.style.display = 'none';
        if (batteryChartInstance) {
            batteryChartInstance.destroy();
            batteryChartInstance = null;
        }
        batteryHealthStatus.innerHTML = '';
    }

    let state = 'awaiting_powerlog_file'; 
    let uploadedPowerlogFile = null;
    let uploadedMessageFile = null;
    let originalModalData = [];
    let filteredModalData = [];
    let currentIssueName = null;
appendMessage(`👋 Hello! I’m your P&B Sentinel Agent. I can help you analyze PowerLog files in multiple ways:

1. **Upload Files:** Use the 📎 button to upload your PowerLog and message files directly.
2. **Analyze from Path:** Type \`/analyze\` followed by the full path to your log directory (e.g., \`/analyze C:\\\\path\\\\to\\\\your\\\\logs\\\\var\\\\log\\\\\`).
3. **Live Log Stream:** Type \`/livepower\` followed by the pump's IP address to stream logs in real-time (e.g., \`/livepower 10.74.32.65\`).
4. **Live Pump View:** Access a live view of the pump <a href="..." target="_blank" style="color: #FFC107;">Multi-Pump Live View</a>.

🧠 I'm the first version of this agent — built to simplify power and battery logs into developer-friendly viewable format.

Let’s get started!`, 'bot');


    const reportsList = document.getElementById('reports-list');

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            if (state === 'awaiting_powerlog_file') {
                uploadedPowerlogFile = e.target.files[0];
                appendMessage(`Powerlog file selected: ${uploadedPowerlogFile.name}`, 'user');
                appendMessage('Now, please select the message file using the Attach Files button.', 'bot');
                state = 'awaiting_message_file';
            } else if (state === 'awaiting_message_file') {
                uploadedMessageFile = e.target.files[0];
                appendMessage(`Message file selected: ${uploadedMessageFile.name}`, 'user');
                appendMessage('Both files selected. Please enter the issue name.', 'bot');
                state = 'awaiting_issue';
            }
        }
    });
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleUserInput();
        }
    });

    userInput.addEventListener('input', () => {
        if (userInput.value.trim().length > 0) {
            sendBtn.style.visibility = 'visible';
        } else {
            sendBtn.style.visibility = 'hidden';
        }
    });

    // Initial check for send button visibility
    if (userInput.value.trim().length > 0) {
        sendBtn.style.visibility = 'visible';
    } else {
        sendBtn.style.visibility = 'hidden';
    }

    sendBtn.addEventListener('click', handleUserInput);

    function typeMessage(element, htmlContent) {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlContent;
        const nodes = Array.from(tempDiv.childNodes);
        let nodeIndex = 0;
        let charIndex = 0;
        let currentTextNode = null; // To build up text content

        element.innerHTML = ''; // Clear content initially

        const interval = setInterval(() => {
            if (nodeIndex < nodes.length) {
                const currentNode = nodes[nodeIndex];

                if (currentNode.nodeType === Node.TEXT_NODE) {
                    if (!currentTextNode) {
                        currentTextNode = document.createTextNode('');
                        element.appendChild(currentTextNode);
                    }
                    if (charIndex < currentNode.textContent.length) {
                        currentTextNode.nodeValue += currentNode.textContent.charAt(charIndex);
                        charIndex++;
                    } else {
                        // Finished with this text node, move to next
                        nodeIndex++;
                        charIndex = 0;
                        currentTextNode = null; // Reset for next text node
                    }
                } else if (currentNode.nodeType === Node.ELEMENT_NODE) {
                    // If there was an active text node, finalize it
                    currentTextNode = null;
                    // Append entire HTML elements at once
                    element.appendChild(currentNode.cloneNode(true)); // Clone to avoid moving from tempDiv
                    nodeIndex++;
                    charIndex = 0; // Reset for next node
                }
                chatBox.scrollTop = chatBox.scrollHeight;
            } else {
                clearInterval(interval);
            }
        }, 5); // Adjust typing speed here less means more faster....
    }

    function appendMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('chat-message', `${sender}-message`);
        const p = document.createElement('p');
        messageDiv.appendChild(p);
        chatBox.appendChild(messageDiv);

        // Basic Markdown to HTML conversion
        let html = text.replace(/\*\*([^\*]+)\*\*/g, '<strong>$1</strong>'); // Bold
        html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>'); // Italics
        html = html.replace(/\n/g, '<br>'); // Newlines

        if (sender === 'bot') {
            typeMessage(p, html);
        }
        else {
            p.innerHTML = html;
        }

        chatBox.scrollTop = chatBox.scrollTop;
    }
    // text during thinking or inner functioning.
   function appendLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-message', 'bot-message', 'loading-message');
    messageDiv.innerHTML = `<p>Thinking<span class="loading-dots">
            <span>.</span><span>.</span><span>.</span>
        </span></p>`;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return messageDiv;
}


    function addReportToSidebar(issueName) {
        const listItem = document.createElement('li');
        const link = document.createElement('a');
        link.href = "#";
        link.innerHTML = `<span class="icon">📄</span> ${issueName}`;
        link.onclick = (e) => {
            e.preventDefault();
            openSummaryModal(issueName);
        };
        listItem.appendChild(link);
        reportsList.prepend(listItem);
    }

    

    function handlePowerlogFile(file) {
        uploadedPowerlogFile = file;
        appendMessage(`Powerlog file selected: ${uploadedPowerlogFile.name}`, 'user');
        appendMessage('Now, please upload the corresponding message file using the 📎 Attach Files button.', 'bot');
        state = 'awaiting_message_file';
    }

    function handleMessageFile(file) {
        uploadedMessageFile = file;
        appendMessage(`Message file selected: ${uploadedMessageFile.name}`, 'user');
        appendMessage('Both files selected. Now what should i name the issue? Please enter the issue name.', 'bot');
        state = 'awaiting_issue';
    }

    async function uploadFilesAndAnalyze(powerlogFile, messageFile, issueName, loadingMessage) {
        const formData = new FormData();
        formData.append('powerlogFile', powerlogFile);
        if (messageFile) {
            formData.append('messageFile', messageFile);
        }
        formData.append('issueName', issueName);

        try {
            const response = await fetch('http://127.0.0.1:5000/upload_and_analyze....', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            if (loadingMessage) loadingMessage.remove();
            if (response.ok) {
                appendMessage('Analysis complete! You can view the summary by clicking the report in the sidebar :)', 'bot');
                addReportToSidebar(result.issue_name);
            } else {
                appendMessage(`Error: ${result.error}`, 'bot');
                if (result.details) appendMessage(result.details, 'bot');
            }
        } catch (error) {
            appendMessage('An unexpected error occurred. Please check the console.', 'bot');
            console.error('Error:', error);
        }
        state = 'awaiting_powerlog_file';
        uploadedPowerlogFile = null;
        uploadedMessageFile = null;
    }

    async function sendChatQuery(query, loadingMessage) {
        try {
            const response = await fetch('http://127.0.0.1:5000/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, session_id: sessionId })
            });
            const result = await response.json();
            if (loadingMessage) loadingMessage.remove();

            if (response.ok) {
                if (result.action === 'open_live_log') {
                    openLiveLogModal(result.pump_ip);
                } else if (result.response) {
                    appendMessage(result.response, 'bot');
                    if (result.report_ready && result.issue_name) {
                        addReportToSidebar(result.issue_name);
                    }
                } else if (result.error) {
                    appendMessage(`Error: ${result.error}`, 'bot');
                } else {
                    appendMessage(result, 'bot');
                }
            } else {
                appendMessage(`Error: ${result.error}`, 'bot');
                if (result.details) appendMessage(result.details, 'bot');
            }
        } catch (error) {
            if (loadingMessage) loadingMessage.remove();
            appendMessage('An unexpected error occurred while chatting. Please check the console.', 'bot');
            console.error('Chat error:', error);
        }
    }

    function openLiveLogModal(pumpIp) {
        liveLogModal.style.display = 'block';
        liveLogHeader.textContent = `Streaming logs from ${pumpIp}`;
        liveLogDisplay.initLiveLogDisplay(pumpIp);
    }

    function closeLiveLogModal() {
        liveLogDisplay.closeLiveLogDisplay();
    }

    function handleUserInput() {
        const userText = userInput.value.trim();
        if (userText) {
            appendMessage(userText, 'user');
            userInput.value = '';
            sendBtn.style.visibility = 'hidden'; // Hide send button after sending
            if (state === 'awaiting_issue') {
                const issueName = userText;
                const loadingMessage = appendLoadingMessage();
                uploadFilesAndAnalyze(uploadedPowerlogFile, uploadedMessageFile, issueName, loadingMessage);
                state = 'analysis_inprogress';
            } else {
                const loadingMessage = appendLoadingMessage();
                sendChatQuery(userText, loadingMessage);
            }
        }
    }

    function openSummaryModal(issueName) {
        currentIssueName = issueName;
        summaryModal.style.display = 'block';
        fetchCSVDataForModal(issueName);
    }

    function closeSummaryModal() {
        summaryModal.style.display = 'none';
        modalTableBody.innerHTML = '';
        modalSearchInput.value = '';
        modalTotalSessions.textContent = '0';
        modalTotalRuntime.textContent = '0';
        modalBatteryUsage.textContent = '0%';
        modalPowerEvents.textContent = '0';
        originalModalData = [];
        filteredModalData = [];
        currentIssueName = null;
    }

    closeButton.addEventListener('click', closeSummaryModal);

    window.addEventListener('click', (event) => {
        if (event.target == summaryModal) closeSummaryModal();
        if (event.target == batteryFlowModal) closeBatteryFlowModal();
        if (event.target == messageLogsModal) closeMessageLogsModal();
        if (event.target == liveLogModal) closeLiveLogModal();
    });

    closeBatteryFlowModalBtn.addEventListener('click', () => {
        console.log("Close button clicked!");
        closeBatteryFlowModal();
    });

    closeMessageLogsModalBtn.addEventListener('click', () => {
        closeMessageLogsModal();
    });

    closeLiveLogModalBtn.addEventListener('click', () => {
        closeLiveLogModal();
    });

    depthViewBtn.addEventListener('click', () => {
        window.open(`/depth_view?issueName=${currentIssueName}`, '_blank');
    });

    closeDepthViewModalBtn.addEventListener('click', () => {
        closeDepthViewModal();
    });

    function parseCSVForModal(csvString) {
        const lines = csvString.trim().split('\n');
        if (lines.length <= 1) return [];
        const headers = lines[0].split(',').map(h => h.trim());
        const data = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim());
            const row = {};
            headers.forEach((header, index) => {
                row[header] = values[index];
            });
            data.push(row);
        }
        return data;
    }

    function renderModalTable(data) {
        modalTableBody.innerHTML = '';
        if (data.length === 0) {
            modalTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center;">No data to display.</td></tr>`;
            return;
        }

        let previousRowEndTime = null;
        let previousRowEndDate = null;

        data.forEach((row, index) => {
            const tr = document.createElement('tr');
            const startDate = new Date(row.StartDate);
            const endDate = new Date(row.EndDate);
            const formatOrdinalDate = (date) => {
                const day = date.getDate();
                const month = date.toLocaleString('en-US', { month: 'long' });
                const year = date.getFullYear();
                const s = ["th", "st", "nd", "rd"];
                const v = day % 100;
                const ordinal = s[(v - 20) % 10] || s[v] || s[0];
                return `${day}${ordinal} ${month} ${year}`;
            };

            let logStartDate = row.StartDate;
            let logStartTime = row.StartTime;

            // For subsequent rows, set the log start time to the previous row's end time
            if (index > 0 && previousRowEndTime && previousRowEndDate) {
                logStartDate = previousRowEndDate;
                logStartTime = previousRowEndTime;
            }

            tr.innerHTML = `
                <td class="date-time">${formatOrdinalDate(startDate)}</td>
                <td class="date-time">${row.StartTime}</td>
                <td class="date-time">${formatOrdinalDate(endDate)}</td>
                <td class="date-time">${row.EndTime}</td>
                <td><div class="duration">${row.TotalTime}</div></td>
                <td><div class="status-badge ${row.BattPres === 'No Battery' ? 'battery-status-off' : 'battery-status'}">${row.BattPres}</div></td>
                <td><div class="status-badge ${row.PowerSrc === 'AC' ? 'power-ac' : 'power-no-ac'}">${row.PowerSrc}</div></td>
                <td><div class="soc-display" data-chunk-id="${row.ChunkID}">Loading...</div><button class="chart-button" data-chunk-id="${row.ChunkID}" data-issue-name="${currentIssueName}">📊 Chart</button></td>
                <td><button class="view-logs-button" data-start-date="${logStartDate}" data-start-time="${logStartTime}" data-end-date="${row.EndDate}" data-end-time="${row.EndTime}" data-issue-name="${currentIssueName}">📄 View Logs</button></td>
            `;
            modalTableBody.appendChild(tr);
            const chartButton = tr.querySelector(`.chart-button[data-chunk-id="${row.ChunkID}"]`);
            if (chartButton) {
                chartButton.addEventListener('click', async () => {
                    const response = await fetch(`http://127.0.0.1:5000/get_chunk_soc/${currentIssueName}/${encodeURIComponent(row.ChunkID)}`);
                    if (response.ok) {
                        const data = await response.json();
                        openBatteryFlowModal();//updated due to condidentiality)    
                    else {
                        console.error('Failed to fetch data for chart:', await response.text());
                    }
                });
            }
            const viewLogsButton = tr.querySelector(`.view-logs-button`);
            if (viewLogsButton) {
                viewLogsButton.addEventListener('click', () => {
                    const startDate = viewLogsButton.dataset.startDate;
                    const startTime = viewLogsButton.dataset.startTime;
                    const endDate = viewLogsButton.dataset.endDate;
                    const endTime = viewLogsButton.dataset.endTime;
                    const issueName = viewLogsButton.dataset.issueName;
                    openMessageLogsModal(issueName, startDate, startTime, endDate, endTime);
                });
            }
            fetchAndDisplaySOC(row.ChunkID, currentIssueName);

            // Update previousRowEndTime for the next iteration
            previousRowEndTime = row.EndTime;
            previousRowEndDate = row.EndDate;
        });
    }

    async function openMessageLogsModal(issueName, startDate, startTime, endDate, endTime) {
        messageLogsModal.style.display = 'block';
        const start = new Date(`${startDate} ${startTime}`);
        const end = new Date(`${endDate} ${endTime}`);
        const options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
        messageLogsHeader.innerHTML = `Logs from <strong>${start.toLocaleString('en-US', options)}</strong> to <strong>${end.toLocaleString('en-US', options)}</strong>`;
        messageLogsContent.textContent = 'Loading logs...';

        const startDateTime = `${startDate} ${startTime}`;
        const endDateTime = `${endDate} ${endTime}`;

        try {
            const response = await fetch(`http://127.0.0.1:5000/get_message_logs/${issueName}?startTime=${encodeURIComponent(startDateTime)}&endTime=${encodeURIComponent(endDateTime)}`);
            if (response.ok) {
                const data = await response.json();
                if (data.logs && data.logs.length > 0) {
                    messageLogsContent.textContent = data.logs.join('\n');
                } else {
                    messageLogsContent.textContent = 'No message logs found for this period.';
                }
            } else {
                messageLogsContent.textContent = `Error loading logs: ${response.statusText}`;
                console.error('Error fetching message logs:', await response.text());
            }
        } catch (error) {
            messageLogsContent.textContent = 'An error occurred while fetching logs.';
            console.error('Fetch error for message logs:', error);
        }
    }

    function closeMessageLogsModal() {
        messageLogsModal.style.display = 'none';
        messageLogsContent.textContent = '';
        messageLogsHeader.textContent = '';
    }

    function openDepthViewModal(issueName) {
        depthViewModal.style.display = 'block';
        depthViewContainer.innerHTML = 'Loading...';
        fetchAndRenderFullPowerLog(issueName);
    }

    function closeDepthViewModal() {
        depthViewModal.style.display = 'none';
        depthViewContainer.innerHTML = '';
    }

    async function fetchAndRenderFullPowerLog(issueName) {
        try {
            const response = await fetch(`http://127.0.0.1:5000/get_powerlog_file/${issueName}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const powerlogText = await response.text();
            renderFullPowerLogTable(powerlogText);
        } catch (error) {
            depthViewContainer.innerHTML = `<p style="color: red;">Failed to load PowerLog data: ${error.message}</p>`;
            console.error('Error fetching full PowerLog data:', error);
        }
    }

    function renderFullPowerLogTable(powerlogText) {
        const lines = powerlogText.trim().split('\n');
        if (lines.length === 0) {
            depthViewContainer.innerHTML = '<p>No data to display.</p>';
            return;
        }

        const table = document.createElement('table');
        table.classList.add('live-log-table');

        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        POWER_LOG_COLUMNS.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        table.appendChild(tbody);

        depthViewContainer.innerHTML = '';
        depthViewContainer.appendChild(table);

        const virtualContainer = document.createElement('div');
        virtualContainer.id = 'depthViewVirtualContainer';
        tbody.appendChild(virtualContainer);

        const rowHeight = 30; // Approximate height of a row
        const containerHeight = depthViewContainer.clientHeight;
        const visibleRows = Math.ceil(containerHeight / rowHeight);

        let startIndex = 0;

        function renderVisibleRows() {
            virtualContainer.innerHTML = '';
            const endIndex = Math.min(startIndex + visibleRows, lines.length);
            virtualContainer.style.height = `${lines.length * rowHeight}px`;

            for (let i = startIndex; i < endIndex; i++) {
                const line = lines[i];
                const parsedData = parseLogLine(line);
                const row = document.createElement('tr');
                row.style.position = 'absolute';
                row.style.top = `${i * rowHeight}px`;
                row.style.width = '100%';

                POWER_LOG_COLUMNS.forEach(col => {
                    const cell = row.insertCell();
                    let displayValue = parsedData[col];

                    if (col === "ExtTS") {
                        const extTs = parseFloat(displayValue);
                        if (!isNaN(extTs) && (extTs < -10 || extTs > 75)) {
                            cell.innerHTML = `${displayValue} <span style="color: red; font-weight: bold;"> ⚠️</span>`;
                        } else {
                            cell.textContent = displayValue;
                        }
                    } else {
                        cell.textContent = displayValue;
                    }
                });
                virtualContainer.appendChild(row);
            }
        }

        depthViewContainer.addEventListener('scroll', () => {
            startIndex = Math.floor(depthViewContainer.scrollTop / rowHeight);
            renderVisibleRows();
        });

        renderVisibleRows();
    }

    async function fetchAndDisplaySOC(chunkId, issueName) {
        const socDisplayElement = document.querySelector(`.soc-display[data-chunk-id="${chunkId}"]`);
        if (!socDisplayElement) return;
        try {
            const response = await fetch(`http://127.0.0.1:5000/get_chunk_soc/${issueName}/${encodeURIComponent(chunkId)}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            const rawPercValues = data.perc_values;
            const rawSohValues = data.soh_values;
            let percValues = [];
            if (Array.isArray(rawPercValues)) {
                percValues = rawPercValues;
            } else if (rawPercValues !== undefined && rawPercValues !== null) {
                percValues = [rawPercValues];
            }
            let sohValues = [];
            if (Array.isArray(rawSohValues)) {
                sohValues = rawSohValues;
            } else if (rawSohValues !== undefined && rawSohValues !== null) {
                sohValues = [rawSohValues];
            }
            if (percValues.length === 0) {
                socDisplayElement.innerHTML = 'N/A';
                return;
            }
            const numericPercValues = percValues.map(Number).filter(n => !isNaN(n));
            if (numericPercValues.length === 0) {
                socDisplayElement.innerHTML = 'N/A';
                return;
            }
            const averagePerc = (numericPercValues.reduce((a, b) => a + b, 0) / numericPercValues.length).toFixed(0);
            let sohDisplay = 'N/A';
            if (sohValues.length > 0) {
                const numericSohValues = sohValues.map(Number).filter(n => !isNaN(n));
                if (numericSohValues.length > 0) {
                    const averageSoh = (numericSohValues.reduce((a, b) => a + b, 0) / numericSohValues.length).toFixed(0);
                    sohDisplay = averageSoh;
                }
            }
            let trendIcon = '';
            if (numericPercValues.length > 1) {
                const first = numericPercValues[0];
                const last = numericPercValues[numericPercValues.length - 1];
                if (last > first) trendIcon = '<span class="trend-icon trend-up">▲</span>';
                else if (last < first) trendIcon = '<span class="trend-icon trend-down">▼</span>';
                else trendIcon = '<span class="trend-icon trend-constant">▬</span>';
            } else {
                trendIcon = '<span class="trend-icon trend-constant">▬</span>';
            }
            socDisplayElement.innerHTML = `${averagePerc}% ${trendIcon} / ${sohDisplay}%`;
        } catch (error) {
            console.error(`Error fetching SOC for chunk ${chunkId}:`, error);
            socDisplayElement.innerHTML = 'Error';
        }
    }

    async function fetchCSVDataForModal(issueName) {
        try {
            const response = await fetch(`http://127.0.0.1:5000/get_summary_csv/${issueName}`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const csvText = await response.text();
            originalModalData = parseCSVForModal(csvText);
            filteredModalData = [...originalModalData];
            renderModalTable(filteredModalData);
            updateModalStats(originalModalData);
        } catch (error) {
            console.error('Error fetching CSV data for modal:', error);
            modalTableBody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: red;">Failed to load data. Please ensure the analysis was successful and the server is running.</td></tr>`;
        }
    }

    function updateModalStats(data) {
        modalTotalSessions.textContent = data.length;
        let totalSeconds = 0;
        let batteryUsageCount = 0;
        let powerEventsCount = 0;
        data.forEach(row => {
            const durationParts = row.TotalTime.split(':').map(Number);
            if (durationParts.length === 3) {
                totalSeconds += durationParts[0] * 3600 + durationParts[1] * 60 + durationParts[2];
            }
            if (row.BattPres === 'Battery') batteryUsageCount++;
            if (row.PowerSrc === 'AC' || row.PowerSrc === 'No AC') powerEventsCount++;
        });
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        modalTotalRuntime.textContent = `${hours}h ${minutes}m ${seconds}s`;
        modalBatteryUsage.textContent = `${((batteryUsageCount / data.length) * 100 || 0).toFixed(0)}%`;
        modalPowerEvents.textContent = powerEventsCount;
    }

    modalFilterBatteryBtn.addEventListener('click', () => {
        filteredModalData = originalModalData.filter(row => row.BattPres === 'Battery');
        renderModalTable(filteredModalData);
    });

    modalFilterPowerBtn.addEventListener('click', () => {
        filteredModalData = originalModalData.filter(row => row.PowerSrc === 'No AC');
        renderModalTable(filteredModalData);
    });

    modalClearFiltersBtn.addEventListener('click', () => {
        filteredModalData = [...originalModalData];
        renderModalTable(filteredModalData);
        modalSearchInput.value = '';
    });

    modalExportDataBtn.addEventListener('click', () => {
        const csv = [
            Object.keys(filteredModalData[0]).join(','),
            ...filteredModalData.map(row => Object.values(row).join(','))
        ].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `powerlog_summary_${currentIssueName || 'data'}.csv`;
        a.click();
        window.URL.revokeObjectURL(url);
    });

    modalSearchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        filteredModalData = originalModalData.filter(row => 
            Object.values(row).some(value => 
                String(value).toLowerCase().includes(searchTerm)
            )
        );
        renderModalTable(filteredModalData);
    });
});