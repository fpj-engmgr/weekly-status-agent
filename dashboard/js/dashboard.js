// Dashboard JavaScript - Loads and visualizes metrics

// Chart.js default configuration
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.plugins.legend.display = true;
Chart.defaults.plugins.legend.position = 'bottom';

// Color palette
const colors = {
    primary: '#667eea',
    secondary: '#764ba2',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
    purple: '#a855f7',
    pink: '#ec4899',
    cyan: '#06b6d4',
    teal: '#14b8a6'
};

const chartColors = [
    colors.primary, colors.success, colors.warning,
    colors.danger, colors.info, colors.purple,
    colors.pink, colors.cyan, colors.teal, colors.secondary
];

// Main initialization
async function initDashboard() {
    try {
        const data = await fetchMetrics();
        updateSummaryCards(data);
        createCharts(data);
        updatePackageTable(data);
        updateLastUpdated(data.generated_at);
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load metrics data');
    }
}

// Fetch metrics from JSON
async function fetchMetrics() {
    const response = await fetch('data/metrics.json');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
}

// Update summary cards
function updateSummaryCards(data) {
    const summary = data.summary;

    document.getElementById('totalIssues').textContent = summary.total.toLocaleString();
    document.getElementById('openIssues').textContent = summary.open.toLocaleString();
    document.getElementById('closedIssues').textContent = summary.closed.toLocaleString();
    document.getElementById('openPercentage').textContent = `${summary.open_percentage}%`;

    if (summary.avg_time_to_close_days !== undefined) {
        document.getElementById('avgResolutionTime').textContent =
            summary.avg_time_to_close_days.toFixed(1);
    } else {
        document.getElementById('avgResolutionTime').textContent = 'N/A';
    }
}

// Update last updated timestamp
function updateLastUpdated(timestamp) {
    const date = new Date(timestamp);
    const formatted = date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    document.getElementById('lastUpdated').textContent = `Last updated: ${formatted}`;
}

// Create all charts
function createCharts(data) {
    createTimelineChart(data.time_series);
    createStatusChart(data.distributions.by_status);
    createPriorityChart(data.distributions.by_priority);
    createPackagesChart(data.package_metrics.top_packages);
    createWorkloadChart(data.team_metrics.workload_distribution);
    createTypeChart(data.distributions.by_type);
    createComponentChart(data.distributions.by_component);
}

// Timeline Chart (Issues Created vs Closed)
function createTimelineChart(timeSeriesData) {
    const ctx = document.getElementById('timelineChart');

    const weeks = Object.keys(timeSeriesData.created_by_week);
    const created = Object.values(timeSeriesData.created_by_week);
    const closed = weeks.map(week => timeSeriesData.closed_by_week[week] || 0);

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: weeks.map(w => formatWeek(w)),
            datasets: [
                {
                    label: 'Issues Created',
                    data: created,
                    borderColor: colors.primary,
                    backgroundColor: colors.primary + '20',
                    tension: 0.3,
                    fill: true
                },
                {
                    label: 'Issues Closed',
                    data: closed,
                    borderColor: colors.success,
                    backgroundColor: colors.success + '20',
                    tension: 0.3,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Status Distribution Chart
function createStatusChart(statusData) {
    const ctx = document.getElementById('statusChart');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(statusData),
            datasets: [{
                data: Object.values(statusData),
                backgroundColor: chartColors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });
}

// Priority Distribution Chart
function createPriorityChart(priorityData) {
    const ctx = document.getElementById('priorityChart');

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(priorityData),
            datasets: [{
                data: Object.values(priorityData),
                backgroundColor: chartColors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });
}

// Top Packages Chart
function createPackagesChart(packagesData) {
    const ctx = document.getElementById('packagesChart');

    // Take top 15 packages
    const entries = Object.entries(packagesData).slice(0, 15);
    const labels = entries.map(([pkg]) => pkg);
    const values = entries.map(([, count]) => count);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Mentions',
                data: values,
                backgroundColor: colors.primary,
                borderColor: colors.primary,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Team Workload Chart
function createWorkloadChart(workloadData) {
    const ctx = document.getElementById('workloadChart');

    const entries = Object.entries(workloadData).slice(0, 10);
    const labels = entries.map(([assignee]) => truncateName(assignee));
    const values = entries.map(([, count]) => count);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Issues Assigned',
                data: values,
                backgroundColor: colors.info,
                borderColor: colors.info,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });
}

// Issue Type Chart
function createTypeChart(typeData) {
    const ctx = document.getElementById('typeChart');

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(typeData),
            datasets: [{
                data: Object.values(typeData),
                backgroundColor: chartColors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });
}

// Component Chart
function createComponentChart(componentData) {
    const ctx = document.getElementById('componentChart');

    new Chart(ctx, {
        type: 'pie',
        data: {
            labels: Object.keys(componentData),
            datasets: [{
                data: Object.values(componentData),
                backgroundColor: chartColors
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true
        }
    });
}

// Update package details table
function updatePackageTable(data) {
    const tbody = document.getElementById('packageTableBody');
    tbody.innerHTML = '';

    const packageDetails = data.package_metrics.package_details;

    for (const [pkg, details] of Object.entries(packageDetails)) {
        const row = tbody.insertRow();

        row.insertCell(0).textContent = pkg;
        row.insertCell(1).textContent = details.mention_count;
        row.insertCell(2).textContent = details.issue_count;

        const issuesCell = row.insertCell(3);
        issuesCell.textContent = details.sample_issues.join(', ');
        issuesCell.style.fontFamily = 'monospace';
        issuesCell.style.fontSize = '0.9em';
    }
}

// Helper Functions

function formatWeek(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function truncateName(name, maxLength = 25) {
    if (name.length <= maxLength) return name;
    return name.substring(0, maxLength - 3) + '...';
}

function showError(message) {
    const container = document.querySelector('.container');
    container.innerHTML = `
        <div class="loading">
            <h2>Error</h2>
            <p>${message}</p>
            <p>Please ensure metrics.json exists in the data/ folder.</p>
        </div>
    `;
}

// Initialize on load
document.addEventListener('DOMContentLoaded', initDashboard);
