import { useState, useEffect } from 'react';
import { fetchConfig, updateConfig, testConnection, fetchProviders } from '../api';

export default function SettingsPanel({ isOpen, onClose }) {
  const [config, setConfig] = useState(null);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState(null);
  const [errors, setErrors] = useState({});

  // Form state
  const [llmProvider, setLlmProvider] = useState('anthropic');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [searchApiKey, setSearchApiKey] = useState('');
  const [jsearchApiKey, setJsearchApiKey] = useState('');
  const [adzunaAppId, setAdzunaAppId] = useState('');
  const [adzunaAppKey, setAdzunaAppKey] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadConfig();
      loadProviders();
    }
  }, [isOpen]);

  async function loadConfig() {
    try {
      setLoading(true);
      const data = await fetchConfig();
      setConfig(data);

      // Populate form fields
      setLlmProvider(data.llm?.provider || 'anthropic');
      setLlmApiKey(data.llm?.api_key || '');
      setLlmModel(data.llm?.model || '');
      setSearchApiKey(data.integrations?.search_api_key || '');
      setJsearchApiKey(data.integrations?.jsearch_api_key || '');
      setAdzunaAppId(data.integrations?.adzuna_app_id || '');
      setAdzunaAppKey(data.integrations?.adzuna_app_key || '');
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  }

  async function loadProviders() {
    try {
      const data = await fetchProviders();
      setProviders(data);
    } catch (err) {
      console.error('Failed to load providers:', err);
    }
  }

  async function handleSave() {
    try {
      setSaving(true);
      setMessage(null);
      setErrors({});

      const updatedConfig = {
        llm: {
          provider: llmProvider,
          api_key: llmApiKey,
          model: llmModel,
        },
        integrations: {
          search_api_key: searchApiKey,
          jsearch_api_key: jsearchApiKey,
          adzuna_app_id: adzunaAppId,
          adzuna_app_key: adzunaAppKey,
        },
      };

      await updateConfig(updatedConfig);
      setMessage({ type: 'success', text: 'Settings saved successfully! Restart the app for changes to take effect.' });

      // Reload config to get masked values
      setTimeout(() => loadConfig(), 1000);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  }

  async function handleTestConnection() {
    try {
      setTesting(true);
      setMessage(null);

      if (!llmProvider) {
        setErrors({ llmProvider: 'Provider is required' });
        return;
      }

      if (!llmApiKey && llmProvider !== 'ollama') {
        setErrors({ llmApiKey: 'API key is required' });
        return;
      }

      const result = await testConnection(llmProvider, llmApiKey, llmModel);

      if (result.success) {
        setMessage({ type: 'success', text: result.message });
        setErrors({});
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setTesting(false);
    }
  }

  const selectedProvider = providers.find(p => p.id === llmProvider);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/30"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative ml-auto w-full max-w-2xl bg-white shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-light"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading settings...</div>
          ) : (
            <>
              {/* Message */}
              {message && (
                <div
                  className={`p-4 rounded-lg ${
                    message.type === 'success'
                      ? 'bg-green-50 text-green-800 border border-green-200'
                      : 'bg-red-50 text-red-800 border border-red-200'
                  }`}
                >
                  {message.text}
                </div>
              )}

              {/* LLM Configuration */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Assistant (LLM)</h3>
                <div className="space-y-4">
                  {/* Provider */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Provider *
                    </label>
                    <select
                      value={llmProvider}
                      onChange={(e) => setLlmProvider(e.target.value)}
                      className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                        errors.llmProvider ? 'border-red-500' : 'border-gray-300'
                      }`}
                    >
                      {providers.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                    {selectedProvider && (
                      <p className="mt-1 text-xs text-gray-500">
                        Default model: {selectedProvider.default_model}
                        {!selectedProvider.requires_api_key && ' • No API key required'}
                      </p>
                    )}
                    {errors.llmProvider && (
                      <p className="mt-1 text-sm text-red-600">{errors.llmProvider}</p>
                    )}
                  </div>

                  {/* API Key */}
                  {selectedProvider?.requires_api_key && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        API Key *
                      </label>
                      <input
                        type="password"
                        value={llmApiKey}
                        onChange={(e) => setLlmApiKey(e.target.value)}
                        placeholder="your-api-key-here"
                        className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm ${
                          errors.llmApiKey ? 'border-red-500' : 'border-gray-300'
                        }`}
                      />
                      {errors.llmApiKey && (
                        <p className="mt-1 text-sm text-red-600">{errors.llmApiKey}</p>
                      )}
                    </div>
                  )}

                  {/* Model Override */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Model Override (optional)
                    </label>
                    <input
                      type="text"
                      value={llmModel}
                      onChange={(e) => setLlmModel(e.target.value)}
                      placeholder={selectedProvider?.default_model || ''}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Leave empty to use the default model
                    </p>
                  </div>

                  {/* Test Connection Button */}
                  <button
                    onClick={handleTestConnection}
                    disabled={testing}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {testing ? 'Testing...' : 'Test Connection'}
                  </button>
                </div>
              </div>

              {/* Integrations */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Integrations (Optional)</h3>
                <div className="space-y-4">
                  {/* Search API */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tavily Search API Key
                    </label>
                    <input
                      type="password"
                      value={searchApiKey}
                      onChange={(e) => setSearchApiKey(e.target.value)}
                      placeholder="tvly-..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Enables web search tool in the AI assistant
                    </p>
                  </div>

                  {/* JSearch */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      JSearch API Key (RapidAPI)
                    </label>
                    <input
                      type="password"
                      value={jsearchApiKey}
                      onChange={(e) => setJsearchApiKey(e.target.value)}
                      placeholder="Your RapidAPI key"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      Enables job board search via JSearch (preferred)
                    </p>
                  </div>

                  {/* Adzuna */}
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Adzuna App ID
                      </label>
                      <input
                        type="text"
                        value={adzunaAppId}
                        onChange={(e) => setAdzunaAppId(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Adzuna App Key
                      </label>
                      <input
                        type="password"
                        value={adzunaAppKey}
                        onChange={(e) => setAdzunaAppKey(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                      />
                      <p className="mt-1 text-xs text-gray-500">
                        Alternative job board search API
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:text-gray-900"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
}
