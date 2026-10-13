async function updatePendingBadge() {
    const badge = document.getElementById('pending-badge');

    if (!badge) {
        console.log('Badge element not found');
        return;
    }

    try {
        const response = await fetch('/admin/pending-count');

        if (!response.ok) {
            console.log('Request failed:', response.status);
            return;
        }

        const data = await response.json();

        console.log('Pending count:', data.pending_count);

        badge.textContent = data.pending_count;
        badge.style.display = data.pending_count > 0 ? 'inline-flex' : 'none';
    } catch (error) {
        console.error('Failed to update pending count:', error);
    }
}

updatePendingBadge();
setInterval(updatePendingBadge, 30000);