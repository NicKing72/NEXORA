export function reportBuilderIsBusy(...states: readonly unknown[]): boolean {
  return states.some((state) => state === true);
}
