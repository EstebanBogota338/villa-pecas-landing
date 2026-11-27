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
       Selector de idioma: recuerda la elección para la próxima visita
    ========================================================== */
    document.querySelectorAll('.lang-switch, .lang-menu-item').forEach((link) => {
        link.addEventListener('click', () => {
            try {
                localStorage.setItem('villapecas-lang', link.getAttribute('hreflang'));
            } catch (error) {
                /* Sin almacenamiento disponible el enlace funciona igual. */
            }
        });
    });


    /* =========================================================
       Carrusel de galería
       - el scroll lo hace el navegador (scroll-snap): fluido en móvil
       - las flechas van a un índice exacto, no suman píxeles
       - contador "3 / 7" y flechas desactivadas en los extremos
       - teclado: ← → Inicio Fin
    ========================================================== */
    document.querySelectorAll('.gallery-carousel').forEach((carousel) => {

        const track = carousel.querySelector('.gallery-track');
        const slides = track ? Array.from(track.querySelectorAll('.gallery-slide')) : [];
        const prevBtn = carousel.querySelector('.gallery-prev');
        const nextBtn = carousel.querySelector('.gallery-next');
        const counter = carousel.querySelector('.gallery-counter');

        if (!track || slides.length === 0) return;

        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        const lastIndex = slides.length - 1;

        let index = 0;
        let settleTimer = null;

        const maxScroll = () => Math.max(0, track.scrollWidth - track.clientWidth);

        /* Distancia, en píxeles de scroll, entre el inicio del track y el slide i. */
        const offsetOf = (i) => {
            const trackRect = track.getBoundingClientRect();
            const slideRect = slides[i].getBoundingClientRect();
            return slideRect.left - trackRect.left + track.scrollLeft;
        };

        /* Slide más cercano a la posición actual. */
        const currentIndex = () => {
            if (track.scrollLeft >= maxScroll() - 2) return lastIndex;

            let best = 0;
            let bestDistance = Infinity;

            slides.forEach((slide, i) => {
                const distance = Math.abs(offsetOf(i) - track.scrollLeft);
                if (distance < bestDistance) {
                    bestDistance = distance;
                    best = i;
                }
            });

            return best;
        };

        const sync = () => {
            if (counter) counter.textContent = `${index + 1} / ${slides.length}`;
            if (prevBtn) prevBtn.disabled = index === 0;
            if (nextBtn) nextBtn.disabled = index === lastIndex;
        };

        const goTo = (target) => {
            index = Math.min(Math.max(target, 0), lastIndex);

            track.scrollTo({
                left: Math.min(offsetOf(index), maxScroll()),
                behavior: reduceMotion.matches ? 'auto' : 'smooth'
            });

            sync();
        };

        if (prevBtn) prevBtn.addEventListener('click', () => goTo(index - 1));
        if (nextBtn) nextBtn.addEventListener('click', () => goTo(index + 1));

        /* Si el usuario arrastra con el dedo o la rueda, el contador se
           actualiza cuando el scroll se detiene (no en cada frame). */
        track.addEventListener('scroll', () => {
            clearTimeout(settleTimer);
            settleTimer = setTimeout(() => {
                index = currentIndex();
                sync();
            }, 120);
        }, { passive: true });

        track.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowRight') {
                event.preventDefault();
                goTo(index + 1);
            } else if (event.key === 'ArrowLeft') {
                event.preventDefault();
                goTo(index - 1);
            } else if (event.key === 'Home') {
                event.preventDefault();
                goTo(0);
            } else if (event.key === 'End') {
                event.preventDefault();
                goTo(lastIndex);
            }
        });

        sync();
    });


    /* =========================================================
       Animación de secciones al hacer scroll
    ========================================================== */

    const sections = document.querySelectorAll('section');

    const observer = new IntersectionObserver((entries) => {

        entries.forEach((entry) => {

            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }

        });

    }, {
        threshold: 0.15
    });

    sections.forEach((section) => {
        observer.observe(section);
    });

    // Cerrar menú al hacer clic en el botón "RESERVAR" (navbar)
    document.querySelector('.nav-button')?.addEventListener('click', () => {
        if (navToggle) navToggle.checked = false;
    });

});
