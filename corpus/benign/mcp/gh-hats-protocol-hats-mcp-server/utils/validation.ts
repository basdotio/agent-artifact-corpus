// Validation for Ethereum addresses
export const addressRegex = /^0x[a-fA-F0-9]{40}$/;
export const isValidAddress = (value: string) => addressRegex.test(value);

// Add other common validation patterns here as needed
