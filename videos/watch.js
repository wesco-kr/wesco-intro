// Preserve a chapter deep link when loading the embedded YouTube player.
(() => {
  const raw = new URLSearchParams(window.location.search).get('t');
  const player = document.querySelector('iframe[data-duration]');
  if (!player || !raw || !/^\d+$/.test(raw)) return;
  const seconds = Number(raw);
  if (seconds < 0 || seconds >= Number(player.dataset.duration)) return;
  const source = new URL(player.src);
  source.searchParams.set('start', String(seconds));
  player.src = source.toString();
})();
