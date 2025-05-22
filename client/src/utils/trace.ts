/**
 * Utility for generating and managing trace IDs
 */

/**
 * Generate a UUID v4 trace ID
 * @returns A unique trace ID string
 */
export const generateTraceId = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

/**
 * Get the current trace ID or generate a new one
 * @returns The current trace ID
 */
export const getTraceId = (): string => {
  const storedTraceId = sessionStorage.getItem('current_trace_id');
  if (storedTraceId) {
    return storedTraceId;
  }
  const newTraceId = generateTraceId();
  sessionStorage.setItem('current_trace_id', newTraceId);
  return newTraceId;
};

/**
 * Clear the current trace ID
 */
export const clearTraceId = (): void => {
  sessionStorage.removeItem('current_trace_id');
}; 