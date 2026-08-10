document.addEventListener('DOMContentLoaded', () => {

    /* =========================================================
       Cerrar el menú móvil al hacer clic en un link
    ========================================================== */
    const navToggle = document.getElementById('nav-toggle');

    document.querySelectorAll('.nav-menu a').forEach((link) => {
        link.addEventListener('click', () => {
            if (navToggle) navToggle.checked = false;
        });
    });


    /* =========================================================
       Carrusel de galería (flechas prev/next)
    ========================================================== */
    document.querySelectorAll('.gallery-carousel').forEach((carousel) => {

        const track = carousel.querySelector('.gallery-track');
        const prevBtn = carousel.querySelector('.gallery-prev');
        const nextBtn = carousel.querySelector('.gallery-next');

        if (!track || !prevBtn || !nextBtn) return;

        const getScrollAmount = () => {
            const slide = track.querySelector('.gallery-slide');
            if (!slide) return track.clientWidth;

            const trackStyle = getComputedStyle(track);
            const gap = parseFloat(trackStyle.columnGap || trackStyle.gap || '0');

            return slide.getBoundingClientRect().width + gap;
        };

        prevBtn.addEventListener('click', () => {
            track.scrollBy({ left: -getScrollAmount(), behavior: 'smooth' });
        });

        nextBtn.addEventListener('click', () => {
            track.scrollBy({ left: getScrollAmount(), behavior: 'smooth' });
        });

    });

});