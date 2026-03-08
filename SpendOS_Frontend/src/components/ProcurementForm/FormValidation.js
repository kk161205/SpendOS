export const validateWeights = (cost, reliability, risk) => {
  const sum = parseFloat(cost) + parseFloat(reliability) + parseFloat(risk);
  // Allow a small floating point margin of error
  return Math.abs(sum - 1.0) < 0.01;
};

export const validateProductName = (name) => {
  if (!name || name.trim().length < 2) return 'Product name must be at least 2 characters';
  if (name.length > 255) return 'Product name must be less than 255 characters';
  return null;
};

export const validateBudget = (budget) => {
  if (budget && parseFloat(budget) <= 0) return 'Budget must be greater than 0';
  return null;
};

export const validateQuantity = (quantity) => {
  if (!quantity || parseInt(quantity) <= 0) return 'Quantity must be at least 1';
  return null;
};

export const CATEGORIES = [
  'Electronics',
  'Raw Materials',
  'Software',
  'Services',
  'Hardware',
  'Office Supplies',
  'Machinery',
  'Other'
];

export const CERTIFICATIONS = [
  'ISO 9001',
  'ISO 14001',
  'ISO 27001',
  'CE',
  'RoHS',
  'FCC',
  'UL',
  'Energy Star'
];
