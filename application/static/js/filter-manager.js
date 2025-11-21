/**
 * Filter manager - Handles filter interactions
 */

export class FilterManager {
    constructor(onFilterChange) {
        this.onFilterChange = onFilterChange;
        this.currentFilter = 'all';
    }

    /**
     * Initialize filter event listeners
     */
    initialize() {
        const filterOptions = document.querySelectorAll('.filter-option');

        filterOptions.forEach(option => {
            option.addEventListener('click', () => {
                // Update UI
                filterOptions.forEach(opt => opt.classList.remove('active'));
                option.classList.add('active');
                option.querySelector('input[type="radio"]').checked = true;

                // Update filter
                this.currentFilter = option.dataset.filter;

                // Notify callback
                if (this.onFilterChange) {
                    this.onFilterChange(this.currentFilter);
                }
            });
        });

        console.log('✓ Filters initialized');
    }

    /**
     * Get current filter
     */
    getCurrentFilter() {
        return this.currentFilter;
    }
}
