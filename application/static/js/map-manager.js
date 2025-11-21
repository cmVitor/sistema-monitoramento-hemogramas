/**
 * Map manager - Handles map initialization and data visualization
 */

import { CONFIG } from './config.js';

export class MapManager {
    constructor() {
        this.map = null;
        this.markersLayer = null;
        this.outbreakAreasLayer = null;
        this.allData = [];
        this.outbreakRegions = {};
        this.currentFilter = 'all';
    }

    /**
     * Initialize the Leaflet map
     */
    initialize() {
        // Initialize map
        this.map = L.map('map', {
            zoomControl: false,
            preferCanvas: true
        }).setView(CONFIG.MAP.center, CONFIG.MAP.zoom);

        // Add tile layer
        L.tileLayer(CONFIG.MAP.tileLayer, {
            attribution: '',
            maxZoom: CONFIG.MAP.maxZoom
        }).addTo(this.map);

        // Initialize layers
        this.markersLayer = L.layerGroup().addTo(this.map);
        this.outbreakAreasLayer = L.layerGroup().addTo(this.map);

        console.log('✓ Map initialized');
    }

    /**
     * Update map data
     */
    setData(observations, outbreaks) {
        this.allData = observations || [];
        this.outbreakRegions = outbreaks || {};
        this.updateMap();
    }

    /**
     * Set current filter
     */
    setFilter(filter) {
        this.currentFilter = filter;
        this.updateMap();
    }

    /**
     * Update map visualization
     */
    updateMap() {
        const filteredData = this.filterDataByIntensity(this.allData, this.currentFilter);

        // Clear old layers
        this.markersLayer.clearLayers();
        this.outbreakAreasLayer.clearLayers();

        // Group data by region
        const regionGroups = this.groupDataByRegion(filteredData);

        // Separate outbreak and normal data
        const outbreakData = [];
        const normalData = [];

        Object.entries(regionGroups).forEach(([region, data]) => {
            if (data.hasOutbreak) {
                outbreakData.push(...data.points);
            } else {
                normalData.push(...data.points);
            }
        });

        // Add markers for normal regions
        normalData.forEach(point => this.addNormalMarker(point));

        // Add outbreak areas and markers
        Object.entries(regionGroups).forEach(([region, data]) => {
            if (data.hasOutbreak) {
                this.addOutbreakArea(region, data.points);
            }
        });

        console.log(`Displaying ${filteredData.length} points (${outbreakData.length} in outbreaks, ${normalData.length} normal)`);
    }

    /**
     * Filter data by intensity
     */
    filterDataByIntensity(data, filter) {
        if (filter === 'all') return data;

        return data.filter(point => {
            const intensity = point.intensity;
            switch(filter) {
                case 'outbreak':
                    return point.region_outbreak === true;
                case 'low':
                    return intensity >= 0 && intensity < CONFIG.THRESHOLDS.low;
                case 'normal':
                    return intensity >= CONFIG.THRESHOLDS.low && intensity < CONFIG.THRESHOLDS.normal;
                case 'high':
                    return intensity >= CONFIG.THRESHOLDS.normal && intensity < CONFIG.THRESHOLDS.high;
                case 'critical':
                    return intensity >= CONFIG.THRESHOLDS.high;
                default:
                    return true;
            }
        });
    }

    /**
     * Group data by region
     */
    groupDataByRegion(data) {
        const regions = {};
        data.forEach(point => {
            const region = point.region;
            if (!regions[region]) {
                regions[region] = {
                    points: [],
                    hasOutbreak: false
                };
            }
            regions[region].points.push(point);
            if (point.region_outbreak) {
                regions[region].hasOutbreak = true;
            }
        });
        return regions;
    }

    /**
     * Get color by intensity
     */
    getColorByIntensity(intensity, isOutbreak = false) {
        if (isOutbreak) {
            return CONFIG.COLORS.outbreak;
        }

        if (intensity < CONFIG.THRESHOLDS.low) {
            return CONFIG.COLORS.low;
        } else if (intensity < CONFIG.THRESHOLDS.normal) {
            return CONFIG.COLORS.normal;
        } else if (intensity < CONFIG.THRESHOLDS.high) {
            return CONFIG.COLORS.high;
        } else {
            return CONFIG.COLORS.critical;
        }
    }

    /**
     * Get intensity level name
     */
    getIntensityLevel(intensity) {
        if (intensity < CONFIG.THRESHOLDS.low) return 'Normal';
        if (intensity < CONFIG.THRESHOLDS.normal) return 'Atenção';
        if (intensity < CONFIG.THRESHOLDS.high) return 'Alto';
        return 'Crítico';
    }

    /**
     * Add normal marker to map
     */
    addNormalMarker(point) {
        const markerColor = this.getColorByIntensity(point.intensity, false);
        const intensityLevel = this.getIntensityLevel(point.intensity);

        const marker = L.circleMarker([point.lat, point.lng], {
            radius: 6,
            fillColor: markerColor,
            color: '#ffffff',
            weight: 2,
            opacity: 0.9,
            fillOpacity: 0.8,
            className: 'normal-marker'
        });

        marker.bindPopup(`
            <div>
                <h4 class="popup-header" style="border-color: ${markerColor};">
                    Região ${point.region}
                </h4>
                <div class="popup-row">
                    <span class="popup-label">Status:</span>
                    <span class="status-badge status-normal">✓ Normal</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Leucócitos:</span>
                    <span class="popup-value">${point.intensity ? point.intensity.toLocaleString() : 'N/A'}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Nível:</span>
                    <span class="popup-value" style="color: ${markerColor}; font-weight: 800;">${intensityLevel}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Casos (7d):</span>
                    <span class="popup-value">${point.region_case_count || 0}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Última atualização:</span>
                    <span class="popup-value">${point.received_at ? new Date(point.received_at).toLocaleString('pt-BR') : 'N/A'}</span>
                </div>
            </div>
        `);

        marker.addTo(this.markersLayer);
    }

    /**
     * Add outbreak area to map
     */
    addOutbreakArea(region, points) {
        const outbreakInfo = this.outbreakRegions[region];
        if (!outbreakInfo) {
            console.warn(`Outbreak data not found for region ${region}`);
            return;
        }

        const centroid = outbreakInfo.centroid;
        const radius = outbreakInfo.radius;

        // Create outbreak circle
        const outbreakArea = L.circle([centroid.lat, centroid.lng], {
            radius: radius,
            fillColor: '#7c2d12',
            fillOpacity: 0.08,
            color: '#fbbf24',
            weight: 3,
            opacity: 0.8,
            dashArray: '10, 10',
            className: 'outbreak-area'
        });

        // Create region label
        const regionLabel = L.marker([centroid.lat, centroid.lng], {
            icon: L.divIcon({
                className: 'outbreak-label',
                html: `<div style="
                    background: rgba(124, 45, 18, 0.95);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 700;
                    font-size: 13px;
                    border: 3px solid #fbbf24;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                    white-space: nowrap;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                ">⚠️ SURTO - (${outbreakInfo.point_count} casos)</div>`,
                iconSize: [200, 40],
                iconAnchor: [100, 20]
            }),
            interactive: false
        });

        outbreakArea.addTo(this.outbreakAreasLayer);
        regionLabel.addTo(this.outbreakAreasLayer);

        // Add individual markers
        points.forEach(point => this.addOutbreakMarker(point));
    }

    /**
     * Add outbreak marker to map
     */
    addOutbreakMarker(point) {
        const markerColor = this.getColorByIntensity(point.intensity, false);
        const intensityLevel = this.getIntensityLevel(point.intensity);

        const marker = L.circleMarker([point.lat, point.lng], {
            radius: 8,
            fillColor: markerColor,
            color: '#ffffff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.9,
            className: 'outbreak-point'
        });

        marker.bindPopup(`
            <div>
                <h4 class="popup-header" style="border-color: #7c2d12; background: linear-gradient(135deg, rgba(124, 45, 18, 0.15), rgba(76, 29, 149, 0.1));">
                    ⚠️ Região ${point.region} - SURTO
                </h4>
                <div class="popup-row">
                    <span class="popup-label">Status da Região:</span>
                    <span class="status-badge status-outbreak">⚠️ SURTO ATIVO</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Leucócitos (este ponto):</span>
                    <span class="popup-value">${point.intensity ? point.intensity.toLocaleString() : 'N/A'}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Nível deste ponto:</span>
                    <span class="popup-value" style="color: ${markerColor}; font-weight: 800;">${intensityLevel}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Total de casos na região (7d):</span>
                    <span class="popup-value">${point.region_case_count || 0}</span>
                </div>
                <div class="popup-row">
                    <span class="popup-label">Última atualização:</span>
                    <span class="popup-value">${point.received_at ? new Date(point.received_at).toLocaleString('pt-BR') : 'N/A'}</span>
                </div>
            </div>
        `);

        marker.addTo(this.markersLayer);
    }
}
