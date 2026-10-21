/** Set the default before loading React, its JSX runtime, or Ink's reconciler. */
export async function loadSonarUi() {
  process.env.NODE_ENV ||= 'production';
  const [ink, react, app] = await Promise.all([import('ink'), import('react'), import('./app.js')]);
  return { render: ink.render, createElement: react.createElement, SonarApp: app.SonarApp };
}
