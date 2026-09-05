/**
 * SignalGraph — Fixed Demo Instrument Universe
 * ==============================================
 * Mirrors backend/app/main.py's SEED_INSTRUMENTS exactly (ExecPlan
 * Context and Orientation — twenty NSE stocks across five sectors).
 * There is no /api/instruments endpoint (see ExecPlan Interfaces and
 * Dependencies), so the fixed universe is hardcoded here rather than
 * fetched, matching the "fixed, not dynamic" decision for this project.
 */

export const INSTRUMENTS = [
  { ticker: 'TCS.NS', name: 'Tata Consultancy Services', sector: 'Information Technology' },
  { ticker: 'INFY.NS', name: 'Infosys', sector: 'Information Technology' },
  { ticker: 'WIPRO.NS', name: 'Wipro', sector: 'Information Technology' },
  { ticker: 'HCLTECH.NS', name: 'HCL Technologies', sector: 'Information Technology' },
  { ticker: 'TECHM.NS', name: 'Tech Mahindra', sector: 'Information Technology' },
  { ticker: 'HDFCBANK.NS', name: 'HDFC Bank', sector: 'Banking' },
  { ticker: 'ICICIBANK.NS', name: 'ICICI Bank', sector: 'Banking' },
  { ticker: 'SBIN.NS', name: 'State Bank of India', sector: 'Banking' },
  { ticker: 'KOTAKBANK.NS', name: 'Kotak Mahindra Bank', sector: 'Banking' },
  { ticker: 'AXISBANK.NS', name: 'Axis Bank', sector: 'Banking' },
  { ticker: 'RELIANCE.NS', name: 'Reliance Industries', sector: 'Energy and Utilities' },
  { ticker: 'ONGC.NS', name: 'Oil and Natural Gas Corp', sector: 'Energy and Utilities' },
  { ticker: 'NTPC.NS', name: 'NTPC Limited', sector: 'Energy and Utilities' },
  { ticker: 'POWERGRID.NS', name: 'Power Grid Corp', sector: 'Energy and Utilities' },
  { ticker: 'HINDUNILVR.NS', name: 'Hindustan Unilever', sector: 'Consumer Goods' },
  { ticker: 'ITC.NS', name: 'ITC Limited', sector: 'Consumer Goods' },
  { ticker: 'NESTLEIND.NS', name: 'Nestle India', sector: 'Consumer Goods' },
  { ticker: 'TMPV.NS', name: 'Tata Motors Passenger Vehicles', sector: 'Automotive' },
  { ticker: 'MARUTI.NS', name: 'Maruti Suzuki', sector: 'Automotive' },
  { ticker: 'M&M.NS', name: 'Mahindra & Mahindra', sector: 'Automotive' },
];

export const SECTORS = [...new Set(INSTRUMENTS.map((i) => i.sector))];
