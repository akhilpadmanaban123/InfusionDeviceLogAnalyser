
// frontend/liveLogDisplay.js

// Define the columns based on RAG_DATA/powerlogInfo.txt and backend/chunker/powerchunk.py
// This list must match the order of data in each log line
const POWER_LOG_COLUMNS = [
    //confidential info removed
];

// Define which columns are bitfields and need special decoding
// This would ideally come from the backend, but for frontend display, we'll hardcode for now
const BITFIELD_COLUMNS = [
    "BattStatus", "SafetyAlert", "SafetyStatus", "PFAlert", "PFStatus",
    "OperationalStatus", "ChargingStatus", "GaugingStatus"
];

let parameterDefinitions = {};
let bitfieldDefinitions = {};

let liveLogEventSource = null;
let liveLogContainer = null;
let liveLogHeader = null;
let liveLogTableBody = null;

export async function initLiveLogDisplay(pumpIp) {
    // Fetch definitions from backend
    try {
        const response = await fetch('http://127.0.0.1:5000/get_power_log_definitions');
        if (response.ok) {
            const data = await response.json();
            parameterDefinitions = data.parameter_definitions;
            bitfieldDefinitions = data.bitfield_definitions;
        } else {
            console.error('Failed to fetch power log definitions:', await response.text());
        }
    } catch (error) {
        console.error('Error fetching power log definitions:', error);
    }
    const liveLogModal = document.getElementById('liveLogModal');
    liveLogHeader = document.getElementById('liveLogHeader');
    liveLogContainer = document.getElementById('liveLogContainer');
    liveLogTableBody = document.getElementById('liveLogTableBody'); // Assuming a tbody with this ID

    liveLogModal.style.display = 'block';
    liveLogHeader.textContent = `Streaming logs from ${pumpIp}`;
    liveLogContainer.innerHTML = ''; // Clear previous content

    // Create table header
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

    liveLogTableBody = document.createElement('tbody'); // Create tbody here
    liveLogTableBody.id = 'liveLogTableBody'; // Assign ID
    table.appendChild(liveLogTableBody);
    liveLogContainer.appendChild(table);

    liveLogEventSource = new EventSource(`http://127.0.0.1:5000/live_power_log/${pumpIp}`);

    liveLogEventSource.onmessage = function(event) {
        const rawLogLine = event.data;
        const parsedData = parseLogLine(rawLogLine);
        addLogEntryToTable(parsedData);
    };

    liveLogEventSource.onerror = function(event) {
        console.error("EventSource failed:", event);
        const errorMsg = document.createElement('div');
        errorMsg.textContent = "Connection to the log stream failed. Please ensure the pump is reachable and the service is running correctly.";
        errorMsg.style.color = 'red';
        liveLogContainer.appendChild(errorMsg);
        liveLogEventSource.close();
    };
}

export function closeLiveLogDisplay() {
    if (liveLogEventSource) {
        liveLogEventSource.close();
        liveLogEventSource = null;
    }
    document.getElementById('liveLogModal').style.display = 'none';
    liveLogContainer.innerHTML = ''; // Clean up table
}

function parseLogLine(line) {
    const parts = line.split(',');
    const parsed = {};
    // Assuming the first part is Timestamp, and the rest map to COLUMNS
    // Adjusting for Timestamp being the first column in POWER_LOG_COLUMNS
    if (parts.length > 0) {
        parsed[POWER_LOG_COLUMNS[0]] = parts[0]; // Timestamp
        for (let i = 1; i < POWER_LOG_COLUMNS.length; i++) {
            parsed[POWER_LOG_COLUMNS[i]] = parts[i] || ''; // Assign value or empty string
        }
    }
    return parsed;
}

function addLogEntryToTable(data) {
    const row = liveLogTableBody.insertRow(0); // Insert at the top for newest first

    POWER_LOG_COLUMNS.forEach(col => {
        const cell = row.insertCell();
        let displayValue = data[col];

        // Basic styling/interpretation for some key parameters
        if (col === "Perc") {
            const perc = parseFloat(displayValue);
            if (!isNaN(perc)) {
                cell.style.fontWeight = 'bold';
                if (perc < 20) cell.style.color = 'red';
                else if (perc < 50) cell.style.color = 'orange';
                else cell.style.color = 'green';
                displayValue += '%';
            }
        } else if (col === "SOH") {
            const soh = parseFloat(displayValue);
            if (!isNaN(soh)) {
                cell.style.fontWeight = 'bold';
                if (soh < 80) cell.style.color = 'red';
                else cell.style.color = 'green';
                displayValue += '%';
            }
        } else if (col === "Temp") {
            const temp = parseFloat(displayValue);
            if (!isNaN(temp)) {
                if (temp > 45 || temp < 0) cell.style.color = 'red';
                else if (temp > 35 || temp < 10) cell.style.color = 'orange';
                displayValue += '°C';
            }
        } else if (col === "Volt") {
            const volt = parseFloat(displayValue);
            if (!isNaN(volt)) {
                displayValue = (volt / 1000).toFixed(2) + 'V'; // Convert mV to V
            }
        }
 else if (col === "Curr") {
            const curr = parseFloat(displayValue);
            if (!isNaN(curr)) {
                displayValue += 'mA';
            }
        }
 else if (col === "ExtTS") {
            const extTs = parseFloat(displayValue);
            if (!isNaN(extTs) && (extTs < -10 || extTs > 75)) {
                cell.innerHTML = `${displayValue} <span style="color: red; font-weight: bold;"> ⚠️</span>`;
                return; // Skip the generic cell.textContent assignment
            }
        }
 else if (BITFIELD_COLUMNS.includes(col)) {
            // For bitfields, decode and display
            if (displayValue) {
                const decoded = decodeBitfield(displayValue, bitfieldDefinitions[col]);
                cell.title = `Raw: ${displayValue}\nDecoded: ${decoded.join(', ')}`;
                displayValue = decoded.join(', ');
            }
        } else if (col === "BattPresent" || col === "PowerSrc") {
            if (displayValue === "No Battery" || displayValue === "No AC") {
                cell.style.backgroundColor = '#ffcccc'; // Light red background
                cell.style.color = 'black';
                cell.style.fontWeight = 'bold';
            } else if (displayValue === "Battery" || displayValue === "AC") {
                cell.style.backgroundColor = '#ccffcc'; // Light green background
                cell.style.color = 'black';
                cell.style.fontWeight = 'bold';
            }
        }

        cell.textContent = displayValue;
    });

    // Limit the number of rows in the table
    const maxRows = 10; // Display last 10 log entries
    while (liveLogTableBody.rows.length > maxRows) {
        liveLogTableBody.deleteRow(liveLogTableBody.rows.length - 1); // Remove oldest row
    }
}

function decodeBitfield(hexValue, bitfieldDef) {
    const intValue = parseInt(hexValue, 16);
    const decodedMeanings = [];
    if (bitfieldDef) {
        for (const bit in bitfieldDef) {
            const bitNum = parseInt(bit);
            if (!isNaN(bitNum) && (intValue & (1 << bitNum))) {
                decodedMeanings.push(bitfieldDef[bit]);
            }
        }
    }
    return decodedMeanings.length > 0 ? decodedMeanings : [`0x${hexValue} (Unknown)`];
}
