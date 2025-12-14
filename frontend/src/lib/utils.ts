export function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
