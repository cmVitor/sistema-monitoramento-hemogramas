/**
 * UI utilities - Helper functions for UI interactions
 */

export class UIUtils {
    /**
     * Toggle section collapse
     */
    static toggleSection(sectionId) {
        const section = document.getElementById(sectionId);
        const button = section.previousElementSibling.querySelector('.toggle-btn');

        section.classList.toggle('collapsed');
        button.textContent = section.classList.contains('collapsed') ? '+' : '−';
    }

    /**
     * Request notification permission
     */
    static async requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('✓ Notifications enabled');
            }
        }
    }

    /**
     * Show browser notification
     */
    static showNotification(title, body, icon = null) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body,
                icon,
                requireInteraction: true
            });
        }
    }
}

// Make toggleSection available globally for inline onclick handlers
window.toggleSection = UIUtils.toggleSection;
