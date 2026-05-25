// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    // --- DARK MODE ---
    const themeBtn = document.getElementById('themeToggleBtn');
    const currentTheme = localStorage.getItem('theme') || 'light';
    
    if (currentTheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        if(themeBtn) themeBtn.innerHTML = '<i class="fa-regular fa-sun"></i>';
    }

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            const isDark = document.body.getAttribute('data-theme') === 'dark';
            if (isDark) {
                document.body.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                themeBtn.innerHTML = '<i class="fa-regular fa-moon"></i>';
            } else {
                document.body.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeBtn.innerHTML = '<i class="fa-regular fa-sun"></i>';
            }
        });
    }

    // --- FAVORITES (Sevimlilar) ---
    const favCountSpan = document.getElementById('favCount');
    let favorites = JSON.parse(localStorage.getItem('favorites')) || [];

    window.toggleFav = function(btn) {
        const id = parseInt(btn.getAttribute('data-id'));
        if (favorites.includes(id)) {
            favorites = favorites.filter(favId => favId !== id);
        } else {
            favorites.push(id);
        }
        localStorage.setItem('favorites', JSON.stringify(favorites));
        updateFavUI();
    };

    function updateFavUI() {
        if (favCountSpan) favCountSpan.textContent = favorites.length;
        document.querySelectorAll('.fav-btn').forEach(btn => {
            const id = parseInt(btn.getAttribute('data-id'));
            if (favorites.includes(id)) {
                btn.classList.add('active');
                btn.innerHTML = '<i class="fa-solid fa-heart"></i>';
            } else {
                btn.classList.remove('active');
                btn.innerHTML = '<i class="fa-regular fa-heart"></i>';
            }
        });
    }
    
    updateFavUI();

    // Favorites Modal
    const modal = document.getElementById('favoritesModal');
    const openModalBtn = document.getElementById('openFavoritesBtn');
    const closeModalBtn = document.querySelector('.close-modal');
    const favList = document.getElementById('favoritesList');

    if (openModalBtn) {
        openModalBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            modal.style.display = 'flex';
            
            if (favorites.length === 0) {
                favList.innerHTML = '<div class="text-center p-5 text-muted"><i class="fa-regular fa-heart" style="font-size: 32px; margin-bottom: 10px;"></i><p>Saqlangan mashinalar yo\'q</p></div>';
                return;
            }

            favList.innerHTML = '<div class="text-center"><i class="fa-solid fa-spinner fa-spin"></i> Yuklanmoqda...</div>';
            
            const res = await fetch(`/api/cars?ids=${favorites.join(',')}`);
            const cars = await res.json();
            
            favList.innerHTML = cars.map(car => `
                <div class="modal-car-card">
                    <img src="${car.image}">
                    <div style="flex: 1;">
                        <h4 style="margin-bottom: 4px;">${car.brand} ${car.model}</h4>
                        <div class="text-primary font-weight-bold" style="font-size: 16px;">$${car.price.toLocaleString()}</div>
                        <button class="btn-outline mt-2 remove-fav-modal" data-id="${car.id}" style="padding: 4px 10px; font-size: 12px; border-color: var(--danger); color: var(--danger);">O'chirish</button>
                    </div>
                </div>
            `).join('');

            document.querySelectorAll('.remove-fav-modal').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = parseInt(e.target.getAttribute('data-id'));
                    favorites = favorites.filter(favId => favId !== id);
                    localStorage.setItem('favorites', JSON.stringify(favorites));
                    updateFavUI();
                    e.target.closest('.modal-car-card').remove();
                    if(favorites.length === 0) favList.innerHTML = '<div class="text-center p-5 text-muted">Saqlangan mashinalar yo\'q</div>';
                });
            });
        });
    }

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => modal.style.display = 'none');
    }
    window.addEventListener('click', (e) => {
        if (e.target == modal) modal.style.display = 'none';
    });

    // --- COMPARE ---
    const compareBtns = document.querySelectorAll('.compare-btn-add');
    let compareList = JSON.parse(localStorage.getItem('compare')) || [];

    compareBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const id = parseInt(btn.getAttribute('data-id'));
            if (!compareList.includes(id)) {
                if (compareList.length >= 2) {
                    alert('Solishtirish uchun faqat 2 ta mashina tanlash mumkin.');
                    return;
                }
                compareList.push(id);
                localStorage.setItem('compare', JSON.stringify(compareList));
                
                // Show success feedback
                const originalHtml = btn.innerHTML;
                btn.innerHTML = '<i class="fa-solid fa-check"></i> Qo\'shildi';
                btn.style.borderColor = 'var(--primary)';
                btn.style.color = 'var(--primary)';
                
                setTimeout(() => {
                    btn.innerHTML = originalHtml;
                    btn.style = '';
                }, 2000);
            } else {
                alert('Bu mashina ro\'yxatda bor!');
            }
        });
    });
});
