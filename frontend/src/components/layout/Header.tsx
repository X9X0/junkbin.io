import { Link, useNavigate } from 'react-router-dom';
import { useState, useRef, useEffect } from 'react';
import { Search, Menu, X, User, LogOut, Plus, Wrench, Package, Cpu, FileText, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { search } from '../../api/endpoints';
import { useAuth } from '../../context/AuthContext';
import clsx from 'clsx';

export default function Header() {
  const { user, isAuthenticated, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Debounce search query — wait 300ms after user stops typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Search suggestions query with debounced input
  const { data: suggestions, isLoading: isSearching } = useQuery({
    queryKey: ['searchSuggestions', debouncedQuery],
    queryFn: () => search.global(debouncedQuery),
    enabled: debouncedQuery.length >= 2 && showSuggestions,
    staleTime: 30000,
  });

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setShowSuggestions(false);
      navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  const handleSuggestionClick = (path: string) => {
    setShowSuggestions(false);
    setSearchQuery('');
    navigate(path);
  };

  const totalResults = suggestions
    ? (suggestions.products?.length || 0) + (suggestions.components?.length || 0) + (suggestions.schematics?.length || 0)
    : 0;

  return (
    <header className="sticky top-0 z-50 border-b border-cyber-light/30 bg-cyber-darker/95 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <Wrench className="h-8 w-8 text-cyber-cyan transition-all group-hover:text-cyber-pink" />
              <div className="absolute inset-0 blur-sm bg-cyber-cyan/30 group-hover:bg-cyber-pink/30 transition-all" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold tracking-wider text-white">
                JUNK<span className="text-cyber-cyan">BIN</span>
              </h1>
              <p className="text-[10px] font-mono text-gray-500 tracking-widest">
                RIGHT TO REPAIR
              </p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <Link
              to="/products"
              className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
            >
              PRODUCTS
            </Link>
            <Link
              to="/components"
              className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
            >
              COMPONENTS
            </Link>
            <Link
              to="/schematics"
              className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
            >
              SCHEMATICS
            </Link>
          </nav>

          {/* Search Bar */}
          <div ref={searchRef} className="hidden md:block relative">
            <form onSubmit={handleSearch} className="flex items-center">
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setShowSuggestions(true);
                  }}
                  onFocus={() => setShowSuggestions(true)}
                  placeholder="Search products, components..."
                  className="w-64 bg-cyber-dark border border-cyber-light/50 rounded-none px-4 py-2 pl-10 text-sm font-mono text-gray-200 placeholder-gray-500 focus:border-cyber-cyan focus:outline-none transition-colors"
                />
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
              </div>
            </form>

            {/* Search Suggestions Dropdown */}
            {showSuggestions && searchQuery.length >= 2 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-cyber-dark border border-cyber-light/50 shadow-lg max-h-80 overflow-y-auto z-50">
                {isSearching ? (
                  <div className="p-4 text-center text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin mx-auto" />
                  </div>
                ) : totalResults === 0 ? (
                  <div className="p-3 text-sm text-gray-500 text-center">
                    No results for "{searchQuery}"
                  </div>
                ) : (
                  <>
                    {/* Products */}
                    {suggestions?.products?.slice(0, 3).map((p: any) => (
                      <button
                        key={`product-${p.id}`}
                        onClick={() => handleSuggestionClick(`/products/${p.id}`)}
                        className="w-full px-3 py-2 flex items-center gap-3 hover:bg-cyber-light/20 text-left transition-colors"
                      >
                        <Package className="h-4 w-4 text-cyber-cyan flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white truncate">{p.model_number}</div>
                          <div className="text-xs text-gray-500 truncate">{p.manufacturer}</div>
                        </div>
                        <span className="text-[10px] text-gray-600 uppercase">Product</span>
                      </button>
                    ))}

                    {/* Components */}
                    {suggestions?.components?.slice(0, 3).map((c: any) => (
                      <button
                        key={`component-${c.id}`}
                        onClick={() => handleSuggestionClick(`/components/${c.id}/products`)}
                        className="w-full px-3 py-2 flex items-center gap-3 hover:bg-cyber-light/20 text-left transition-colors"
                      >
                        <Cpu className="h-4 w-4 text-cyber-pink flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white font-mono truncate">{c.part_number}</div>
                          <div className="text-xs text-gray-500 truncate">{c.manufacturer}</div>
                        </div>
                        <span className="text-[10px] text-gray-600 uppercase">Component</span>
                      </button>
                    ))}

                    {/* Schematics */}
                    {suggestions?.schematics?.slice(0, 2).map((s: any) => (
                      <button
                        key={`schematic-${s.id}`}
                        onClick={() => handleSuggestionClick(`/products/${s.product?.id}`)}
                        className="w-full px-3 py-2 flex items-center gap-3 hover:bg-cyber-light/20 text-left transition-colors"
                      >
                        <FileText className="h-4 w-4 text-cyber-green flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white truncate">{s.title}</div>
                          <div className="text-xs text-gray-500 truncate">{s.schematic_type_display}</div>
                        </div>
                        <span className="text-[10px] text-gray-600 uppercase">Schematic</span>
                      </button>
                    ))}

                    {/* View all link */}
                    <button
                      onClick={() => {
                        setShowSuggestions(false);
                        navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
                      }}
                      className="w-full px-3 py-2 text-center text-sm text-cyber-cyan hover:bg-cyber-cyan/10 border-t border-cyber-light/30"
                    >
                      View all {totalResults} results →
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Right side - Auth */}
          <div className="hidden md:flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <Link
                  to="/submit"
                  className="btn-cyber flex items-center gap-2 text-sm py-1.5"
                >
                  <Plus className="h-4 w-4" />
                  SUBMIT
                </Link>
                <div className="relative group">
                  <button className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
                    <User className="h-5 w-5" />
                    <span className="font-mono text-sm">{user?.username}</span>
                  </button>
                  <div className="absolute right-0 mt-2 w-48 py-2 bg-cyber-dark border border-cyber-light/30 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                    <Link
                      to="/profile"
                      className="block px-4 py-2 text-sm text-gray-400 hover:text-cyber-cyan hover:bg-cyber-light/20"
                    >
                      Profile
                    </Link>
                    <Link
                      to="/my-submissions"
                      className="block px-4 py-2 text-sm text-gray-400 hover:text-cyber-cyan hover:bg-cyber-light/20"
                    >
                      My Submissions
                    </Link>
                    <button
                      onClick={logout}
                      className="w-full text-left px-4 py-2 text-sm text-gray-400 hover:text-cyber-pink hover:bg-cyber-light/20 flex items-center gap-2"
                    >
                      <LogOut className="h-4 w-4" />
                      Logout
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  LOGIN
                </Link>
                <Link to="/register" className="btn-cyber text-sm py-1.5">
                  REGISTER
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden p-2 text-gray-400 hover:text-white"
          >
            {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile menu */}
        <div
          className={clsx(
            'md:hidden overflow-hidden transition-all duration-300',
            isMenuOpen ? 'max-h-96 py-4' : 'max-h-0'
          )}
        >
          <form onSubmit={handleSearch} className="mb-4">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
                className="w-full bg-cyber-dark border border-cyber-light/50 px-4 py-2 pl-10 text-sm font-mono text-gray-200 placeholder-gray-500 focus:border-cyber-cyan focus:outline-none"
              />
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            </div>
          </form>
          <nav className="flex flex-col gap-2">
            <Link
              to="/products"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan"
              onClick={() => setIsMenuOpen(false)}
            >
              PRODUCTS
            </Link>
            <Link
              to="/components"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan"
              onClick={() => setIsMenuOpen(false)}
            >
              COMPONENTS
            </Link>
            <Link
              to="/schematics"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan"
              onClick={() => setIsMenuOpen(false)}
            >
              SCHEMATICS
            </Link>
            <div className="border-t border-cyber-light/30 pt-4 mt-2">
              {isAuthenticated ? (
                <>
                  <Link
                    to="/submit"
                    className="block py-2 font-mono text-sm text-cyber-cyan"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    + SUBMIT NEW
                  </Link>
                  <button
                    onClick={() => {
                      logout();
                      setIsMenuOpen(false);
                    }}
                    className="py-2 font-mono text-sm text-cyber-pink"
                  >
                    LOGOUT
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="block py-2 font-mono text-sm text-gray-400"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    LOGIN
                  </Link>
                  <Link
                    to="/register"
                    className="block py-2 font-mono text-sm text-cyber-cyan"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    REGISTER
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
