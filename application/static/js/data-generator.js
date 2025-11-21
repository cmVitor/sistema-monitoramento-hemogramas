/**
 * Data generator - Handles synthetic data generation
 */

import { CONFIG } from './config.js';

export class DataGenerator {
    constructor(onStatusChange) {
        this.onStatusChange = onStatusChange;
    }

    /**
     * Initialize modal and button event listeners
     */
    initialize() {
        const modal = document.getElementById('generateModal');

        // Button click
        document.getElementById('generateBtn').addEventListener('click', () => {
            this.openModal();
        });

        // Close modal when clicking outside
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                this.closeModal();
            }
        });

        // Close button
        document.querySelector('.modal-close').addEventListener('click', () => {
            this.closeModal();
        });

        // Option clicks
        document.querySelectorAll('.modal-option').forEach(option => {
            option.addEventListener('click', () => {
                const count = parseInt(option.dataset.count);
                if (count) {
                    this.generateData(count);
                }
            });
        });

        console.log('✓ Data generator initialized');
    }

    /**
     * Open modal
     */
    openModal() {
        document.getElementById('generateModal').classList.add('active');
    }

    /**
     * Close modal
     */
    closeModal() {
        document.getElementById('generateModal').classList.remove('active');
    }

    /**
     * Show status message
     */
    showStatus(title, text, type = 'info') {
        const messageEl = document.getElementById('statusMessage');
        messageEl.innerHTML = `
            <div class="status-title">${title}</div>
            <div class="status-text">${text}</div>
        `;
        messageEl.className = `status-message active ${type}`;

        // Auto-hide after 10 seconds for success
        if (type === 'success') {
            setTimeout(() => {
                messageEl.classList.remove('active');
            }, 10000);
        }
    }

    /**
     * Generate synthetic data
     */
    async generateData(count) {
        this.closeModal();

        const generateBtn = document.getElementById('generateBtn');
        generateBtn.disabled = true;
        generateBtn.classList.add('loading');

        this.showStatus(
            'Gerando Dados...',
            `Gerando ${count} hemogramas em tempo real. Isso levará alguns minutos. Acompanhe o mapa para ver os dados aparecendo!`,
            'info'
        );

        console.log(`Starting generation of ${count} hemograms...`);

        try {
            const response = await fetch(`${CONFIG.API.seedData}?count=${count}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }

            const data = await response.json();
            console.log('Data generated successfully:', data);

            this.showStatus(
                'Dados Gerados com Sucesso!',
                `${data.inserted_count} hemogramas foram gerados. ${data.alerts_created} alerta(s) criado(s).`,
                'success'
            );

            // Notify callback
            if (this.onStatusChange) {
                this.onStatusChange('generated', data);
            }

        } catch (error) {
            console.error('Error generating data:', error);
            this.showStatus(
                'Erro ao Gerar Dados',
                `Ocorreu um erro: ${error.message}. Verifique se o servidor está rodando.`,
                'error'
            );
        } finally {
            generateBtn.disabled = false;
            generateBtn.classList.remove('loading');
        }
    }
}
