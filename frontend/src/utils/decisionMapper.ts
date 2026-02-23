/**
 * Utility functions for mapping decision values between backend and display formats
 */

/**
 * Maps backend decision values to user-friendly display values
 * @param decision - Backend decision value (Selected, Review, Not Selected)
 * @returns Display value (Proceed, Review Required, Do Not Proceed)
 */
export function getDecisionDisplayValue(decision: string): string {
  const mapping: Record<string, string> = {
    'Selected': 'Proceed',
    'Review': 'Review Required',
    'Not Selected': 'Do Not Proceed',
  };
  
  return mapping[decision] || decision;
}

/**
 * Maps display values back to backend decision values
 * @param displayValue - Display value (Proceed, Review Required, Do Not Proceed)
 * @returns Backend decision value (Selected, Review, Not Selected)
 */
export function getDecisionBackendValue(displayValue: string): string {
  const mapping: Record<string, string> = {
    'Proceed': 'Selected',
    'Review Required': 'Review',
    'Do Not Proceed': 'Not Selected',
  };
  
  return mapping[displayValue] || displayValue;
}

