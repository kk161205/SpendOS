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
  const [progress, setProgress] = useState(0);

  const pollIntervalRef = useRef(null);
  const progressIntervalRef = useRef(null);

  // cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        if (typeof pollIntervalRef.current.close === 'function') {
          pollIntervalRef.current.close();
        } else {
          clearInterval(pollIntervalRef.current);
        }
      }
      if (progressIntervalRef.current) clearInterval(progressIntervalRef.current);
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
      setProgress(5);
      
      // Simulated progress for the UI
      progressIntervalRef.current = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) return prev; // Cap at 90% until complete
          return prev + Math.floor(Math.random() * 5) + 2; // Add 2-6% randomly
        });
      }, 1000);

      const { task_id } = await procurementService.analyze(payload);
      
      const eventSource = procurementService.getAnalysisEventSource(task_id);
      pollIntervalRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const statusData = JSON.parse(event.data);
          
          if (statusData.error) {
            throw new Error(statusData.error);
          }

          setPollingStatus(statusData.status);
          
          if (statusData.status === 'completed') {
            eventSource.close();
            clearInterval(progressIntervalRef.current);
            setProgress(100);
            
            // Give the progress bar 500ms to show 100%
            setTimeout(() => {
              const results = statusData.result;
              const sessionId = addSession(results);
              navigate('/dashboard/results', { 
                state: { 
                  session: { 
                    id: sessionId, 
                    results, 
                    product_name: payload.product_name, 
                    category: payload.product_category 
                  } 
                } 
              });
              setIsSubmitting(false);
              setPollingStatus('');
              setProgress(0);
            }, 500);
          } else if (statusData.status === 'failed') {
            eventSource.close();
            clearInterval(progressIntervalRef.current);
            setError(statusData.error || statusData.result?.error || 'Analysis failed.');
            setIsSubmitting(false);
            setPollingStatus('');
            setProgress(0);
          }
        } catch (err) {
          eventSource.close();
          clearInterval(progressIntervalRef.current);
          setError(err.message || 'An error occurred during real-time status tracking.');
          setIsSubmitting(false);
          setPollingStatus('');
          setProgress(0);
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        clearInterval(progressIntervalRef.current);
        setError('Lost connection to analysis server. Please check your history in a few moments.');
        setIsSubmitting(false);
        setPollingStatus('');
        setProgress(0);
      };

    } catch (err) {
      clearInterval(progressIntervalRef.current);
      setError(err.message || err.detail || 'An error occurred during analysis. Please try again.');
      setIsSubmitting(false);
      setPollingStatus('');
      setProgress(0);
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
                disabled={isSubmitting}
                className={`input-field ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
                placeholder="e.g. Lithium Battery Pack 100Ah"
              />
            </div>

            <div>
              <label htmlFor="category" className="label-text">Category *</label>
              <select
                id="category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={isSubmitting}
                className={`input-field bg-white ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
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
                disabled={isSubmitting}
                className={`input-field ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
              />
            </div>

            <div className="sm:col-span-2">
              <label htmlFor="description" className="label-text">Detailed Description (Optional)</label>
              <textarea
                id="description"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isSubmitting}
                className={`input-field resize-none ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
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
                  disabled={isSubmitting}
                  className={`input-field pl-7 ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
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
                disabled={isSubmitting}
                className={`input-field ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
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
                    disabled={isSubmitting}
                    className={`inline-flex items-center px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      selectedCerts.includes(cert)
                        ? 'bg-brand-50 border-brand-200 text-brand-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    } ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
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
                  <input type="range" min="0" max="1" step="0.05" value={costWeight} onChange={(e) => setCostWeight(e.target.value)} disabled={isSubmitting} className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600 ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`} />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-sm font-medium text-gray-700">Reliability Focus ({relWeight})</label>
                  </div>
                  <input type="range" min="0" max="1" step="0.05" value={relWeight} onChange={(e) => setRelWeight(e.target.value)} disabled={isSubmitting} className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600 ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`} />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-sm font-medium text-gray-700">Risk Aversion Focus ({riskWeight})</label>
                  </div>
                  <input type="range" min="0" max="1" step="0.05" value={riskWeight} onChange={(e) => setRiskWeight(e.target.value)} disabled={isSubmitting} className={`w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-brand-600 ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`} />
                </div>
              </div>

              <div className={`mt-6 p-4 rounded-md border text-sm font-medium flex justify-between items-center ${isWeightValid ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
                <span>Total Weight Sum</span>
                <span className="text-lg">{weightSum} / 1.00</span>
              </div>
            </div>
          )}
        </div>

        {/* Progress Bar & Status (Visible during analysis) */}
        {isSubmitting && (
          <div className="glass-card p-6 sm:p-8 rounded-2xl border-brand-200 bg-brand-50/30 animate-fade-in">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-bold text-brand-800">
                {pollingStatus === 'pending' ? 'Initializing AI Agents...' : 
                 pollingStatus === 'processing' ? 'Evaluating Global Vendors...' : 
                 pollingStatus === 'completed' ? 'Finalizing Results...' : 'Analyzing...'}
              </span>
              <span className="text-sm font-medium text-brand-600">{progress}%</span>
            </div>
            <div className="w-full bg-brand-100 rounded-full h-2.5 overflow-hidden">
              <div 
                className="bg-brand-600 h-2.5 rounded-full transition-all duration-500 ease-out" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="mt-3 text-xs text-brand-600/70 text-center animate-pulse">
              This process may take 15-30 seconds as multiple specialized AI models orchestrate to bring you the best results.
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-4 pt-4">
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className={`btn-secondary ${isSubmitting ? 'opacity-50 cursor-not-allowed' : ''}`}
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
