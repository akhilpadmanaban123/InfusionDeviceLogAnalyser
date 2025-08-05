document.addEventListener('DOMContentLoaded', () => {
    const headerContainer = document.getElementById('header-container');
    const bodyContainer = document.getElementById('body-container');
    const depthViewHeader = document.getElementById('depthViewHeader');

    const urlParams = new URLSearchParams(window.location.search);
    const issueName = urlParams.get('issueName');

    console.log('DOMContentLoaded fired.');
    console.log('headerContainer:', headerContainer);
    console.log('bodyContainer:', bodyContainer);

    if (issueName) {
        depthViewHeader.textContent = `Issue: ${issueName}`;
        fetchAndRenderFullPowerLog(issueName);
    } else {
        depthViewContainer.innerHTML = '<p style="color: red;">No issue name provided.</p>';
    }

    const POWER_LOG_COLUMNS = [
        // Hidden due to confidentiality
    ];

    function parseLogLine(line) {
        const parts = line.split(',');
        const parsed = {};
        if (parts.length > 0) {
            POWER_LOG_COLUMNS.forEach((col, index) => {
                parsed[col] = parts[index] || '';
            });
        }
        return parsed;
    }

    async function fetchAndRenderFullPowerLog(issueName) {
        console.log('fetchAndRenderFullPowerLog called for issue:', issueName);
        try {
            const response = await fetch(`/get_powerlog_file/${issueName}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const powerlogText = await response.text();
            console.log('Powerlog text fetched successfully. Length:', powerlogText.length);
            renderTables(powerlogText);
        } catch (error) {
            depthViewContainer.innerHTML = `<p style="color: red;">Failed to load PowerLog data: ${error.message}</p>`;
            console.error('Error fetching full PowerLog data:', error);
        }
    }

    function renderTables(powerlogText) {
        console.log('renderTables called.');
        const lines = powerlogText.trim().split('\n');
        if (lines.length === 0) {
            bodyContainer.innerHTML = '<p>No data to display.</p>';
            console.log('No lines in powerlogText.');
            return;
        }

        // --- Create a temporary header table to measure natural column widths ---
        const tempHeaderTable = document.createElement('table');
        tempHeaderTable.style.position = 'absolute';
        tempHeaderTable.style.visibility = 'hidden';
        tempHeaderTable.style.width = 'auto'; // Allow natural width
        tempHeaderTable.style.whiteSpace = 'nowrap'; // Prevent text wrapping
        tempHeaderTable.classList.add('live-log-table'); // Apply base table styles

        const tempThead = document.createElement('thead');
        const tempHeaderRow = document.createElement('tr');
        POWER_LOG_COLUMNS.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            tempHeaderRow.appendChild(th);
        });
        tempThead.appendChild(tempHeaderRow);
        tempHeaderTable.appendChild(tempThead);
        document.body.appendChild(tempHeaderTable); // Temporarily add to DOM for measurement

        const headerCells = Array.from(tempHeaderRow.cells);
        const columnWidths = headerCells.map(cell => cell.getBoundingClientRect().width);
        const totalTableWidth = columnWidths.reduce((sum, width) => sum + width, 0);

        console.log('Measured Column Widths:', columnWidths);
        console.log('Calculated Total Table Width:', totalTableWidth);

        document.body.removeChild(tempHeaderTable); // Clean up the temporary table

        // --- Step 2: Create and render the actual header table ---
        const headerTable = document.createElement('table');
        headerTable.classList.add('live-log-table');
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        POWER_LOG_COLUMNS.forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });

        thead.appendChild(headerRow);
        headerTable.appendChild(thead);
        headerContainer.innerHTML = '';
        headerContainer.appendChild(headerTable);
        console.log('Header table appended to headerContainer.');

        // --- Apply measured widths to header table using colgroup ---
        const colgroupHeader = document.createElement('colgroup');
        columnWidths.forEach(width => {
            const col = document.createElement('col');
            col.style.width = `${width}px`;
            colgroupHeader.appendChild(col);
        });
        headerTable.insertBefore(colgroupHeader, thead);
        headerTable.style.width = `${totalTableWidth}px`;
        headerTable.style.tableLayout = 'fixed';
        console.log('Header Table final width (after colgroup and fixed layout):', headerTable.style.width);

        // --- Create and render the body table ---
        const bodyTable = document.createElement('table');
        bodyTable.classList.add('live-log-table');
        const tbody = document.createElement('tbody');
        const virtualContainer = document.createElement('div');
        virtualContainer.id = 'depthViewVirtualContainer';
        tbody.appendChild(virtualContainer);
        bodyTable.appendChild(tbody);
        bodyContainer.innerHTML = '';
        bodyContainer.appendChild(bodyTable);
        console.log('Body table appended to bodyContainer.');

        // --- Apply measured widths to body table using colgroup ---
        const colgroupBody = document.createElement('colgroup');
        columnWidths.forEach(width => {
            const col = document.createElement('col');
            col.style.width = `${width}px`;
            colgroupBody.appendChild(col);
        });
        bodyTable.insertBefore(colgroupBody, tbody);
        bodyTable.style.width = `${totalTableWidth}px`;
        bodyTable.style.tableLayout = 'fixed';
        console.log('Body Table final width (after colgroup and fixed layout):', bodyTable.style.width);

        // --- Synchronize horizontal scrolling ---
        bodyContainer.addEventListener('scroll', () => {
            headerContainer.scrollLeft = bodyContainer.scrollLeft;
        });

        // --- Virtual Scrolling Logic ---
        const rowHeight = 30; // Approximate height of a row
        console.log('Body Container Client Height (before renderVisibleRows):', bodyContainer.clientHeight);
        const containerHeight = bodyContainer.clientHeight;
        const visibleRows = Math.ceil(containerHeight / rowHeight) + 2; // Add a buffer

        // Create a single wrapper for visible rows
        const visibleRowsWrapper = document.createElement('div');
        visibleRowsWrapper.style.position = 'relative';
        visibleRowsWrapper.style.width = '100%';
        virtualContainer.appendChild(visibleRowsWrapper);

        function renderVisibleRows() {
            console.log('Rendering visible rows...');
            const scrollTop = bodyContainer.scrollTop;
            const startIndex = Math.floor(scrollTop / rowHeight);
            const endIndex = Math.min(startIndex + visibleRows, lines.length);

            visibleRowsWrapper.innerHTML = ''; // Clear previous rows
            virtualContainer.style.height = `${lines.length * rowHeight}px`; // Total height for scrollbar
            console.log('Virtual Container Height:', virtualContainer.style.height);

            // Position the wrapper to simulate scrolling
            visibleRowsWrapper.style.transform = `translateY(${startIndex * rowHeight}px)`;

            for (let i = startIndex; i < endIndex; i++) {
                const line = lines[i];
                if (!line) continue;

                const parsedData = parseLogLine(line);
                const row = document.createElement('tr');
                // Rows are no longer absolutely positioned, they are part of the normal flow within visibleRowsWrapper
                row.style.height = `${rowHeight}px`;

                POWER_LOG_COLUMNS.forEach(col => {
                    const cell = row.insertCell();
                    const displayValue = parsedData[col] || '';
                    cell.textContent = displayValue;
                    cell.title = displayValue; // Add tooltip for long content
                });
                visibleRowsWrapper.appendChild(row);
            }
            console.log('Finished rendering visible rows.');
        }

        bodyContainer.addEventListener('scroll', renderVisibleRows);
        window.addEventListener('resize', () => renderTables(powerlogText)); // Re-render on resize

        renderVisibleRows(); // Initial render
    }
});

        bodyContainer.addEventListener('scroll', renderVisibleRows);
        window.addEventListener('resize', () => renderTables(powerlogText)); // Re-render on resize

        renderVisibleRows(); // Initial render
    }
});