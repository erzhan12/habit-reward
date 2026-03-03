/**
 * Lightweight particle burst effect.
 *
 * Creates a temporary fullscreen canvas, spawns particles with velocity,
 * gravity and fade, then removes the canvas. No dependencies.
 */

/**
 * Spawn particles at a given position.
 *
 * @param {{ x: number, y: number, count?: number, colors?: string[],
 *           duration?: number }} opts
 * @returns {Promise<void>} Resolves when animation completes
 */
export function spawnParticles({
  x,
  y,
  count = 12,
  colors = ['#fbbf24', '#10b981', '#06b6d4', '#ec4899'],
  duration = 600,
}) {
  return new Promise((resolve) => {
    const canvas = document.createElement('canvas');
    canvas.style.cssText =
      'position:fixed;top:0;left:0;width:100vw;height:100vh;pointer-events:none;z-index:9999';
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const particles = [];

    for (let i = 0; i < count; i++) {
      const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.5;
      const speed = 120 + Math.random() * 180;
      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        radius: 3 + Math.random() * 3,
        color: colors[i % colors.length],
        life: 1,
      });
    }

    const startTime = performance.now();
    const gravity = 300;

    function frame(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const dt = 1 / 60; // fixed timestep for smooth animation

      for (const p of particles) {
        p.vy += gravity * dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.life = 1 - progress;

        ctx.globalAlpha = p.life;
        ctx.fillStyle = p.color;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * p.life, 0, Math.PI * 2);
        ctx.fill();
      }

      if (progress < 1) {
        requestAnimationFrame(frame);
      } else {
        canvas.remove();
        resolve();
      }
    }

    requestAnimationFrame(frame);
  });
}
