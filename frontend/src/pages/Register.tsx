import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserPlus, AlertCircle, Check } from 'lucide-react';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.password_confirm) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);

    try {
      await register(formData);
      navigate('/');
    } catch (err: any) {
      const data = err.response?.data;
      if (data) {
        const messages = Object.values(data).flat();
        setError(messages.join(' '));
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-200px)] flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="font-display text-3xl font-bold text-white mb-2">
            CREATE <span className="text-cyber-cyan">ACCOUNT</span>
          </h1>
          <p className="text-gray-500 font-mono text-sm">
            Join the repair community
          </p>
        </div>

        <div className="card-cyber p-8">
          {error && (
            <div className="flex items-center gap-2 p-4 mb-6 bg-cyber-pink/10 border border-cyber-pink/30 text-cyber-pink">
              <AlertCircle className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                USERNAME
              </label>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                className="input-cyber"
                placeholder="Choose a username"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                EMAIL
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="input-cyber"
                placeholder="your@email.com"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                PASSWORD
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="input-cyber"
                placeholder="Min 8 characters"
                required
                minLength={8}
              />
            </div>

            <div>
              <label className="block text-sm font-mono text-gray-400 mb-2">
                CONFIRM PASSWORD
              </label>
              <input
                type="password"
                name="password_confirm"
                value={formData.password_confirm}
                onChange={handleChange}
                className="input-cyber"
                placeholder="Repeat password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full btn-cyber flex items-center justify-center gap-2 py-3"
            >
              {isLoading ? (
                <span className="animate-pulse">CREATING ACCOUNT...</span>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  REGISTER
                </>
              )}
            </button>
          </form>

          {/* Benefits */}
          <div className="mt-6 p-4 bg-cyber-cyan/5 border border-cyber-cyan/20">
            <p className="text-xs font-mono text-gray-400 mb-3">
              WITH AN ACCOUNT YOU CAN:
            </p>
            <ul className="space-y-2 text-sm text-gray-300">
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-cyber-green" />
                Submit products and components
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-cyber-green" />
                Upload schematics and documentation
              </li>
              <li className="flex items-center gap-2">
                <Check className="h-4 w-4 text-cyber-green" />
                Build reputation in the community
              </li>
            </ul>
          </div>

          <div className="divider-circuit" />

          <p className="text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link to="/login" className="text-cyber-cyan hover:underline">
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
