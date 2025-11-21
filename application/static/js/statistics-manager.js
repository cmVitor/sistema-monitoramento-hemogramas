/**
 * Statistics manager - Handles statistics display
 */

export class StatisticsManager {
    /**
     * Update statistics display
     */
    update(data) {
        const totalCases = data.length;
        const outbreakRegions = new Set(data.filter(p => p.region_outbreak).map(p => p.region));
        const outbreakCount = outbreakRegions.size;
        const criticalCases = data.filter(p => p.intensity >= 15000).length;
        const avgIntensity = data.length > 0 ?
            (data.reduce((sum, p) => sum + p.intensity, 0) / data.length).toFixed(0) : 0;

        // Update DOM
        document.getElementById('total-cases').textContent = totalCases.toLocaleString();
        document.getElementById('outbreak-count').textContent = outbreakCount;
        document.getElementById('critical-cases').textContent = criticalCases;
        document.getElementById('avg-intensity').textContent = avgIntensity;

        // Show/hide outbreak alert
        const outbreakAlert = document.getElementById('outbreak-alert');
        if (outbreakCount > 0) {
            outbreakAlert.style.display = 'flex';
            document.getElementById('outbreak-regions').textContent = outbreakCount;
        } else {
            outbreakAlert.style.display = 'none';
        }
    }
}
