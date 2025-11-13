// Use relative path - nginx will route /api/crawler/ to the API service
const API_URL = '/api/crawler';

let groupingMode = 'provider-query'; // or 'query-provider'
let displayMode = 'table'; // or 'cards'
let dateFilterDays = null; // null = no filter, 7/14/30 = days

// Check authentication on page load
async function checkAuth() {
  try {
    const url = `${API_URL}/auth/check`;
    console.log('Checking auth at URL:', url);
    const response = await fetch(url, {
      credentials: 'include'
    });
    
    console.log('Auth check response status:', response.status);
    console.log('Auth check response headers:', response.headers.get('content-type'));
    const responseText = await response.text();
    console.log('Auth check raw response:', responseText);
    
    const data = JSON.parse(responseText);
    console.log('Auth check parsed data:', data);
    
    if (!data.authenticated) {
      console.log('Not authenticated, redirecting to login');
      window.location.href = '/login.html';
      return false;
    }
    
    // Update UI with user info
    const userEmail = data.email;
    const userEmailElement = document.getElementById('userEmail');
    if (userEmailElement) {
      userEmailElement.textContent = userEmail;
    }
    console.log('Authenticated as:', userEmail);
    return true;
  } catch (error) {
    console.error('Auth check failed:', error);
    window.location.href = '/login.html';
    return false;
  }
}

// Run auth check immediately
checkAuth();

async function loadJobs() {
  const container = document.getElementById("jobs");
  
  try {
    // Build URL with optional date filter
    let url = `${API_URL}/jobs?limit=500`;
    if (dateFilterDays !== null) {
      url += `&days=${dateFilterDays}`;
    }
    
    const res = await fetch(url, {
      credentials: 'include'
    });
    
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    
    const jobs = await res.json();
    container.innerHTML = "";
    
    // Update summary at the top
    const summaryDiv = document.getElementById('jobsSummary');
    if (jobs.length === 0) {
      summaryDiv.style.display = 'none';
      container.innerHTML = '<p style="color: white; background: rgba(255,255,255,0.2); padding: 2rem; border-radius: 12px;">Keine Jobs gefunden. Klicken Sie auf "Crawler starten" um Jobs zu sammeln.</p>';
      return;
    }
    
    // Show and update summary
    const uniqueSources = new Set(jobs.map(j => j.source)).size;
    summaryDiv.style.display = 'block';
    summaryDiv.querySelector('p').innerHTML = `<b>${jobs.length}</b> Jobs gefunden aus <b>${uniqueSources}</b> Quellen`;

    // Display based on display mode
    if (displayMode === 'table') {
      displayAsTable(jobs, container);
    } else {
      // Display based on grouping mode
      if (groupingMode === 'provider-query') {
        displayGroupedByProviderThenQuery(jobs, container);
      } else {
        displayGroupedByQueryThenProvider(jobs, container);
      }
    }
    
  } catch (error) {
    console.error('Error loading jobs:', error);
    container.innerHTML = `
      <div style="color: #721c24; padding: 2rem; background: #f8d7da; border-radius: 12px; border: 1px solid #f5c6cb;">
        <h3 style="margin-top: 0;">Fehler beim Laden der Jobs</h3>
        <p>Stellen Sie sicher, dass die API läuft: <code>docker compose ps</code></p>
        <p>Fehler: ${error.message}</p>
      </div>
    `;
  }
}

// Toggle processed status
async function toggleProcessed(jobId, checkbox) {
  const processed = checkbox.checked;
  
  try {
    const response = await fetch(`${API_URL}/jobs/${jobId}/processed?processed=${processed}`, {
      method: 'PATCH',
      credentials: 'include'
    });
    
    const data = await response.json();
    
    if (data.status === 'error') {
      console.error('Error updating processed status:', data.error);
      checkbox.checked = !processed;
      return;
    }
    
    // Visual feedback
    const jobElement = checkbox.closest('.job') || checkbox.closest('tr');
    if (jobElement) {
      if (processed) {
        jobElement.style.opacity = '0.6';
        if (jobElement.classList.contains('job')) {
          jobElement.style.background = '#f0fdf4';
        }
      } else {
        jobElement.style.opacity = '1';
        if (jobElement.classList.contains('job')) {
          jobElement.style.background = 'white';
        }
      }
    }
  } catch (error) {
    console.error('Error:', error);
    checkbox.checked = !processed;
  }
}

function displayGroupedByProviderThenQuery(jobs, container) {
  // Group by source, then by query
  const grouped = {};
  
  jobs.forEach(job => {
    const source = job.source;
    const query = getJobQuery(job.title);
    
    if (!grouped[source]) {
      grouped[source] = {};
    }
    if (!grouped[source][query]) {
      grouped[source][query] = [];
    }
    grouped[source][query].push(job);
  });
  
  // Display: Provider > Query > Jobs
  Object.keys(grouped).sort().forEach(source => {
    const queries = grouped[source];
    const totalJobs = Object.values(queries).flat().length;
    
    // Provider header (master group)
    const providerHeader = document.createElement("div");
    providerHeader.style.cssText = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.15);";
    providerHeader.innerHTML = `<h2 style="margin: 0; color: white; font-size: 1.75rem;">${getSourceIcon(source)} ${getSourceName(source)} <span style="opacity: 0.8; font-size: 1.2rem;">(${totalJobs})</span></h2>`;
    container.appendChild(providerHeader);
    
    // Query subgroups
    Object.keys(queries).sort().forEach(query => {
      const queryJobs = queries[query];
      
      // Query header (detail group)
      const queryHeader = document.createElement("div");
      queryHeader.style.cssText = "background: white; border-radius: 10px; padding: 0.75rem 1.25rem; margin: 0.5rem 0 0.75rem 1.5rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08); border-left: 4px solid #667eea;";
      queryHeader.innerHTML = `<h3 style="margin: 0; color: #667eea; font-size: 1.2rem;">${getQueryIcon(query)} ${getQueryName(query)} <span style="color: #999; font-size: 0.9rem;">(${queryJobs.length})</span></h3>`;
      container.appendChild(queryHeader);
      
      // Jobs
      queryJobs.forEach(job => {
        const div = document.createElement("div");
        div.className = "job";
        div.style.marginLeft = "1.5rem";
        div.innerHTML = `
          <div style="display: flex; align-items: start; gap: 1rem;">
            <input type="checkbox" 
                   ${job.processed ? 'checked' : ''} 
                   onchange="toggleProcessed(${job.id}, this)"
                   style="margin-top: 0.5rem; width: 18px; height: 18px; cursor: pointer; flex-shrink: 0;">
            <div style="flex: 1;">
              <h3><a href="${job.link}" target="_blank">${job.title}</a></h3>
              <p><b>${job.company || "Unbekannt"}</b> – ${job.location || "n/a"}</p>
              <small>${job.posted}</small>
            </div>
          </div>
        `;
        if (job.processed) {
          div.style.opacity = '0.6';
          div.style.background = '#f0fdf4';
        }
        container.appendChild(div);
      });
    });
  });
}

function displayGroupedByQueryThenProvider(jobs, container) {
  // Group by query, then by source
  const grouped = {};
  
  jobs.forEach(job => {
    const query = getJobQuery(job.title);
    const source = job.source;
    
    if (!grouped[query]) {
      grouped[query] = {};
    }
    if (!grouped[query][source]) {
      grouped[query][source] = [];
    }
    grouped[query][source].push(job);
  });
  
  // Display: Query > Provider > Jobs
  Object.keys(grouped).sort().forEach(query => {
    const providers = grouped[query];
    const totalJobs = Object.values(providers).flat().length;
    
    // Query header (master group)
    const queryHeader = document.createElement("div");
    queryHeader.style.cssText = "background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.15);";
    queryHeader.innerHTML = `<h2 style="margin: 0; color: white; font-size: 1.75rem;">${getQueryIcon(query)} ${getQueryName(query)} <span style="opacity: 0.8; font-size: 1.2rem;">(${totalJobs})</span></h2>`;
    container.appendChild(queryHeader);
    
    // Provider subgroups
    Object.keys(providers).sort().forEach(source => {
      const providerJobs = providers[source];
      
      // Provider header (detail group)
      const providerHeader = document.createElement("div");
      providerHeader.style.cssText = "background: white; border-radius: 10px; padding: 0.75rem 1.25rem; margin: 0.5rem 0 0.75rem 1.5rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08); border-left: 4px solid #48bb78;";
      providerHeader.innerHTML = `<h3 style="margin: 0; color: #48bb78; font-size: 1.2rem;">${getSourceIcon(source)} ${getSourceName(source)} <span style="color: #999; font-size: 0.9rem;">(${providerJobs.length})</span></h3>`;
      container.appendChild(providerHeader);
      
      // Jobs
      providerJobs.forEach(job => {
        const div = document.createElement("div");
        div.className = "job";
        div.style.marginLeft = "1.5rem";
        div.innerHTML = `
          <div style="display: flex; align-items: start; gap: 1rem;">
            <input type="checkbox" 
                   ${job.processed ? 'checked' : ''} 
                   onchange="toggleProcessed(${job.id}, this)"
                   style="margin-top: 0.5rem; width: 18px; height: 18px; cursor: pointer; flex-shrink: 0;">
            <div style="flex: 1;">
              <h3><a href="${job.link}" target="_blank">${job.title}</a></h3>
              <p><b>${job.company || "Unbekannt"}</b> – ${job.location || "n/a"}</p>
              <small>${job.posted}</small>
            </div>
          </div>
        `;
        if (job.processed) {
          div.style.opacity = '0.6';
          div.style.background = '#f0fdf4';
        }
        container.appendChild(div);
      });
    });
  });
}

function getJobQuery(title) {
  const titleLower = title.toLowerCase();
  
  // Detect query based on keywords in title
  if (titleLower.includes('rollout') && titleLower.includes('crm')) return 'crm_rollout_manager';
  if (titleLower.includes('business analyst') && titleLower.includes('crm')) return 'crm_business_analyst';
  if (titleLower.includes('salesforce')) return 'salesforce';
  if (titleLower.includes('llm') || titleLower.includes('large language') || 
      titleLower.includes('gpt') || titleLower.includes('ai')) return 'llm';
  if (titleLower.includes('data science') || titleLower.includes('data scientist') ||
      titleLower.includes('machine learning') || titleLower.includes('ml')) return 'data_science';
  
  return 'other';
}

function getQueryIcon(query) {
  const icons = {
    'salesforce': '⚡',
    'llm': '🤖',
    'data_science': '📊',
    'crm_rollout_manager': '🚀',
    'crm_business_analyst': '📋',
    'other': '💼'
  };
  return icons[query] || '💼';
}

function getQueryName(query) {
  const names = {
    'salesforce': 'Salesforce',
    'llm': 'LLM / AI',
    'data_science': 'Data Science',
    'crm_rollout_manager': 'CRM Rollout Manager',
    'crm_business_analyst': 'CRM Business Analyst',
    'other': 'Andere'
  };
  return names[query] || query.charAt(0).toUpperCase() + query.slice(1);
}

function getSourceIcon(source) {
  const icons = {
    'freelancermap': '🗺️',
    'solcom': '💼',
    'hays': '🏢',
    'malt': '🍺'
  };
  return icons[source] || '📋';
}

function getSourceName(source) {
  const names = {
    'freelancermap': 'FreelancerMap',
    'solcom': 'Solcom',
    'hays': 'Hays',
    'malt': 'Malt'
  };
  return names[source] || source.charAt(0).toUpperCase() + source.slice(1);
}

function displayAsTable(jobs, container) {
  // Group jobs based on grouping mode
  if (groupingMode === 'provider-query') {
    displayTableGroupedByProviderThenQuery(jobs, container);
  } else {
    displayTableGroupedByQueryThenProvider(jobs, container);
  }
}

function displayTableGroupedByProviderThenQuery(jobs, container) {
  // Group by source, then by query
  const grouped = {};
  
  jobs.forEach(job => {
    const source = job.source;
    const query = getJobQuery(job.title);
    
    if (!grouped[source]) {
      grouped[source] = {};
    }
    if (!grouped[source][query]) {
      grouped[source][query] = [];
    }
    grouped[source][query].push(job);
  });
  
  // Display: Provider > Query > Table
  Object.keys(grouped).sort().forEach(source => {
    const queries = grouped[source];
    const totalJobs = Object.values(queries).flat().length;
    
    // Provider header (master group)
    const providerHeader = document.createElement('div');
    providerHeader.style.cssText = 'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    providerHeader.innerHTML = `<h2 style="margin: 0; color: white; font-size: 1.75rem;">${getSourceIcon(source)} ${getSourceName(source)} <span style="opacity: 0.8; font-size: 1.2rem;">(${totalJobs})</span></h2>`;
    container.appendChild(providerHeader);
    
    // Query subgroups with tables
    Object.keys(queries).sort().forEach(query => {
      const queryJobs = queries[query];
      
      // Query header (detail group)
      const queryHeader = document.createElement('div');
      queryHeader.style.cssText = 'background: white; border-radius: 10px 10px 0 0; padding: 0.75rem 1.25rem; margin: 0.5rem 0 0 1.5rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08); border-left: 4px solid #667eea;';
      queryHeader.innerHTML = `<h3 style="margin: 0; color: #667eea; font-size: 1.2rem;">${getQueryIcon(query)} ${getQueryName(query)} <span style="color: #999; font-size: 0.9rem;">(${queryJobs.length})</span></h3>`;
      container.appendChild(queryHeader);
      
      // Table for this query
      createJobTable(queryJobs, container, '1.5rem');
    });
  });
}

function displayTableGroupedByQueryThenProvider(jobs, container) {
  // Group by query, then by source
  const grouped = {};
  
  jobs.forEach(job => {
    const query = getJobQuery(job.title);
    const source = job.source;
    
    if (!grouped[query]) {
      grouped[query] = {};
    }
    if (!grouped[query][source]) {
      grouped[query][source] = [];
    }
    grouped[query][source].push(job);
  });
  
  // Display: Query > Provider > Table
  Object.keys(grouped).sort().forEach(query => {
    const providers = grouped[query];
    const totalJobs = Object.values(providers).flat().length;
    
    // Query header (master group)
    const queryHeader = document.createElement('div');
    queryHeader.style.cssText = 'background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.15);';
    queryHeader.innerHTML = `<h2 style="margin: 0; color: white; font-size: 1.75rem;">${getQueryIcon(query)} ${getQueryName(query)} <span style="opacity: 0.8; font-size: 1.2rem;">(${totalJobs})</span></h2>`;
    container.appendChild(queryHeader);
    
    // Provider subgroups with tables
    Object.keys(providers).sort().forEach(source => {
      const providerJobs = providers[source];
      
      // Provider header (detail group)
      const providerHeader = document.createElement('div');
      providerHeader.style.cssText = 'background: white; border-radius: 10px 10px 0 0; padding: 0.75rem 1.25rem; margin: 0.5rem 0 0 1.5rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08); border-left: 4px solid #48bb78;';
      providerHeader.innerHTML = `<h3 style="margin: 0; color: #48bb78; font-size: 1.2rem;">${getSourceIcon(source)} ${getSourceName(source)} <span style="color: #999; font-size: 0.9rem;">(${providerJobs.length})</span></h3>`;
      container.appendChild(providerHeader);
      
      // Table for this provider
      createJobTable(providerJobs, container, '1.5rem');
    });
  });
}

// Sorting state per table (using a Map to track multiple tables)
const tableSortState = new Map();

// Helper function to parse German date format
function parseGermanDate(dateStr) {
  if (!dateStr || dateStr === 'N/A') return null;
  
  // Handle relative dates like "vor 2 Tagen", "heute", "gestern"
  const now = new Date();
  if (dateStr.toLowerCase().includes('heute')) {
    return now;
  }
  if (dateStr.toLowerCase().includes('gestern')) {
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    return yesterday;
  }
  
  const daysMatch = dateStr.match(/vor\s+(\d+)\s+tag/i);
  if (daysMatch) {
    const daysAgo = parseInt(daysMatch[1]);
    const date = new Date(now);
    date.setDate(date.getDate() - daysAgo);
    return date;
  }
  
  // Try to parse DD.MM.YYYY format
  const parts = dateStr.split('.');
  if (parts.length === 3) {
    const day = parseInt(parts[0]);
    const month = parseInt(parts[1]) - 1; // JS months are 0-indexed
    const year = parseInt(parts[2]);
    if (!isNaN(day) && !isNaN(month) && !isNaN(year)) {
      return new Date(year, month, day);
    }
  }
  
  return null;
}

// Helper function to compare values for sorting
function compareValues(a, b, column, ascending) {
  let aVal, bVal;
  
  switch (column) {
    case 'posted': // Date column
      aVal = parseGermanDate(a.posted);
      bVal = parseGermanDate(b.posted);
      
      // Handle null dates (put them at the end)
      if (!aVal && !bVal) return 0;
      if (!aVal) return 1;
      if (!bVal) return -1;
      
      return ascending ? aVal - bVal : bVal - aVal;
      
    case 'title':
    case 'company':
    case 'location':
      aVal = (a[column] || 'N/A').toLowerCase();
      bVal = (b[column] || 'N/A').toLowerCase();
      
      if (aVal === bVal) return 0;
      const result = aVal < bVal ? -1 : 1;
      return ascending ? result : -result;
      
    default:
      return 0;
  }
}

// Function to sort and re-render table
function sortTable(tableId, column) {
  const state = tableSortState.get(tableId) || { column: null, ascending: true };
  
  // Toggle direction if clicking same column, otherwise default to ascending
  if (state.column === column) {
    state.ascending = !state.ascending;
  } else {
    state.column = column;
    state.ascending = true;
  }
  
  tableSortState.set(tableId, state);
  
  // Get the table and its data
  const tableWrapper = document.querySelector(`[data-table-id="${tableId}"]`);
  if (!tableWrapper) return;
  
  const jobs = tableWrapper.__jobsData;
  if (!jobs) return;
  
  // Sort the jobs
  const sortedJobs = [...jobs].sort((a, b) => compareValues(a, b, column, state.ascending));
  
  // Re-render the table body
  const tbody = tableWrapper.querySelector('tbody');
  tbody.innerHTML = '';
  
  sortedJobs.forEach((job, index) => {
    const row = document.createElement('tr');
    row.style.cssText = 'border-bottom: 1px solid #e2e8f0; transition: background 0.2s;';
    
    const baseBackground = index % 2 === 0 ? 'white' : '#fafafa';
    const processedBackground = job.processed ? '#f0fdf4' : baseBackground;
    
    row.onmouseover = () => row.style.background = '#f7fafc';
    row.onmouseout = () => row.style.background = processedBackground;
    row.style.background = processedBackground;
    
    if (job.processed) {
      row.style.opacity = '0.6';
    }
    
    row.innerHTML = `
      <td style="padding: 0.75rem; text-align: center; vertical-align: middle;">
        <input type="checkbox" 
               ${job.processed ? 'checked' : ''} 
               onchange="toggleProcessed(${job.id}, this)"
               style="width: 18px; height: 18px; cursor: pointer;">
      </td>
      <td style="padding: 0.75rem; vertical-align: top;">
        <a href="${job.link}" target="_blank" style="color: #667eea; font-weight: 500; text-decoration: none;">
          ${job.title}
        </a>
      </td>
      <td style="padding: 0.75rem; vertical-align: top; color: #4a5568;">${job.company || 'N/A'}</td>
      <td style="padding: 0.75rem; vertical-align: top; color: #4a5568;">${job.location || 'N/A'}</td>
      <td style="padding: 0.75rem; vertical-align: top; color: #718096; font-size: 0.85rem;">${job.posted}</td>
    `;
    
    tbody.appendChild(row);
  });
  
  // Update header sort indicators
  updateSortIndicators(tableId, column, state.ascending);
}

// Update sort indicators in table headers
function updateSortIndicators(tableId, activeColumn, ascending) {
  const tableWrapper = document.querySelector(`[data-table-id="${tableId}"]`);
  if (!tableWrapper) return;
  
  const headers = tableWrapper.querySelectorAll('th[data-column]');
  headers.forEach(th => {
    const column = th.getAttribute('data-column');
    const indicator = th.querySelector('.sort-indicator');
    
    if (column === activeColumn) {
      indicator.textContent = ascending ? ' ▲' : ' ▼';
      indicator.style.opacity = '1';
    } else {
      indicator.textContent = ' ▲';
      indicator.style.opacity = '0.3';
    }
  });
}

function createJobTable(jobs, container, marginLeft = '0') {
  // Generate unique table ID
  const tableId = 'table_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  
  // Determine default sort: by date descending if any job has a valid date, otherwise by company
  let defaultColumn = 'company';
  let defaultAscending = true;
  
  const hasValidDates = jobs.some(job => parseGermanDate(job.posted) !== null);
  if (hasValidDates) {
    defaultColumn = 'posted';
    defaultAscending = false; // Descending for dates (newest first)
  }
  
  // Sort jobs with default sorting
  const sortedJobs = [...jobs].sort((a, b) => compareValues(a, b, defaultColumn, defaultAscending));
  
  // Create table wrapper
  const tableWrapper = document.createElement('div');
  tableWrapper.style.cssText = `background: white; border-radius: 0 0 10px 10px; padding: 0 1.5rem 1.5rem 1.5rem; margin-left: ${marginLeft}; margin-bottom: 1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08); overflow-x: auto;`;
  tableWrapper.setAttribute('data-table-id', tableId);
  tableWrapper.__jobsData = jobs; // Store original jobs data
  
  // Initialize sort state for this table
  tableSortState.set(tableId, { column: defaultColumn, ascending: defaultAscending });
  
  // Create table
  const table = document.createElement('table');
  table.style.cssText = 'width: 100%; border-collapse: collapse; font-size: 0.95rem;';
  
  // Table header with sortable columns
  const thead = document.createElement('thead');
  thead.innerHTML = `
    <tr style="background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
      <th style="padding: 0.75rem; text-align: center; font-weight: 600; color: #2d3748; font-size: 0.85rem; width: 50px;">✓</th>
      <th data-column="title" onclick="sortTable('${tableId}', 'title')" style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem; cursor: pointer; user-select: none;">
        Titel<span class="sort-indicator" style="opacity: 0.3;"> ▲</span>
      </th>
      <th data-column="company" onclick="sortTable('${tableId}', 'company')" style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem; cursor: pointer; user-select: none;">
        Firma<span class="sort-indicator" style="opacity: 0.3;"> ▲</span>
      </th>
      <th data-column="location" onclick="sortTable('${tableId}', 'location')" style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem; cursor: pointer; user-select: none;">
        Ort<span class="sort-indicator" style="opacity: 0.3;"> ▲</span>
      </th>
      <th data-column="posted" onclick="sortTable('${tableId}', 'posted')" style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem; cursor: pointer; user-select: none;">
        Veröffentlicht<span class="sort-indicator" style="opacity: 0.3;"> ▲</span>
      </th>
    </tr>
  `;
  table.appendChild(thead);
  
  // Table body
  const tbody = document.createElement('tbody');
  
  sortedJobs.forEach((job, index) => {
    const row = document.createElement('tr');
    row.style.cssText = 'border-bottom: 1px solid #e2e8f0; transition: background 0.2s;';
    
    const baseBackground = index % 2 === 0 ? 'white' : '#fafafa';
    const processedBackground = job.processed ? '#f0fdf4' : baseBackground;
    
    row.onmouseover = () => row.style.background = '#f7fafc';
    row.onmouseout = () => row.style.background = processedBackground;
    row.style.background = processedBackground;
    
    if (job.processed) {
      row.style.opacity = '0.6';
    }
    
    row.innerHTML = `
      <td style="padding: 0.75rem; text-align: center; vertical-align: middle;">
        <input type="checkbox" 
               ${job.processed ? 'checked' : ''} 
               onchange="toggleProcessed(${job.id}, this)"
               style="width: 18px; height: 18px; cursor: pointer;">
      </td>
      <td style="padding: 0.75rem; vertical-align: top;">
        <a href="${job.link}" target="_blank" style="color: #667eea; font-weight: 500; text-decoration: none;">
          ${job.title}
        </a>
      </td>
      <td style="padding: 0.75rem; vertical-align: top; color: #4a5568;">${job.company || 'N/A'}</td>
      <td style="padding: 0.75rem; vertical-align: top; color: #4a5568;">${job.location || 'N/A'}</td>
      <td style="padding: 0.75rem; vertical-align: top; color: #718096; font-size: 0.85rem;">${job.posted}</td>
    `;
    
    tbody.appendChild(row);
  });
  
  table.appendChild(tbody);
  tableWrapper.appendChild(table);
  container.appendChild(tableWrapper);
  
  // Update sort indicators to show default sort state
  updateSortIndicators(tableId, defaultColumn, defaultAscending);
}

function toggleGrouping() {
  const btn = document.getElementById('groupingBtn');
  
  if (groupingMode === 'provider-query') {
    groupingMode = 'query-provider';
    btn.innerHTML = '🔄 Gruppierung: Query → Provider';
    btn.style.background = '#48bb78';
  } else {
    groupingMode = 'provider-query';
    btn.innerHTML = '🔄 Gruppierung: Provider → Query';
    btn.style.background = '#667eea';
  }
  
  loadJobs();
}

function toggleDisplay() {
  const btn = document.getElementById('displayBtn');
  
  if (displayMode === 'cards') {
    displayMode = 'table';
    btn.innerHTML = '📊 Ansicht: Tabelle';
    btn.style.background = '#ed8936';
  } else {
    displayMode = 'cards';
    btn.innerHTML = '🎴 Ansicht: Karten';
    btn.style.background = '#667eea';
  }
  
  loadJobs();
}

let logLines = [];
const MAX_LOG_LINES = 5;
let progressInterval = null;

function showProgress() {
  document.getElementById('progressContainer').style.display = 'block';
  document.getElementById('logContainer').style.display = 'block';
  logLines = [];
  updateLogWindow();
}

function hideProgress() {
  document.getElementById('progressContainer').style.display = 'none';
  document.getElementById('logContainer').style.display = 'none';
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
}

function updateProgress(percent, text = '') {
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');
  
  progressBar.style.width = percent + '%';
  progressBar.textContent = Math.round(percent) + '%';
  progressText.textContent = Math.round(percent) + '%';
}

function addLogLine(message, type = 'info') {
  const timestamp = new Date().toLocaleTimeString('de-DE');
  const colors = {
    'info': '#60a5fa',
    'success': '#48bb78',
    'error': '#f56565',
    'warning': '#ed8936'
  };
  const color = colors[type] || colors['info'];
  
  logLines.push({ timestamp, message, color });
  
  // Keep only last MAX_LOG_LINES
  if (logLines.length > MAX_LOG_LINES) {
    logLines.shift();
  }
  
  updateLogWindow();
}

function updateLogWindow() {
  const logWindow = document.getElementById('logWindow');
  logWindow.innerHTML = logLines.map(log => 
    `<div style="color: ${log.color}; margin-bottom: 0.25rem;">[${log.timestamp}] ${log.message}</div>`
  ).join('');
  
  // Auto-scroll to bottom
  const logContainer = document.getElementById('logContainer');
  logContainer.scrollTop = logContainer.scrollHeight;
}

async function triggerCrawler() {
  const btn = document.getElementById('crawlerBtn');
  const originalText = btn.innerHTML;
  
  try {
    btn.innerHTML = '⏳ Crawler wird gestartet...';
    btn.disabled = true;
    
    // Show progress UI
    showProgress();
    addLogLine('Crawler wird gestartet...', 'info');
    updateProgress(0);
    
    const response = await fetch(`${API_URL}/crawler/run`, {
      method: 'POST',
      credentials: 'include'
    });
    
    const data = await response.json();
    
    // Check if crawler is already running
    if (data.status === 'error') {
      addLogLine(data.message, 'warning');
      btn.innerHTML = '⚠️ Läuft bereits';
      btn.style.background = '#ed8936';
      setTimeout(() => {
        hideProgress();
        btn.innerHTML = originalText;
        btn.style.background = '#48bb78';
        btn.disabled = false;
      }, 3000);
      return;
    }
    
    if (response.ok && data.status === 'started') {
      btn.innerHTML = '⏳ Crawler läuft...';
      addLogLine('Crawler erfolgreich gestartet', 'success');
      
      // Poll for real progress from API
      progressInterval = setInterval(async () => {
        try {
          const progressResponse = await fetch(`${API_URL}/crawler/progress`, {
            credentials: 'include'
          });
          const progressData = await progressResponse.json();
          
          // Calculate progress percentage: completed / total * 100
          const progressPercent = progressData.total > 0 
            ? (progressData.completed / progressData.total) * 100 
            : 0;
          
          updateProgress(progressPercent);
          
          // Update log window with latest logs from backend
          if (progressData.logs && progressData.logs.length > 0) {
            // Clear current logs and add new ones
            logLines = [];
            progressData.logs.forEach(log => {
              // Determine log type based on content
              let type = 'info';
              if (log.includes('abgeschlossen') || log.includes('Alle Crawler')) {
                type = 'success';
              } else if (log.includes('Fehler') || log.includes('Timeout')) {
                type = 'error';
              }
              
              const timestamp = new Date().toLocaleTimeString('de-DE');
              const colors = {
                'info': '#60a5fa',
                'success': '#48bb78',
                'error': '#f56565',
                'warning': '#ed8936'
              };
              logLines.push({ timestamp, message: log, color: colors[type] });
            });
            updateLogWindow();
          }
          
          // Check if crawler finished
          if (!progressData.running && progressData.completed >= progressData.total) {
            clearInterval(progressInterval);
            progressInterval = null;
            updateProgress(100);
            
            // Hide progress after a short delay
            setTimeout(() => {
              hideProgress();
              loadJobs();
              btn.innerHTML = originalText;
              btn.disabled = false;
              btn.style.background = '#48bb78';
            }, 2000);
          }
        } catch (error) {
          console.error('Error polling progress:', error);
        }
      }, 500); // Poll every 500ms for responsive updates
      
    } else {
      addLogLine('Fehler: ' + data.detail, 'error');
      btn.innerHTML = '❌ Fehler';
      btn.style.background = '#f56565';
      setTimeout(() => {
        hideProgress();
        btn.innerHTML = originalText;
        btn.style.background = '#48bb78';
        btn.disabled = false;
      }, 3000);
    }
  } catch (error) {
    addLogLine('Verbindungsfehler: ' + error.message, 'error');
    btn.innerHTML = '❌ Verbindungsfehler';
    btn.style.background = '#f56565';
    setTimeout(() => {
      hideProgress();
      btn.innerHTML = originalText;
      btn.style.background = '#48bb78';
      btn.disabled = false;
    }, 3000);
  }
}

loadJobs();

// ========== Configuration Editor Functions ==========

let currentConfig = null;
let currentVersionFilename = null;
let versions = [];

// Tab Switching
function switchTab(tabName) {
  // Update tab buttons
  document.querySelectorAll('.tab').forEach(tab => {
    tab.classList.remove('active');
  });
  event.target.classList.add('active');
  
  // Update tab content
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });
  
  if (tabName === 'jobs') {
    document.getElementById('jobsTab').classList.add('active');
  } else if (tabName === 'config') {
    document.getElementById('configTab').classList.add('active');
    loadConfig();
    loadVersionHistory();
    loadConfigSummary();
  } else if (tabName === 'documents') {
    document.getElementById('documentsTab').classList.add('active');
    loadDocuments();
    initializeDropZone();
  }
}

// Load current configuration
async function loadConfig() {
  try {
    const response = await fetch(`${API_URL}/config`, {
      credentials: 'include'
    });
    const data = await response.json();
    
    if (data.error) {
      showConfigStatus('Error loading configuration: ' + data.error, 'error');
      return;
    }
    
    currentConfig = data.config;
    document.getElementById('configTextarea').value = JSON.stringify(data.config, null, 2);
    currentVersionFilename = null;
    document.getElementById('activateBtn').disabled = true;
  } catch (error) {
    showConfigStatus('Error loading configuration: ' + error.message, 'error');
  }
}

// Load version history
async function loadVersionHistory() {
  try {
    const response = await fetch(`${API_URL}/config/versions`, {
      credentials: 'include'
    });
    const data = await response.json();
    
    if (data.error) {
      document.getElementById('versionList').innerHTML = 
        `<div style="text-align: center; color: #e53e3e; padding: 2rem;">Error: ${data.error}</div>`;
      return;
    }
    
    versions = data.versions || [];
    renderVersionList();
  } catch (error) {
    document.getElementById('versionList').innerHTML = 
      `<div style="text-align: center; color: #e53e3e; padding: 2rem;">Error: ${error.message}</div>`;
  }
}

// Render version list
function renderVersionList() {
  const versionList = document.getElementById('versionList');
  
  if (versions.length === 0) {
    versionList.innerHTML = 
      '<div style="text-align: center; color: #718096; padding: 2rem;">No versions saved yet</div>';
    return;
  }
  
  versionList.innerHTML = versions.map(version => {
    const date = new Date(version.modified * 1000);
    const dateStr = date.toLocaleDateString('de-DE');
    const timeStr = date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    
    const isSelected = currentVersionFilename === version.filename;
    const activeClass = isSelected ? 'active' : '';
    
    return `
      <div class="version-item ${activeClass}" onclick="loadVersion('${version.filename}')">
        <div class="version-time">${timeStr}</div>
        <div class="version-date">${dateStr}</div>
        ${version.is_active ? '<div class="version-badge">✓ Active</div>' : ''}
      </div>
    `;
  }).join('');
}

// Load a specific version
async function loadVersion(filename) {
  try {
    const response = await fetch(`${API_URL}/config/version/${filename}`, {
      credentials: 'include'
    });
    const data = await response.json();
    
    if (data.error) {
      showConfigStatus('Error loading version: ' + data.error, 'error');
      return;
    }
    
    currentConfig = data.config;
    currentVersionFilename = filename;
    document.getElementById('configTextarea').value = JSON.stringify(data.config, null, 2);
    document.getElementById('activateBtn').disabled = false;
    
    renderVersionList();
    showConfigStatus(`Loaded version: ${filename}`, 'info');
  } catch (error) {
    showConfigStatus('Error loading version: ' + error.message, 'error');
  }
}

// Validate JSON
function validateConfig() {
  const textarea = document.getElementById('configTextarea');
  const content = textarea.value;
  
  try {
    const parsed = JSON.parse(content);
    showConfigStatus('✓ Valid JSON', 'success');
    return true;
  } catch (error) {
    showConfigStatus('✗ Invalid JSON: ' + error.message, 'error');
    return false;
  }
}

// Save new version
async function saveConfigVersion() {
  const textarea = document.getElementById('configTextarea');
  const content = textarea.value;
  
  // Validate first
  let parsed;
  try {
    parsed = JSON.parse(content);
  } catch (error) {
    showConfigStatus('✗ Cannot save: Invalid JSON - ' + error.message, 'error');
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/config/save`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(parsed)
    });
    
    const data = await response.json();
    
    if (data.status === 'error') {
      showConfigStatus('Error saving: ' + data.error, 'error');
      return;
    }
    
    showConfigStatus('✓ ' + data.message, 'success');
    currentVersionFilename = data.filename;
    document.getElementById('activateBtn').disabled = false;
    
    // Reload version history
    await loadVersionHistory();
  } catch (error) {
    showConfigStatus('Error saving: ' + error.message, 'error');
  }
}

// Activate current config
async function activateCurrentConfig() {
  if (!currentVersionFilename) {
    showConfigStatus('Please save the configuration first', 'warning');
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/config/activate/${currentVersionFilename}`, {
      method: 'POST',
      credentials: 'include'
    });
    
    const data = await response.json();
    
    if (data.status === 'error') {
      showConfigStatus('Error activating: ' + data.error, 'error');
      return;
    }
    
    showConfigStatus('✓ ' + data.message + ' - Will be used for next crawler run!', 'success');
    
    // Reload version history to update active badge
    await loadVersionHistory();
  } catch (error) {
    showConfigStatus('Error activating: ' + error.message, 'error');
  }
}

// Export configuration
async function exportConfig() {
  try {
    const response = await fetch(`${API_URL}/config/export`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      showConfigStatus('Error exporting configuration', 'error');
      return;
    }
    
    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'search_config.json';
    if (contentDisposition) {
      const matches = /filename="(.+)"/.exec(contentDisposition);
      if (matches && matches[1]) {
        filename = matches[1];
      }
    }
    
    // Download the file
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    showConfigStatus('✓ Configuration exported: ' + filename, 'success');
  } catch (error) {
    showConfigStatus('Error exporting: ' + error.message, 'error');
  }
}

// Import configuration
function importConfig() {
  // Create file input
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
      // Read file content
      const text = await file.text();
      let config;
      
      // Parse JSON
      try {
        config = JSON.parse(text);
      } catch (parseError) {
        showConfigStatus('✗ Invalid JSON file: ' + parseError.message, 'error');
        return;
      }
      
      // Send to API for validation and import
      const response = await fetch(`${API_URL}/config/import`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      });
      
      const data = await response.json();
      
      if (data.status === 'error') {
        let errorMsg = 'Import failed: ' + data.error;
        if (data.details && data.details.length > 0) {
          errorMsg += '\n\nValidation errors:\n' + data.details.join('\n');
        }
        showConfigStatus(errorMsg, 'error');
        return;
      }
      
      // Success - load the imported config
      showConfigStatus('✓ ' + data.message, 'success');
      currentVersionFilename = data.filename;
      document.getElementById('configTextarea').value = JSON.stringify(config, null, 2);
      document.getElementById('activateBtn').disabled = false;
      
      // Reload version history
      await loadVersionHistory();
    } catch (error) {
      showConfigStatus('Error importing: ' + error.message, 'error');
    }
  };
  
  input.click();
}

// Show status message
function showConfigStatus(message, type) {
  const statusDiv = document.getElementById('configStatus');
  statusDiv.style.display = 'block';
  statusDiv.textContent = message;
  
  const colors = {
    'success': { bg: '#c6f6d5', border: '#48bb78', text: '#22543d' },
    'error': { bg: '#fed7d7', border: '#f56565', text: '#742a2a' },
    'warning': { bg: '#feebc8', border: '#ed8936', text: '#7c2d12' },
    'info': { bg: '#bee3f8', border: '#4299e1', text: '#2c5282' }
  };
  
  const color = colors[type] || colors.info;
  statusDiv.style.background = color.bg;
  statusDiv.style.border = `2px solid ${color.border}`;
  statusDiv.style.color = color.text;
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    statusDiv.style.display = 'none';
  }, 5000);
}

// Logout function
async function logout() {
  try {
    await fetch(`${API_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include'
    });
    window.location.href = '/login.html';
  } catch (error) {
    console.error('Logout failed:', error);
    // Redirect anyway
    window.location.href = '/login.html';
  }
}

// ========== Document Management Functions ==========

let dropZoneInitialized = false;

// Initialize drag-and-drop functionality
function initializeDropZone() {
  if (dropZoneInitialized) return;
  
  const dropZone = document.getElementById('dropZone');
  
  // Prevent default drag behaviors
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
  });
  
  // Highlight drop zone when item is dragged over it
  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
      dropZone.classList.add('drag-over');
    }, false);
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, () => {
      dropZone.classList.remove('drag-over');
    }, false);
  });
  
  // Handle dropped files
  dropZone.addEventListener('drop', handleDrop, false);
  
  dropZoneInitialized = true;
}

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function handleDrop(e) {
  const dt = e.dataTransfer;
  const files = dt.files;
  handleFiles(files);
}

function handleFileSelect(e) {
  const files = e.target.files;
  handleFiles(files);
}

async function handleFiles(files) {
  if (files.length === 0) return;
  
  // Upload files one by one
  for (let i = 0; i < files.length; i++) {
    await uploadFile(files[i]);
  }
  
  // Reload documents list
  await loadDocuments();
  
  // Reset file input
  document.getElementById('fileInput').value = '';
}

async function uploadFile(file) {
  const progressDiv = document.getElementById('uploadProgress');
  const fileNameSpan = document.getElementById('uploadFileName');
  const percentSpan = document.getElementById('uploadPercent');
  const progressBar = document.getElementById('uploadBar');
  
  // Show progress
  progressDiv.style.display = 'block';
  fileNameSpan.textContent = file.name;
  percentSpan.textContent = '0%';
  progressBar.style.width = '0%';
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_URL}/documents/upload`, {
      method: 'POST',
      credentials: 'include',
      body: formData
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Animate to 100%
      progressBar.style.width = '100%';
      percentSpan.textContent = '100%';
      
      // Hide after a short delay
      setTimeout(() => {
        progressDiv.style.display = 'none';
      }, 1000);
    } else {
      alert('Upload failed: ' + (data.detail || data.error || 'Unknown error'));
      progressDiv.style.display = 'none';
    }
  } catch (error) {
    console.error('Upload error:', error);
    alert('Upload failed: ' + error.message);
    progressDiv.style.display = 'none';
  }
}

async function loadDocuments() {
  const listDiv = document.getElementById('documentsList');
  
  try {
    const response = await fetch(`${API_URL}/documents`, {
      credentials: 'include'
    });
    
    const data = await response.json();
    
    if (data.documents && data.documents.length > 0) {
      listDiv.innerHTML = data.documents.map(doc => {
        const size = formatFileSize(doc.size);
        const date = new Date(doc.modified_iso);
        const dateStr = date.toLocaleDateString('de-DE');
        const timeStr = date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
        const icon = getFileIcon(doc.name);
        
        return `
          <div class="document-item">
            <div class="document-info">
              <div class="document-icon">${icon}</div>
              <div class="document-details">
                <div class="document-name">${escapeHtml(doc.name)}</div>
                <div class="document-meta">${size} • ${dateStr} ${timeStr}</div>
              </div>
            </div>
            <div class="document-actions">
              <button class="doc-btn download" onclick="downloadDocument('${escapeHtml(doc.name)}')">
                ⬇️ Download
              </button>
              <button class="doc-btn delete" onclick="deleteDocument('${escapeHtml(doc.name)}')">
                🗑️ Delete
              </button>
            </div>
          </div>
        `;
      }).join('');
    } else {
      listDiv.innerHTML = '<p style="text-align: center; color: #718096; padding: 2rem;">No documents uploaded yet. Drag & drop files above to get started.</p>';
    }
  } catch (error) {
    console.error('Error loading documents:', error);
    listDiv.innerHTML = '<p style="text-align: center; color: #e53e3e; padding: 2rem;">Error loading documents: ' + error.message + '</p>';
  }
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  const icons = {
    'pdf': '📕',
    'doc': '📘',
    'docx': '📘',
    'txt': '📄',
    'png': '🖼️',
    'jpg': '🖼️',
    'jpeg': '🖼️',
    'gif': '🖼️',
    'zip': '📦',
    'rar': '📦'
  };
  return icons[ext] || '📄';
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

async function downloadDocument(filename) {
  try {
    const response = await fetch(`${API_URL}/documents/${encodeURIComponent(filename)}`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error('Download failed');
    }
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('Download error:', error);
    alert('Download failed: ' + error.message);
  }
}

async function deleteDocument(filename) {
  if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
    return;
  }
  
  try {
    const response = await fetch(`${API_URL}/documents/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
      credentials: 'include'
    });
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Reload documents list
      await loadDocuments();
    } else {
      alert('Delete failed: ' + (data.detail || data.error || 'Unknown error'));
    }
  } catch (error) {
    console.error('Delete error:', error);
    alert('Delete failed: ' + error.message);
  }
}

// ========== Configuration Wizard Functions ==========

let configMode = 'simple'; // 'simple' or 'expert'
let wizardConfig = null; // Working copy of config for wizard

// Switch between simple and expert mode
function switchConfigMode(mode) {
  configMode = mode;
  
  const simpleMode = document.getElementById('simpleMode');
  const expertMode = document.getElementById('expertMode');
  const simpleModeBtn = document.getElementById('simpleModeBtn');
  const expertModeBtn = document.getElementById('expertModeBtn');
  
  if (mode === 'simple') {
    simpleMode.style.display = 'block';
    expertMode.style.display = 'none';
    simpleModeBtn.style.background = '#48bb78';
    simpleModeBtn.style.color = 'white';
    expertModeBtn.style.background = '#cbd5e0';
    expertModeBtn.style.color = '#4a5568';
    loadConfigSummary();
  } else {
    simpleMode.style.display = 'none';
    expertMode.style.display = 'block';
    expertModeBtn.style.background = '#667eea';
    expertModeBtn.style.color = 'white';
    simpleModeBtn.style.background = '#cbd5e0';
    simpleModeBtn.style.color = '#4a5568';
    loadConfig();
    loadVersionHistory();
  }
}

// Load and display configuration summary
async function loadConfigSummary() {
  try {
    const response = await fetch(`${API_URL}/config`, {
      credentials: 'include'
    });
    const data = await response.json();
    
    if (data.error) {
      document.getElementById('configSummary').innerHTML = 
        `<p style="color: #e53e3e;">Error loading configuration: ${data.error}</p>`;
      return;
    }
    
    wizardConfig = data.config;
    
    // Count queries per provider
    const providers = ['freelancermap', 'solcom', 'hays'];
    let summaryHTML = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">';
    
    providers.forEach(provider => {
      const providerConfig = wizardConfig[provider];
      const queryCount = providerConfig && providerConfig.queries ? providerConfig.queries.length : 0;
      const icon = provider === 'freelancermap' ? '🗺️' : provider === 'solcom' ? '💼' : '🏢';
      
      summaryHTML += `
        <div style="background: #f7fafc; border: 2px solid #e2e8f0; border-radius: 8px; padding: 1rem; text-align: center;">
          <div style="font-size: 2rem; margin-bottom: 0.5rem;">${icon}</div>
          <div style="font-weight: 600; color: #2d3748; margin-bottom: 0.25rem;">${provider.charAt(0).toUpperCase() + provider.slice(1)}</div>
          <div style="color: #667eea; font-size: 1.5rem; font-weight: bold;">${queryCount}</div>
          <div style="color: #718096; font-size: 0.85rem;">queries</div>
        </div>
      `;
    });
    
    // Count total keywords
    const keywordCategories = wizardConfig.keywords ? Object.keys(wizardConfig.keywords).length : 0;
    const totalKeywords = wizardConfig.keywords ? 
      Object.values(wizardConfig.keywords).reduce((sum, arr) => sum + arr.length, 0) : 0;
    
    summaryHTML += `
      <div style="background: #f0fff4; border: 2px solid #9ae6b4; border-radius: 8px; padding: 1rem; text-align: center;">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🏷️</div>
        <div style="font-weight: 600; color: #2d3748; margin-bottom: 0.25rem;">Keywords</div>
        <div style="color: #48bb78; font-size: 1.5rem; font-weight: bold;">${totalKeywords}</div>
        <div style="color: #718096; font-size: 0.85rem;">${keywordCategories} categories</div>
      </div>
    `;
    
    summaryHTML += '</div>';
    document.getElementById('configSummary').innerHTML = summaryHTML;
  } catch (error) {
    document.getElementById('configSummary').innerHTML = 
      `<p style="color: #e53e3e;">Error: ${error.message}</p>`;
  }
}

// Open wizard modal
function openWizard(wizardType) {
  const modal = document.getElementById('wizardModal');
  const title = document.getElementById('wizardTitle');
  const body = document.getElementById('wizardBody');
  
  modal.style.display = 'flex';
  
  switch (wizardType) {
    case 'manageKeywords':
      title.textContent = '🏷️ Manage Keywords';
      body.innerHTML = renderManageKeywordsWizard();
      break;
    case 'viewQueries':
      title.textContent = '📋 View and Edit All Queries';
      body.innerHTML = renderViewQueriesWizard();
      break;
  }
}

// Close wizard modal
function closeWizard() {
  document.getElementById('wizardModal').style.display = 'none';
}

// Render Add Query Wizard
function renderAddQueryWizard() {
  const providers = [
    { value: 'freelancermap', label: '🗺️ FreelancerMap' },
    { value: 'solcom', label: '💼 Solcom' },
    { value: 'hays', label: '🏢 Hays' }
  ];
  
  // Collect all unique queries from all providers
  const allQueries = new Set();
  providers.forEach(p => {
    const providerConfig = wizardConfig[p.value];
    if (providerConfig && providerConfig.queries) {
      providerConfig.queries.forEach(q => {
        if (q.query) {
          allQueries.add(q.query);
        }
      });
    }
  });
  
  const uniqueQueries = Array.from(allQueries).sort();
  const keywordCategories = wizardConfig.keywords ? Object.keys(wizardConfig.keywords) : [];
  
  return `
    <div class="wizard-help">
      💡 Add a new search query to one or more job providers. Select which keyword filters to apply.
    </div>
    
    <div class="wizard-form-group">
      <label class="wizard-label">Search Query *</label>
      <select id="querySelect" class="wizard-select" onchange="toggleCustomQueryInput()">
        <option value="">-- Select a query --</option>
        ${uniqueQueries.map(q => `<option value="${escapeHtml(q)}">${escapeHtml(q)}</option>`).join('')}
        <option value="__custom__">➕ Custom query...</option>
      </select>
    </div>
    
    <div class="wizard-form-group" id="customQueryGroup" style="display: none;">
      <label class="wizard-label">Custom Query Text *</label>
      <input type="text" id="customQueryText" class="wizard-input" placeholder="e.g., salesforce developer" />
    </div>
    
    <div class="wizard-form-group">
      <label class="wizard-label">Select Providers *</label>
      <div class="wizard-checkbox-group">
        ${providers.map(p => `
          <div class="wizard-checkbox-item">
            <input type="checkbox" id="provider_${p.value}" value="${p.value}" checked />
            <label for="provider_${p.value}">${p.label}</label>
          </div>
        `).join('')}
      </div>
    </div>
    
    <div class="wizard-form-group">
      <label class="wizard-label">Keyword Filters (optional)</label>
      <div class="wizard-checkbox-group">
        ${keywordCategories.map(cat => `
          <div class="wizard-checkbox-item">
            <input type="checkbox" id="keyword_${cat}" value="${cat}" />
            <label for="keyword_${cat}">${cat}</label>
          </div>
        `).join('')}
      </div>
    </div>
    
    <div class="wizard-actions">
      <button class="wizard-btn secondary" onclick="closeWizard()">Cancel</button>
      <button class="wizard-btn primary" onclick="saveNewQuery()">✓ Add Query</button>
    </div>
  `;
}

// Render Manage Keywords Wizard
function renderManageKeywordsWizard() {
  const keywords = wizardConfig.keywords || {};
  const categories = Object.keys(keywords);
  
  let html = `
    <div class="wizard-help">
      💡 Manage keyword filters used to refine search results. Add new categories or edit existing ones.
    </div>
  `;
  
  if (categories.length > 0) {
    html += `
      <table class="keyword-table">
        <thead>
          <tr>
            <th>Category</th>
            <th>Keywords (comma-separated)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
    `;
    
    categories.forEach(category => {
      const keywordList = keywords[category].join(', ');
      
      // Check if category is in use by ANY provider
      const providers = ['freelancermap', 'solcom', 'hays'];
      let isInUse = false;
      providers.forEach(provider => {
        const providerConfig = wizardConfig[provider];
        if (providerConfig && providerConfig.queries) {
          providerConfig.queries.forEach(q => {
            if (Array.isArray(q.keywords) && q.keywords.includes(category)) {
              isInUse = true;
            } else if (typeof q.keywords === 'string' && q.keywords === category) {
              isInUse = true;
            }
          });
        }
      });
      
      const deleteDisabled = isInUse ? 'disabled' : '';
      const deleteStyle = isInUse ? 
        'padding: 0.5rem 0.75rem; font-size: 0.8rem; opacity: 0.4; cursor: not-allowed; pointer-events: none; min-width: 80px;' : 
        'padding: 0.5rem 0.75rem; font-size: 0.8rem; min-width: 80px;';
      
      html += `
        <tr>
          <td class="keyword-category-name">${escapeHtml(category)}</td>
          <td class="keyword-input-cell">
            <input type="text" id="keywords_${category}" class="wizard-input" 
                   value="${escapeHtml(keywordList)}" 
                   placeholder="Enter keywords separated by commas" />
          </td>
          <td class="keyword-actions-cell">
            <button class="query-btn edit" onclick="saveSingleCategory('${category.replace(/'/g, "\\'")}')"
                    style="padding: 0.5rem 0.75rem; font-size: 0.8rem; margin-right: 0.25rem; min-width: 80px;">✓ Save</button>
            <button class="query-btn delete" onclick="deleteKeywordCategory('${category.replace(/'/g, "\\'")}')"
                    ${deleteDisabled}
                    style="${deleteStyle}">🗑️</button>
          </td>
        </tr>
      `;
    });
    
    html += `
        </tbody>
      </table>
    `;
  } else {
    html += `
      <p style="text-align: center; color: #718096; padding: 2rem; background: #f7fafc; border-radius: 8px;">
        No keyword categories yet. Add your first category below.
      </p>
    `;
  }
  
  html += `
    <div style="background: #f7fafc; border-radius: 8px; padding: 1.5rem; margin-top: 1.5rem;">
      <h4 style="margin: 0 0 1rem 0; color: #2d3748;">➕ Add New Category</h4>
      <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem;">
        <thead>
          <tr style="background: #edf2f7; border-bottom: 2px solid #cbd5e0;">
            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem; width: 250px;">Category Name *</th>
            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem;">Keywords (comma-separated) *</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 0.75rem; vertical-align: top;">
              <input type="text" id="newCategoryName" class="wizard-input" placeholder="e.g., cloud_computing" style="width: 100%;" />
            </td>
            <td style="padding: 0.75rem; vertical-align: top;">
              <input type="text" id="newCategoryKeywords" class="wizard-input" placeholder="e.g., AWS, Azure, Google Cloud, Kubernetes" style="width: 100%; min-width: 0;" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <div class="wizard-actions">
      <button class="wizard-btn secondary" onclick="closeWizard()">Cancel</button>
      <button class="wizard-btn primary" onclick="addKeywordCategory()">✓ Add Category</button>
    </div>
  `;
  
  return html;
}

// Render View Queries Wizard
function renderViewQueriesWizard() {
  const providers = ['freelancermap', 'solcom', 'hays'];
  
  // Collect all unique queries from all providers
  const allQueries = new Set();
  providers.forEach(p => {
    const providerConfig = wizardConfig[p];
    if (providerConfig && providerConfig.queries) {
      providerConfig.queries.forEach(q => {
        if (q.query) {
          allQueries.add(q.query);
        }
      });
    }
  });
  const uniqueQueries = Array.from(allQueries).sort();
  
  let html = `
    <div class="wizard-help">
      💡 View and manage all configured search queries across providers. Add existing queries or delete them.
    </div>
  `;
  
  providers.forEach(provider => {
    const providerConfig = wizardConfig[provider];
    const queries = providerConfig && providerConfig.queries ? providerConfig.queries : [];
    const icon = provider === 'freelancermap' ? '🗺️' : provider === 'solcom' ? '💼' : '🏢';
    const providerName = provider.charAt(0).toUpperCase() + provider.slice(1);
    
    html += `
      <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 1rem 1.5rem; margin: 1.5rem 0 0.5rem 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <h3 style="margin: 0; color: white; font-size: 1.3rem;">${icon} ${providerName} <span style="opacity: 0.8; font-size: 1rem;">(${queries.length})</span></h3>
      </div>
    `;
    
    if (queries.length === 0) {
      html += `
        <div style="background: white; border-radius: 10px; padding: 2rem; margin-bottom: 1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08); text-align: center;">
          <p style="color: #718096; font-style: italic; margin: 0;">No queries configured</p>
        </div>
      `;
    } else {
      html += `
        <div style="background: white; border-radius: 10px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08); overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem;">
            <thead>
              <tr style="background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem;">Query</th>
                <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #2d3748; font-size: 0.85rem;">Keywords</th>
                <th style="padding: 0.75rem; text-align: center; font-weight: 600; color: #2d3748; font-size: 0.85rem; width: 100px;">Actions</th>
              </tr>
            </thead>
            <tbody>
      `;
      
      queries.forEach((q, index) => {
        const keywordList = Array.isArray(q.keywords) ? q.keywords.join(', ') : q.keywords || 'none';
        const rowBg = index % 2 === 0 ? 'white' : '#fafafa';
        html += `
          <tr style="border-bottom: 1px solid #e2e8f0; background: ${rowBg};" 
              onmouseover="this.style.background='#f7fafc'" 
              onmouseout="this.style.background='${rowBg}'">
            <td style="padding: 0.75rem; vertical-align: top; color: #2d3748; font-weight: 500;">${escapeHtml(q.query)}</td>
            <td style="padding: 0.75rem; vertical-align: top; color: #4a5568;">${escapeHtml(keywordList)}</td>
            <td style="padding: 0.75rem; text-align: center; vertical-align: middle;">
              <button class="query-btn delete" onclick="deleteQuery('${escapeHtml(provider)}', ${index})" 
                      style="padding: 0.5rem 0.75rem;">🗑️ Delete</button>
            </td>
          </tr>
        `;
      });
      
      html += `
            </tbody>
          </table>
        </div>
      `;
    }
    
    // Add section to add keyword categories to this provider
    // Get all available keyword categories
    const allCategories = wizardConfig.keywords ? Object.keys(wizardConfig.keywords) : [];
    
    // Get categories already used by this provider's queries
    const usedCategories = new Set();
    queries.forEach(q => {
      if (Array.isArray(q.keywords)) {
        q.keywords.forEach(cat => {
          usedCategories.add(cat);
        });
      } else if (typeof q.keywords === 'string') {
        // Handle case where keywords might be a string
        usedCategories.add(q.keywords);
      }
    });
    
    console.log(`Provider ${provider} - All categories:`, allCategories);
    console.log(`Provider ${provider} - Used categories:`, Array.from(usedCategories));
    console.log(`Provider ${provider} - Queries:`, queries);
    
    // Find categories that exist but aren't used by this provider
    const availableCategories = allCategories.filter(cat => !usedCategories.has(cat));
    
    if (availableCategories.length > 0) {
      html += `
        <div style="background: white; border-radius: 10px; padding: 1rem 1.5rem; margin-bottom: 1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.08);">
          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <label style="font-weight: 600; color: #2d3748; white-space: nowrap;">➕ Add Category:</label>
            <select id="addCategory_${provider}" class="wizard-select" style="flex: 1;">
              <option value="">-- Select a category to add --</option>
              ${availableCategories.map(cat => `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`).join('')}
            </select>
            <button class="wizard-btn primary" onclick="addCategoryToProvider('${provider}')" style="padding: 0.5rem 1rem; white-space: nowrap;">✓ Add</button>
          </div>
        </div>
      `;
    }
  });
  
  html += `
    <div class="wizard-actions">
      <button class="wizard-btn secondary" onclick="closeWizard()">Close</button>
    </div>
  `;
  
  return html;
}

// Save new query
async function saveNewQuery() {
  const queryText = document.getElementById('queryText').value.trim();
  
  if (!queryText) {
    alert('Please enter a search query');
    return;
  }
  
  // Get selected providers
  const selectedProviders = [];
  ['freelancermap', 'solcom', 'hays'].forEach(provider => {
    const checkbox = document.getElementById(`provider_${provider}`);
    if (checkbox && checkbox.checked) {
      selectedProviders.push(provider);
    }
  });
  
  if (selectedProviders.length === 0) {
    alert('Please select at least one provider');
    return;
  }
  
  // Get selected keywords
  const selectedKeywords = [];
  const keywordCategories = wizardConfig.keywords ? Object.keys(wizardConfig.keywords) : [];
  keywordCategories.forEach(cat => {
    const checkbox = document.getElementById(`keyword_${cat}`);
    if (checkbox && checkbox.checked) {
      selectedKeywords.push(cat);
    }
  });
  
  // Add query to selected providers
  selectedProviders.forEach(provider => {
    if (!wizardConfig[provider]) {
      wizardConfig[provider] = { queries: [] };
    }
    if (!wizardConfig[provider].queries) {
      wizardConfig[provider].queries = [];
    }
    
    wizardConfig[provider].queries.push({
      query: queryText,
      keywords: selectedKeywords
    });
  });
  
  // Save configuration
  await saveWizardConfig();
}

// Save single keyword category
async function saveSingleCategory(category) {
  const input = document.getElementById(`keywords_${category}`);
  if (!input) {
    alert('Error: Could not find input field');
    return;
  }
  
  const value = input.value.trim();
  if (!value) {
    alert('Please enter at least one keyword');
    return;
  }
  
  // Update the category in wizardConfig
  wizardConfig.keywords[category] = value.split(',').map(k => k.trim()).filter(k => k);
  
  if (wizardConfig.keywords[category].length === 0) {
    alert('Please enter at least one valid keyword');
    return;
  }
  
  // Save and activate the configuration
  await saveWizardConfig();
  
  // Show success message
  alert(`Category "${category}" saved and activated successfully!`);
}

// Add query to provider
async function addQueryToProvider(provider) {
  const select = document.getElementById(`addQuery_${provider}`);
  if (!select || !select.value) {
    alert('Please select a query to add');
    return;
  }
  
  const queryText = select.value;
  
  // Find the query details from other providers to get keywords
  const providers = ['freelancermap', 'solcom', 'hays'];
  let queryKeywords = [];
  
  for (const p of providers) {
    const providerConfig = wizardConfig[p];
    if (providerConfig && providerConfig.queries) {
      const existingQuery = providerConfig.queries.find(q => q.query === queryText);
      if (existingQuery) {
        queryKeywords = existingQuery.keywords || [];
        break;
      }
    }
  }
  
  // Add query to the provider
  if (!wizardConfig[provider]) {
    wizardConfig[provider] = { queries: [] };
  }
  if (!wizardConfig[provider].queries) {
    wizardConfig[provider].queries = [];
  }
  
  wizardConfig[provider].queries.push({
    query: queryText,
    keywords: queryKeywords
  });
  
  // Save and refresh
  await saveWizardConfig();
  
  // Refresh the wizard to show updated list
  openWizard('viewQueries');
}

// Delete query
async function deleteQuery(provider, index) {
  if (!confirm('Are you sure you want to delete this query?')) {
    return;
  }
  
  if (wizardConfig[provider] && wizardConfig[provider].queries) {
    wizardConfig[provider].queries.splice(index, 1);
  }
  
  await saveWizardConfig();
  // Refresh the wizard view
  openWizard('viewQueries');
}

// Delete keyword category
async function deleteKeywordCategory(category) {
  if (!confirm(`Are you sure you want to delete the "${category}" keyword category?\n\nThis will remove it from the configuration but won't affect queries that are already using it.`)) {
    return;
  }
  
  if (wizardConfig.keywords && wizardConfig.keywords[category]) {
    delete wizardConfig.keywords[category];
  }
  
  // Save and refresh
  await saveWizardConfig();
  
  // Refresh the wizard
  openWizard('manageKeywords');
}

// Add keyword category
async function addKeywordCategory() {
  const categoryName = document.getElementById('newCategoryName').value.trim();
  const keywordsInput = document.getElementById('newCategoryKeywords').value.trim();
  
  if (!categoryName) {
    alert('Please enter a category name');
    return;
  }
  
  if (!keywordsInput) {
    alert('Please enter at least one keyword');
    return;
  }
  
  if (!wizardConfig.keywords) {
    wizardConfig.keywords = {};
  }
  
  if (wizardConfig.keywords[categoryName]) {
    alert('Category already exists');
    return;
  }
  
  // Parse keywords from comma-separated input
  const keywords = keywordsInput.split(',').map(k => k.trim()).filter(k => k);
  
  if (keywords.length === 0) {
    alert('Please enter at least one valid keyword');
    return;
  }
  
  wizardConfig.keywords[categoryName] = keywords;
  
  // Save and activate the configuration
  await saveWizardConfig();
  
  // Refresh the wizard
  openWizard('manageKeywords');
}

// Save keywords
async function saveKeywords() {
  const keywordCategories = wizardConfig.keywords ? Object.keys(wizardConfig.keywords) : [];
  
  keywordCategories.forEach(category => {
    const input = document.getElementById(`keywords_${category}`);
    if (input) {
      const value = input.value.trim();
      wizardConfig.keywords[category] = value ? value.split(',').map(k => k.trim()).filter(k => k) : [];
    }
  });
  
  await saveWizardConfig();
}

// Save wizard configuration
async function saveWizardConfig() {
  try {
    const response = await fetch(`${API_URL}/config/save`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(wizardConfig)
    });
    
    const data = await response.json();
    
    if (data.status === 'error') {
      alert('Error saving configuration: ' + data.error);
      return;
    }
    
    // Auto-activate the new configuration
    await fetch(`${API_URL}/config/activate/${data.filename}`, {
      method: 'POST',
      credentials: 'include'
    });
    
    alert('✓ Configuration saved and activated!');
    closeWizard();
    loadConfigSummary();
  } catch (error) {
    alert('Error saving configuration: ' + error.message);
  }
}

// Export jobs to CSV
async function exportJobsCSV() {
  try {
    console.log('Exporting jobs to CSV...');
    
    // Fetch CSV from API
    const response = await fetch(`${API_URL}/jobs/export`, {
      credentials: 'include'
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.statusText}`);
    }
    
    // Get the blob
    const blob = await response.blob();
    
    // Extract filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'freelance_jobs.csv';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    console.log('✓ CSV export successful:', filename);
  } catch (error) {
    console.error('Error exporting CSV:', error);
    alert('Failed to export CSV: ' + error.message);
  }
}

// Apply date filter
function applyDateFilter() {
  const select = document.getElementById('dateFilter');
  const value = select.value;
  
  // Update global filter variable
  dateFilterDays = value === '' ? null : parseInt(value);
  
  console.log('Date filter changed to:', dateFilterDays === null ? 'No filter' : `${dateFilterDays} days`);
  
  // Reload jobs with new filter
  loadJobs();
}
