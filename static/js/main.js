/* Main JavaScript file for PDF Parser application */

// Helper function for showing notifications
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show notification-toast`;
    
    // Add content
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to page
    const container = document.createElement('div');
    container.className = 'notification-container';
    container.appendChild(notification);
    document.body.appendChild(container);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            if (container && container.parentNode) {
                container.parentNode.removeChild(container);
            }
        }, 500);
    }, 5000);
}

// Add general event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                const target = document.querySelector(targetId);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
    
    // Fix for footer position on short pages
    const body = document.body;
    const html = document.documentElement;
    
    function adjustFooter() {
        const height = Math.max(
            body.scrollHeight, body.offsetHeight,
            html.clientHeight, html.scrollHeight, html.offsetHeight
        );
        const windowHeight = window.innerHeight;
        
        const footer = document.querySelector('footer');
        if (footer) {
            if (height < windowHeight) {
                footer.classList.add('fixed-bottom');
            } else {
                footer.classList.remove('fixed-bottom');
            }
        }
    }
    
    adjustFooter();
    window.addEventListener('resize', adjustFooter);
});
