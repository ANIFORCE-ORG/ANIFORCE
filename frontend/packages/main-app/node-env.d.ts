declare module 'path' {
  export function resolve(...paths: string[]): string
}

declare const __dirname: string

declare const process: {
  env: Record<string, string | undefined>
}
