import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../../context/SessionContext';
import { procurementService } from '../../services/procurementService';
import { validateWeights, validateProductName, validateBudget, validateQuantity, CATEGORIES, CERTIFICATIONS } from './FormValidation';
import { AlertCircle, ArrowRight, Settings, Package, Sliders, Target } from 'lucide-react';

export default function ProcurementForm() {
  const navigate = useNavigate();
  const { addSession } = useSession();

  // Basic Details
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [description, setDescription] = useState('');

  // Parameters
  const [quantity, setQuantity] = useState('1');
  const [budget, setBudget] = useState('');
  const [selectedCerts, setSelectedCerts] = useState([]);
  const [deadline, setDeadline] = useState('');

  // Weights
  const [costWeight, setCostWeight] = useState(0.35);
  const [relWeight, setRelWeight] = useState(0.40);
  const [riskWeight, setRiskWeight] = useState(0.25);
  
  // UI State
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showWeights, setShowWeights] = useState(false);
  const [pollingStatus, setPollingStatus] = useState('');

  const pollIntervalRef = useRef(null);

  // cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleCertToggle = (cert) => {
    setSelectedCerts(prev => 
      prev.includes(cert) ? prev.filter(c => c !== cert) : [...prev, cert]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validations
    const nameErr = validateProductName(productName);
    const qtyErr = validateQuantity(quantity);
    const bdgErr = validateBudget(budget);
    
    if (nameErr || qtyErr || bdgErr) {
      setError(nameErr || qtyErr || bdgErr);
      return;
    }

    if (!validateWeights(costWeight, relWeight, riskWeight)) {
      setError('Scoring weights must sum up exactly to 1.0');
      setShowWeights(true);
      return;
    }

    setIsSubmitting(true);

    const payload = {
      product_name: productName.trim(),
      product_category: category,
      description: description.trim() || undefined,
      quantity: parseInt(quantity, 10),
      budget_usd: budget ? parseFloat(budget) : undefined,
      required_certifications: selectedCerts.length > 0 ? selectedCerts : undefined,
      delivery_deadline_days: deadline ? parseInt(deadline, 10) : undefined,
      scoring_weights: {
        cost_weight: parseFloat(costWeight),
        reliability_weight: parseFloat(relWeight),
        risk_weight: parseFloat(riskWeight)
      }
    };

    try {
      setPollingStatus('pending');
      const { task_id } = await procurementService.analyze(payload);
      
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusData = await procurementService.getAnalysisStatus(task_id);
          setPollingStatus(statusData.status);
          
          if (statusData.status === 'completed') {
            clearInterval(pollIntervalRef.current);
            const results = statusData.result;
            const sessionId = addSession(results);
            navigate('/dashboard/results', { state: { session: { id: sessionId, results, product_name: payload.product_name, category: payload.product_category } } });
            setIsSubmitting(false);
            setPollingStatus('');
          } else if (statusData.status === 'failed') {
            clearInterval(pollIntervalRef.current);
            setError(statusData.result?.error || 'Analysis failed.');
            setIsSubmitting(false);
            setPollingStatus('');
          }
        } catch (pollErr) {
          clearInterval(pollIntervalRef.current);
          setError(pollErr.message || pollErr.detail || 'An error occurred while checking status.');
          setIsSubmitting(false);
          setPollingStatus('');
        }
      }, 3000);

    } catch (err) {
      setError(err.message || err.detail || 'An error occurred during analysis. Please try again.');
      setIsSubmitting(false);
      setPollingStatus('');
    }
  };

  const weightSum = (parseFloat(costWeight) + parseFloat(relWeight) + parseFloat(riskWeight)).toFixed(2);
  const isWeightValid = validateWeights(costWeight, relWeight, riskWeight);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center">
          <Target className="w-6 h-6 mr-2 text-brand-600" /> New Procurement Analysis
        </h1>
        <p className="mt-1 text-sm text-gray-500">Provide the details of your sourcing requirements and let our AI discover, evaluate, and rank the best vendors globally.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        
        {/* Error State */}
        {error && (
          <div className="rounded-md bg-red-50 p-4 border border-red-100 flex items-start animate-fade-in">
            <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
            <div className="ml-3 text-sm text-red-700 font-medium">{error}</div>
          </div>
        )}

        {/* Section 1: Product Details */}
        <div className="glass-card p-6 sm:p-8 rounded-2xl">
          <h2 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-3 mb-5 flex items-center">
            <Package className="w-5 h-5 mr-2 text-gray-400" /> Product Information
          </h2>
          
          <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label htmlFor="productName" className="label-text">Product Name *</label>
              <input
                id="productName"
                type="text"
                required
                value={productName}
                onChange={(e) => setProductName(e.target.value)}
                className="input-field"
                placeholder="e.g. Lithium Battery Pack 100Ah"
              />
            </div>

            <div>
              <label htmlFor="category" className="label-text">Category *</label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input-field bg-white"
              >
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>

            <div>
              <label htmlFor="quantity" className="label-text">Order Quantity *</label>
              <input
                id="quantity"
                type="number"
                min="1"
                required
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="input-field"
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="description" className="label-text">Detailed Description (Optional)</label>
              <textarea
                id="description"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="input-field resize-none"
                placeholder="Include technical specs, physical dimensions, or special material requirements that vendors should meet."
              />
            </div>
          </div>
        </div>

        {/* Section 2: Parameters */}
        <div className="glass-card p-6 sm:p-8 rounded-2xl">
          <h2 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-3 mb-5 flex items-center">
            <Settings className="w-5 h-5 mr-2 text-gray-400" /> Sourcing Constraints
          </h2>
          
          <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-2">
            <div>
              <label htmlFor="budget" className="label-text">Max Budget (USD, Optional)</label>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <span className="text-gray-500 sm:text-sm">$</span>
                </div>
                <input
                  id="budget"
                  type="number"
                  min="0"
                  step="0.01"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="input-field pl-7"
                  placeholder="50000"
                />
              </div>
            </div>

            <div>
              <label htmlFor="deadline" className="label-text">Max Delivery Time (Days, Optional)</label>
              <input
                id="deadline"
                type="number"
                min="1"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                className="input-field"
                placeholder="30"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="label-text mb-2">Required Certifications (Optional)</label>
              <div className="flex flex-wrap gap-2">
                {CERTIFICATIONS.map(cert => (
                  <button
                    key={cert}
                    type="button"
                    onClick={() => handleCertToggle(cert)}
                    className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      selectedCerts.includes(cert)
                        ? 'bg-brand-50 border-brand-200 text-brand-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {cert}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Weights */}
        <div className="glass-card p-6 sm:p-8 rounded-2xl overflow-hidden transition-all duration-300">
          <button 
            type="button"
            onClick={() => setShowWeights(!showWeights)}
            className="w-full text-left flex justify-between items-center group focus:outline-none"
          >
            <h2 className="text-lg font-bold text-gray-900 flex items-center">
              <Sliders className="w-5 h-5 mr-2 text-gray-400 group-hover:text-brand-500 transition-colors" /> 
              Scoring Weights Configuration
            </h2>
            <span className="text-sm font-medium text-brand-600 border border-brand-200 bg-brand-50 px-2 py-1 rounded hidden sm:block">
              {showWeights ? 'Hide Settings' : 'Customize Priorities'}
            </span>
          </button>
          
          {showWeights && (
            <div className="mt-6 border-t border-gray-100 pt-5 animate-fade-in">
              <p className="text-sm text-gray-500 mb-6">Modify the importance of each factor for the final score. The total must equal exactly 1.00.</p>
              
              <div className="space-y-5 max-w-2xl">
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-sm font-medium text-gray-700">Cost Focus ({costWeight})</label>
                  </div>
                  <input type="range" min="0" max="1" step="0.05" value={costWeight} onChange={(e) => setCostWeight(e.target.value)} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-sm font-medium text-gray-700">Reliability Focus ({relWeight})</label>
                  </div>
                  <input type="range" min="0" max="1" step="0.05" value={relWeight} onChange={(e) => setRelWeight(e.target.value)} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-sm font-medium text-gray-700">Risk Aversion Focus ({riskWeight})</label>
                  </div>
                  <input type="range" min="0" max="1" step="0.05" value={riskWeight} onChange={(e) => setRiskWeight(e.target.value)} className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600" />
                </div>
              </div>

              <div className={`mt-6 p-4 rounded-md border text-sm font-medium flex justify-between items-center ${isWeightValid ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                <span>Total Weight Sum</span>
                <span className="text-lg">{weightSum} / 1.00</span>
              </div>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-4 pt-4">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="btn-secondary"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary space-x-2 group relative overflow-hidden px-6"
          >
            {isSubmitting ? (
              <span className="flex items-center">
                <div className="w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                {pollingStatus ? `Analyzing (${pollingStatus})...` : 'Starting Analysis...'}
              </span>
            ) : (
              <span className="flex items-center">
                Commence Analysis
                <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
              </span>
            )}
            
            {/* Subtle sweep animation layer */}
            {!isSubmitting && (
              <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent group-hover:animate-shimmer" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
