function updateRelativeTimes() {
    const timeElements = document.querySelectorAll('.relative-time');
    
    timeElements.forEach(element => {
        const timestamp = element.getAttribute('data-timestamp');
        const date = new Date(timestamp);
        const now = new Date();
        const diffSeconds = Math.floor((now - date) / 1000);

        let timeString;
        if (diffSeconds < 60) {
            timeString = 'Just now';
        } else if (diffSeconds < 3600) {
            const minutes = Math.floor(diffSeconds / 60);
            timeString = `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else if (diffSeconds < 86400) {
            const hours = Math.floor(diffSeconds / 3600);
            timeString = `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else if (diffSeconds < 604800) {
            const days = Math.floor(diffSeconds / 86400);
            timeString = `${days} day${days > 1 ? 's' : ''} ago`;
        } else {
            timeString = timestamp.split(' ')[0]; // Show just the date part
        }

        element.textContent = timeString;
    });
}

// Update times immediately and then every minute
document.addEventListener('DOMContentLoaded', () => {
    updateRelativeTimes();
    setInterval(updateRelativeTimes, 60000);
});