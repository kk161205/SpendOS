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
  if (!budget) return 'Max Budget is required for procurement analysis';
  if (parseFloat(budget) <= 0) return 'Budget must be greater than 0';
  return null;
};

export const validateDeadline = (deadline) => {
  if (!deadline) return 'Delivery Deadline is required for procurement analysis';
  if (parseInt(deadline) <= 0) return 'Deadline must be at least 1 day';
  return null;
};

export const validateQuantity = (quantity) => {
  if (!quantity || parseInt(quantity) <= 0) return 'Quantity must be at least 1';
  return null;
};

export const validateShippingDestination = (dest) => {
  if (!dest || dest.trim().length < 2) return 'Shipping destination (Country/City) is required';
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
export const PAYMENT_TERMS = [
  'Net 30',
  'Net 60',
  'Net 90',
  'Cash Against Documents',
  'Letter of Credit',
  '100% Advance',
  '50% Advance / 50% on Delivery'
];

export const INCOTERMS = [
  'EXW (Ex Works)',
  'FOB (Free on Board)',
  'CIF (Cost, Insurance & Freight)',
  'DDP (Delivered Duty Paid)',
  'FCA (Free Carrier)',
  'CIP (Carriage and Insurance Paid)'
];

export const REGIONS = [
  'No Preference',
  'North America',
  'Europe',
  'Asia',
  'South America',
  'Africa',
  'Oceania',
  'Domestic (Same Country)'
];
