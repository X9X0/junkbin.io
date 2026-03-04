import { Link, useNavigate } from 'react-router-dom';
import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Menu, X, User, LogOut, Plus, Wrench, Package, Cpu, FileText, Loader2, Shield, Trophy, MessageSquare, Award, Archive, Hammer, BookOpen, BarChart3, Store, Globe, Check } from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { search, auth as authApi } from '../../api/endpoints';
import { useAuth } from '../../context/AuthContext';
import { useUnreadCount } from '../../hooks/useUnreadCount';
import clsx from 'clsx';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'es', label: 'Español' },
  { code: 'pt', label: 'Português' },
  { code: 'de', label: 'Deutsch' },
  { code: 'it', label: 'Italiano' },
  { code: 'nl', label: 'Nederlands' },
  { code: 'pl', label: 'Polski' },
  { code: 'cs', label: 'Čeština' },
  { code: 'sk', label: 'Slovenčina' },
  { code: 'hr', label: 'Hrvatski' },
  { code: 'sr', label: 'Srpski' },
  { code: 'sl', label: 'Slovenščina' },
  { code: 'ru', label: 'Русский' },
  { code: 'uk', label: 'Українська' },
  { code: 'ro', label: 'Română' },
  { code: 'hu', label: 'Magyar' },
  { code: 'tr', label: 'Türkçe' },
];

const GITHUB_REPO = 'https://github.com/X9X0/junkbin.io';

export default function Header() {
  const { t, i18n } = useTranslation();
  const { user, isAuthenticated, logout } = useAuth();
  const queryClient = useQueryClient();
  const unreadCount = useUnreadCount();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [showLangMenu, setShowLangMenu] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const langRef = useRef<HTMLDivElement>(null);
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
      if (langRef.current && !langRef.current.contains(e.target as Node)) {
        setShowLangMenu(false);
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

  const handleLanguageChange = (code: string) => {
    i18n.changeLanguage(code);
    setShowLangMenu(false);
    setIsMenuOpen(false);
    // Persist to user profile when authenticated
    if (isAuthenticated) {
      authApi.updateMe({ preferred_language: code }).catch(() => {
        // Non-critical — localStorage already saved by i18next
      });
    }
  };

  const totalResults = suggestions
    ? (suggestions.products?.length || 0) + (suggestions.components?.length || 0) + (suggestions.schematics?.length || 0) + (suggestions.users?.length || 0)
    : 0;

  const currentLang = LANGUAGES.find(l => l.code === i18n.language) || LANGUAGES[0];

  return (
    <header className="sticky top-0 z-50 border-b border-cyber-light/30 bg-cyber-darker/95 backdrop-blur-sm">
      <div className="mx-auto max-w-screen-2xl px-4">
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
                {t('nav.right_to_repair')}
              </p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <Link
              to="/products"
              className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
            >
              {t('nav.products')}
            </Link>
            <Link
              to="/components"
              className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
            >
              {t('nav.components')}
            </Link>
            <Link
              to="/schematics"
              className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
            >
              {t('nav.schematics')}
            </Link>
            <Link
              to="/recipes"
              className="font-mono text-sm text-gray-400 hover:text-cyber-cyan transition-colors"
            >
              {t('nav.recipes')}
            </Link>
            <Link
              to="/community"
              className="font-mono text-sm text-gray-400 hover:text-cyber-yellow transition-colors flex items-center gap-1"
            >
              <Trophy className="h-3.5 w-3.5" />
              {t('nav.community')}
            </Link>
            {isAuthenticated && (user?.is_moderator || user?.is_staff) && (
              <>
                <Link
                  to="/moderation"
                  className="font-mono text-sm text-cyber-yellow hover:text-cyber-yellow/80 transition-colors flex items-center gap-1"
                >
                  <Shield className="h-3.5 w-3.5" />
                  {t('nav.mod')}
                </Link>
                <Link
                  to="/analytics"
                  className="font-mono text-sm text-cyber-yellow hover:text-cyber-yellow/80 transition-colors flex items-center gap-1"
                >
                  <BarChart3 className="h-3.5 w-3.5" />
                  {t('nav.analytics')}
                </Link>
              </>
            )}
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
                  placeholder={t('nav.search_placeholder')}
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
                    {t('nav.no_results_for', { query: searchQuery })}
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

                    {/* Users */}
                    {suggestions?.users?.slice(0, 3).map((u: any) => (
                      <button
                        key={`user-${u.id}`}
                        onClick={() => handleSuggestionClick(`/users/${u.id}`)}
                        className="w-full px-3 py-2 flex items-center gap-3 hover:bg-cyber-light/20 text-left transition-colors"
                      >
                        <User className="h-4 w-4 text-cyber-yellow flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-white truncate flex items-center gap-1">
                            {u.display_name || u.username}
                            {u.is_trusted && <Shield className="h-3 w-3 text-cyber-green flex-shrink-0" />}
                          </div>
                          <div className="text-xs text-gray-500 flex items-center gap-1">
                            <Award className="h-3 w-3" />
                            {u.reputation_score} rep
                          </div>
                        </div>
                        <span className="text-[10px] text-gray-600 uppercase">User</span>
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
                      {t('nav.view_all_results', { count: totalResults })}
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Right side - Auth + Language */}
          <div className="hidden md:flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <Link
                  to="/buildable"
                  className="font-mono text-sm text-cyber-green hover:text-cyber-green/80 transition-colors flex items-center gap-1"
                >
                  <Hammer className="h-3.5 w-3.5" />
                  {t('nav.build')}
                </Link>
                <Link
                  to="/submit"
                  className="btn-cyber flex items-center gap-2 text-sm py-1.5"
                >
                  <Plus className="h-4 w-4" />
                  {t('nav.submit')}
                </Link>
                <Link
                  to="/swap"
                  className="relative text-gray-400 hover:text-cyber-cyan transition-colors p-1"
                  title={t('nav.swap')}
                >
                  <Store className="h-5 w-5" />
                </Link>
                <Link
                  to="/messages"
                  className="relative text-gray-400 hover:text-cyber-cyan transition-colors p-1"
                >
                  <MessageSquare className="h-5 w-5" />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-cyber-pink text-[10px] font-mono font-bold text-white px-1">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
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
                      {t('nav.profile')}
                    </Link>
                    <Link
                      to="/my-junkbin"
                      className="block px-4 py-2 text-sm text-gray-400 hover:text-cyber-cyan hover:bg-cyber-light/20 flex items-center gap-2"
                    >
                      <Archive className="h-3.5 w-3.5" />
                      {t('nav.my_junkbin')}
                    </Link>
                    <Link
                      to="/my-submissions"
                      className="block px-4 py-2 text-sm text-gray-400 hover:text-cyber-cyan hover:bg-cyber-light/20"
                    >
                      {t('nav.my_submissions')}
                    </Link>
                    <button
                      onClick={async () => { await logout(); queryClient.clear(); navigate('/login'); }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-400 hover:text-cyber-pink hover:bg-cyber-light/20 flex items-center gap-2"
                    >
                      <LogOut className="h-4 w-4" />
                      {t('nav.logout')}
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
                  {t('nav.login')}
                </Link>
                <Link to="/register" className="btn-cyber text-sm py-1.5">
                  {t('nav.register')}
                </Link>
              </>
            )}

            {/* Language switcher */}
            <div ref={langRef} className="relative">
              <button
                onClick={() => setShowLangMenu(!showLangMenu)}
                className="flex items-center gap-1 text-gray-400 hover:text-cyber-cyan transition-colors p-1"
                title={t('lang.switcher_label')}
              >
                <Globe className="h-4 w-4" />
                <span className="font-mono text-xs uppercase">{i18n.language?.slice(0, 2) || 'en'}</span>
              </button>
              {showLangMenu && (
                <div className="absolute right-0 mt-2 w-44 py-1 bg-cyber-dark border border-cyber-light/30 shadow-lg z-50">
                  {LANGUAGES.map((lang) => (
                    <button
                      key={lang.code}
                      onClick={() => handleLanguageChange(lang.code)}
                      className="w-full px-3 py-2 text-left text-sm text-gray-400 hover:text-cyber-cyan hover:bg-cyber-light/20 flex items-center justify-between transition-colors"
                    >
                      <span>{lang.label}</span>
                      {i18n.language?.startsWith(lang.code) && (
                        <Check className="h-3.5 w-3.5 text-cyber-cyan" />
                      )}
                    </button>
                  ))}
                  <div className="border-t border-cyber-light/20 mt-1 pt-1">
                    <a
                      href={`${GITHUB_REPO}/blob/main/frontend/public/locales/${i18n.language?.slice(0, 2) || 'en'}/translation.json`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full px-3 py-2 text-left text-xs text-gray-600 hover:text-cyber-green hover:bg-cyber-light/20 flex items-center gap-1.5 transition-colors"
                      onClick={() => setShowLangMenu(false)}
                    >
                      <Globe className="h-3 w-3" />
                      Help improve this translation →
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Mobile controls */}
          <div className="md:hidden flex items-center gap-1">
            {isAuthenticated ? (
              <>
                <Link
                  to="/submit"
                  className="p-2 text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  <Plus className="h-5 w-5" />
                </Link>
                <Link
                  to="/swap"
                  className="p-2 text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  <Store className="h-5 w-5" />
                </Link>
                <Link
                  to="/messages"
                  className="relative p-2 text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  <MessageSquare className="h-5 w-5" />
                  {unreadCount > 0 && (
                    <span className="absolute top-0.5 right-0.5 min-w-[14px] h-3.5 flex items-center justify-center rounded-full bg-cyber-pink text-[9px] font-mono font-bold text-white px-0.5">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </Link>
                <Link
                  to="/profile"
                  className="p-2 text-gray-400 hover:text-cyber-cyan transition-colors"
                >
                  <User className="h-5 w-5" />
                </Link>
              </>
            ) : (
              <Link
                to="/login"
                className="p-2 text-gray-400 hover:text-cyber-cyan transition-colors"
              >
                <User className="h-5 w-5" />
              </Link>
            )}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="p-2 text-gray-400 hover:text-white"
            >
              {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        <div
          className={clsx(
            'md:hidden overflow-hidden transition-all duration-300',
            isMenuOpen ? 'max-h-[32rem] py-4' : 'max-h-0'
          )}
        >
          <form onSubmit={handleSearch} className="mb-4">
            <div className="relative">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('nav.search_mobile_placeholder')}
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
              {t('nav.products')}
            </Link>
            <Link
              to="/components"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan"
              onClick={() => setIsMenuOpen(false)}
            >
              {t('nav.components')}
            </Link>
            <Link
              to="/schematics"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan"
              onClick={() => setIsMenuOpen(false)}
            >
              {t('nav.schematics')}
            </Link>
            <Link
              to="/recipes"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan"
              onClick={() => setIsMenuOpen(false)}
            >
              {t('nav.recipes')}
            </Link>
            <Link
              to="/community"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-yellow flex items-center gap-1"
              onClick={() => setIsMenuOpen(false)}
            >
              <Trophy className="h-3.5 w-3.5" />
              {t('nav.community')}
            </Link>
            <Link
              to="/swap"
              className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan flex items-center gap-1"
              onClick={() => setIsMenuOpen(false)}
            >
              <Store className="h-3.5 w-3.5" />
              {t('nav.swap')}
            </Link>
            {isAuthenticated && (
              <Link
                to="/messages"
                className="py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan flex items-center gap-1"
                onClick={() => setIsMenuOpen(false)}
              >
                <MessageSquare className="h-3.5 w-3.5" />
                {t('nav.messages')}
                {unreadCount > 0 && (
                  <span className="ml-1 min-w-[16px] h-4 flex items-center justify-center rounded-full bg-cyber-pink text-[10px] font-mono font-bold text-white px-1">
                    {unreadCount > 99 ? '99+' : unreadCount}
                  </span>
                )}
              </Link>
            )}
            {isAuthenticated && (user?.is_moderator || user?.is_staff) && (
              <>
                <Link
                  to="/moderation"
                  className="py-2 font-mono text-sm text-cyber-yellow flex items-center gap-1"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <Shield className="h-3.5 w-3.5" />
                  {t('nav.moderation')}
                </Link>
                <Link
                  to="/analytics"
                  className="py-2 font-mono text-sm text-cyber-yellow flex items-center gap-1"
                  onClick={() => setIsMenuOpen(false)}
                >
                  <BarChart3 className="h-3.5 w-3.5" />
                  {t('nav.analytics')}
                </Link>
              </>
            )}
            <div className="border-t border-cyber-light/30 pt-4 mt-2">
              {isAuthenticated ? (
                <>
                  <Link
                    to="/buildable"
                    className="block py-2 font-mono text-sm text-cyber-green hover:text-cyber-green/80 flex items-center gap-1"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <Hammer className="h-3.5 w-3.5" />
                    {t('nav.build')}
                  </Link>
                  <Link
                    to="/my-junkbin"
                    className="block py-2 font-mono text-sm text-gray-400 hover:text-cyber-cyan flex items-center gap-1"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    <Archive className="h-3.5 w-3.5" />
                    {t('nav.my_junkbin_upper')}
                  </Link>
                  <Link
                    to="/submit"
                    className="block py-2 font-mono text-sm text-cyber-cyan"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {t('nav.submit_new')}
                  </Link>
                  <button
                    onClick={async () => { await logout(); queryClient.clear(); setIsMenuOpen(false); navigate('/login'); }}
                    className="py-2 font-mono text-sm text-cyber-pink"
                  >
                    {t('nav.logout')}
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="block py-2 font-mono text-sm text-gray-400"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {t('nav.login')}
                  </Link>
                  <Link
                    to="/register"
                    className="block py-2 font-mono text-sm text-cyber-cyan"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    {t('nav.register')}
                  </Link>
                </>
              )}
            </div>

            {/* Mobile language selector */}
            <div className="border-t border-cyber-light/30 pt-4 mt-2">
              <p className="text-xs font-mono text-gray-600 mb-2 flex items-center gap-1">
                <Globe className="h-3.5 w-3.5" />
                {t('lang.switcher_label')}
              </p>
              <div className="flex flex-wrap gap-2">
                {LANGUAGES.map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => handleLanguageChange(lang.code)}
                    className={clsx(
                      'px-2 py-1 text-xs font-mono border transition-colors',
                      i18n.language?.startsWith(lang.code)
                        ? 'border-cyber-cyan text-cyber-cyan bg-cyber-cyan/10'
                        : 'border-cyber-light/30 text-gray-500 hover:text-cyber-cyan hover:border-cyber-cyan/50'
                    )}
                  >
                    {lang.label}
                  </button>
                ))}
              </div>
              <a
                href={`${GITHUB_REPO}/blob/main/frontend/public/locales/${i18n.language?.slice(0, 2) || 'en'}/translation.json`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 flex items-center gap-1.5 text-xs text-gray-600 hover:text-cyber-green transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                <Globe className="h-3 w-3" />
                Help improve this translation →
              </a>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
