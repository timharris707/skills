"use client";

/**
 * The lamp the chart is read under.
 *
 * There is deliberately no React state here. The theme lives in exactly two
 * places — `data-theme` on <html> and localStorage — both set before first
 * paint by the inline script in the root layout. A state hook would be a
 * second, later, disagreeing source of truth, and would decide the glyph one
 * frame too late; which glyph shows is settled in CSS instead.
 */
export default function ThemeToggle() {
  function toggle() {
    const root = document.documentElement;
    const pinned = root.dataset.theme;
    const lit =
      pinned === "dark" ||
      (pinned !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = lit ? "light" : "dark";

    root.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Private browsing refuses the write. The choice still holds for this
      // page; it just will not survive the next one.
    }
  }

  return (
    <button
      type="button"
      className="lamp"
      onClick={toggle}
      title="Light / dark"
      aria-label="Switch between the light and dark theme"
    >
      <svg
        className="lamp__day"
        viewBox="0 0 24 24"
        width="15"
        height="15"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="4.2" />
        <path d="M12 2.6v2.2M12 19.2v2.2M21.4 12h-2.2M4.8 12H2.6M18.6 5.4 17 7M7 17l-1.6 1.6M18.6 18.6 17 17M7 7 5.4 5.4" />
      </svg>

      <svg
        className="lamp__night"
        viewBox="0 0 24 24"
        width="15"
        height="15"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M20.5 14.6A8.6 8.6 0 0 1 9.4 3.5a8.6 8.6 0 1 0 11.1 11.1Z" />
      </svg>
    </button>
  );
}
