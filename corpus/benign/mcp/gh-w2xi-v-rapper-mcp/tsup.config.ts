import { defineConfig } from 'tsup'

export default defineConfig({
  entry: ['cli.ts'],
  format: ['esm'],
  clean: true,
  splitting: true,
  treeshake: true,
  target: 'es2022',
  minify: true,
  platform: 'node',
})
